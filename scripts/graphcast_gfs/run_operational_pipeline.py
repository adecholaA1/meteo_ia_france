"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Pipeline OPÉRATIONNEL GraphCast (prédictions J+1)
FICHIER  : scripts/graphcast_gfs/run_operational_pipeline.py
RÔLE     : Version opérationnelle du pipeline. Utilise les runs 18z de
           chaque jour J pour publier les prédictions complètes du jour J+1.
           Supporte le mode batch (recollecte plusieurs dates) avec retry.
═══════════════════════════════════════════════════════════════════════════

DIFFÉRENCE vs run_daily_pipeline.py
-----------------------------------
  - Mode batch multi-dates dans une SEULE session Python
    → JIT compilé UNE FOIS pour N dates (gain énorme : 80min → 30min pour 9 dates)
  - Retry automatique 3× par étape en cas d'échec
  - Par défaut : --hour 18 (runs opérationnels)
  - Par défaut : prédit J+1 complet (4 horizons)

PIPELINE COMPLET PAR DATE
-------------------------
Pour chaque date/run (ex: run 18z du 16 avril 2026) :
  T-6h = 16 avril 12h UTC
  T0   = 16 avril 18h UTC
  → Prédictions : 17 avril 00h, 06h, 12h, 18h (= journée J+1 complète)

  1. Téléchargement GDAS NOMADS (T-6h + T0)
  2. Parsing GRIB2 → NetCDF
  3. Inférence GraphCast Operational
  4. Export CSV format DB

USAGE
-----
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts

    # BATCH : recollecter du 16 avril au 24 avril (runs 18z, prédit 17→25)
    python -m graphcast_gfs.run_operational_pipeline \
        --start-date 2026-04-16 --end-date 2026-04-24

    # UNE date précise
    python -m graphcast_gfs.run_operational_pipeline --date 2026-04-24

    # Aujourd'hui (par défaut, 18z d'aujourd'hui)
    python -m graphcast_gfs.run_operational_pipeline

    # Skip les fichiers déjà présents
    python -m graphcast_gfs.run_operational_pipeline \
        --start-date 2026-04-16 --end-date 2026-04-24 --skip-existing

TEMPS ESTIMÉ SUR MAC CPU
------------------------
- Chargement modèle + compilation JIT : ~8 min (UNE SEULE FOIS)
- Par date supplémentaire              : ~2 min (téléchargement + inférence)
- 9 dates total                        : ~25-30 min
═══════════════════════════════════════════════════════════════════════════
"""

# Suppression warnings avant imports lourds
import os
os.environ["JAX_PLATFORMS"] = "cpu"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GRPC_VERBOSITY"] = "ERROR"

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message="Skipping gradient checkpointing")
warnings.filterwarnings("ignore", message=".*Dataset.dims.*")
warnings.filterwarnings("ignore", message=".*xarray.concat.*")

import logging
logging.getLogger("absl").setLevel(logging.ERROR)
logging.getLogger("jax").setLevel(logging.ERROR)

import argparse
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable, Optional, List

# Imports des modules de notre pipeline
from graphcast_gfs.fetch_gdas_nomads import download_run, OUTPUT_DIR as FETCH_OUTPUT_DIR
from graphcast_gfs.parse_gdas import assemble_run, OUTPUT_DIR as PARSE_OUTPUT_DIR
from graphcast_gfs.export_graphcast_csv import export_run_to_csv, OUTPUT_DIR as CSV_OUTPUT_DIR
from graphcast_gfs.inference_graphcast import (
    load_graphcast_model,
    build_jit_functions,
    run_inference_single_date,
    OUTPUT_DIR as INFERENCE_OUTPUT_DIR,
)


# ───────────────────────────────────────────────────────────────────────────
# Configuration logging
# ───────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# CONFIGURATION RETRY
# ───────────────────────────────────────────────────────────────────────────

RETRY_MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 10  # 10 sec entre tentatives (30 min en prod VPS)


def retry(
    fn: Callable,
    name: str,
    max_attempts: int = RETRY_MAX_ATTEMPTS,
    delay: int = RETRY_DELAY_SECONDS,
):
    """
    Exécute une fonction avec retry automatique.

    Args:
        fn: Fonction à exécuter (sans arguments, utilise une lambda/partial si besoin)
        name: Nom descriptif pour les logs
        max_attempts: Nombre max de tentatives
        delay: Délai en secondes entre tentatives

    Returns:
        Le résultat de la fonction si succès

    Raises:
        Exception: Si toutes les tentatives ont échoué
    """
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            if attempt > 1:
                logger.warning(
                    f"   🔄 Tentative {attempt}/{max_attempts} pour '{name}'..."
                )
            return fn()
        except Exception as e:
            last_exception = e
            logger.error(
                f"   ⚠️  Tentative {attempt}/{max_attempts} échouée pour '{name}' : {e}"
            )
            if attempt < max_attempts:
                logger.info(f"   ⏳ Pause {delay}s avant prochaine tentative...")
                time.sleep(delay)

    logger.error(f"   ❌ ÉCHEC DÉFINITIF après {max_attempts} tentatives : {name}")
    raise last_exception


# ───────────────────────────────────────────────────────────────────────────
# GESTION DES ARGUMENTS CLI
# ───────────────────────────────────────────────────────────────────────────

def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Pipeline opérationnel GraphCast — prédictions J+1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date unique au format YYYY-MM-DD (défaut: aujourd'hui)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Date de début pour mode batch (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Date de fin pour mode batch (YYYY-MM-DD, incluse)",
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=18,
        choices=[0, 6, 12, 18],
        help="Heure UTC du run (0, 6, 12, 18). Défaut: 18 (opérationnel J+1).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip les étapes dont le fichier de sortie existe déjà",
    )
    return parser.parse_args()


def get_dates_to_process(args) -> List[datetime]:
    """Calcule la liste des dates à traiter selon les arguments."""
    # Mode batch
    if args.start_date and args.end_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError:
            logger.error("❌ Format invalide pour --start-date ou --end-date (YYYY-MM-DD)")
            sys.exit(1)

        if end_date < start_date:
            logger.error("❌ --end-date doit être après --start-date")
            sys.exit(1)

        dates = []
        current = start_date
        while current <= end_date:
            dates.append(datetime(
                year=current.year, month=current.month, day=current.day,
                hour=args.hour, minute=0, second=0,
            ))
            current += timedelta(days=1)
        return dates

    # Mode date unique
    if args.date:
        try:
            run_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"❌ Format de date invalide : {args.date}")
            sys.exit(1)
    else:
        # Défaut : aujourd'hui UTC
        run_date = datetime.now(timezone.utc).date()

    return [datetime(
        year=run_date.year, month=run_date.month, day=run_date.day,
        hour=args.hour, minute=0, second=0,
    )]


# ───────────────────────────────────────────────────────────────────────────
# ÉTAPES DU PIPELINE (avec retry intégré)
# ───────────────────────────────────────────────────────────────────────────

def step_fetch(run_dt: datetime, skip_existing: bool) -> Path:
    """Étape 1 : Téléchargement GDAS via NOMADS (avec retry)."""
    logger.info(f"\n📥 [1/4] Collecte GDAS run {run_dt.strftime('%Y-%m-%d %Hz UTC')}")

    run_dir = FETCH_OUTPUT_DIR / run_dt.strftime("%Y%m%d_%H")

    # Check idempotence
    if skip_existing and run_dir.exists():
        n_files = sum(1 for _ in run_dir.rglob("*.grib2"))
        if n_files >= 28:
            logger.info(f"   ✅ Fichiers déjà présents ({n_files}/28), skip")
            return run_dir

    def _fetch():
        success = download_run(run_dt, run_dir)
        if not success:
            raise RuntimeError(f"Collecte GDAS incomplète pour {run_dt}")
        return run_dir

    t0 = time.time()
    result = retry(_fetch, f"fetch {run_dt.strftime('%Y-%m-%d %Hz')}")
    elapsed = time.time() - t0

    n_files = sum(1 for _ in run_dir.rglob("*.grib2"))
    logger.info(f"   ✅ Collecte OK ({n_files} fichiers, {elapsed:.1f}s)")
    return result


def step_parse(run_dt: datetime, run_dir: Path, skip_existing: bool) -> Path:
    """Étape 2 : Parsing GRIB2 → NetCDF (avec retry)."""
    logger.info(f"\n🔧 [2/4] Parsing GRIB2 → NetCDF run {run_dt.strftime('%Y-%m-%d %Hz')}")

    date_str = run_dt.strftime("%Y%m%d_%H")
    output_path = PARSE_OUTPUT_DIR / f"gdas_{date_str}.nc"

    if skip_existing and output_path.exists():
        logger.info(f"   ✅ {output_path.name} existe déjà, skip")
        return output_path

    PARSE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _parse():
        ds = assemble_run(run_dt, run_dir)
        ds.to_netcdf(output_path)
        return output_path

    t0 = time.time()
    result = retry(_parse, f"parse {run_dt.strftime('%Y-%m-%d %Hz')}")
    elapsed = time.time() - t0

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ {output_path.name} ({size_mb:.1f} Mo, {elapsed:.1f}s)")
    return result


def step_inference(
    run_dt: datetime,
    gdas_nc_path: Path,
    run_forward_jitted,
    task_config,
    static_vars_global,
    skip_existing: bool,
) -> Path:
    """
    Étape 3 : Inférence GraphCast (avec retry).

    Note : le modèle est passé en argument pour réutilisation entre runs
    → JIT compilé UNE SEULE FOIS pour tout le batch.
    """
    logger.info(f"\n🤖 [3/4] Inférence GraphCast run {run_dt.strftime('%Y-%m-%d %Hz')}")

    date_str = run_dt.strftime("%Y%m%d")
    hour_str = run_dt.strftime("%H")
    output_path = INFERENCE_OUTPUT_DIR / f"graphcast_{date_str}_{hour_str}h.nc"

    if skip_existing and output_path.exists():
        logger.info(f"   ✅ {output_path.name} existe déjà, skip")
        return output_path

    INFERENCE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _infer():
        return run_inference_single_date(
            gdas_nc_path, run_dt, run_forward_jitted, task_config,
            static_vars_global, INFERENCE_OUTPUT_DIR,
        )

    t0 = time.time()
    result = retry(_infer, f"inference {run_dt.strftime('%Y-%m-%d %Hz')}")
    elapsed = time.time() - t0

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ {output_path.name} ({size_mb:.1f} Mo, {elapsed:.1f}s)")
    return result


def step_csv(
    run_dt: datetime,
    prediction_nc_path: Path,
    skip_existing: bool,
) -> Path:
    """Étape 4 : Export CSV format DB (avec retry)."""
    logger.info(f"\n📊 [4/4] Export CSV run {run_dt.strftime('%Y-%m-%d %Hz')}")

    date_str = run_dt.strftime("%Y%m%d")
    hour_str = run_dt.strftime("%H")
    output_path = CSV_OUTPUT_DIR / f"graphcast_{date_str}_{hour_str}h.csv"

    if skip_existing and output_path.exists():
        logger.info(f"   ✅ {output_path.name} existe déjà, skip")
        return output_path

    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _export():
        return export_run_to_csv(prediction_nc_path, CSV_OUTPUT_DIR)

    t0 = time.time()
    result = retry(_export, f"csv {run_dt.strftime('%Y-%m-%d %Hz')}")
    elapsed = time.time() - t0

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ {output_path.name} ({size_mb:.1f} Mo, {elapsed:.1f}s)")
    return result


# ───────────────────────────────────────────────────────────────────────────
# PIPELINE POUR UNE DATE (utilise les éléments préchargés)
# ───────────────────────────────────────────────────────────────────────────

def run_pipeline_for_date(
    run_dt: datetime,
    run_forward_jitted,
    task_config,
    static_vars_global,
    skip_existing: bool,
) -> dict:
    """
    Exécute le pipeline complet pour UNE date.

    Utilise le modèle GraphCast déjà chargé (JIT compilé) pour éviter
    la recompilation. Retourne un dict avec le statut de chaque étape.
    """
    t_minus_6h = run_dt - timedelta(hours=6)
    target_date = run_dt + timedelta(hours=24)

    logger.info("\n" + "╔" + "═" * 68 + "╗")
    msg = f"🔄 Pipeline run {run_dt.strftime('%Y-%m-%d %Hz UTC')}"
    logger.info(f"║  {msg:<66s}║")
    msg = f"   T-6h = {t_minus_6h.strftime('%Y-%m-%d %Hz')} | T0 = {run_dt.strftime('%Y-%m-%d %Hz')}"
    logger.info(f"║  {msg:<66s}║")
    msg = f"   Prédit jusqu'à : {target_date.strftime('%Y-%m-%d %Hz')} (= J+1)"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")

    t_start = time.time()
    results = {
        "run_dt": run_dt,
        "fetch": None,
        "parse": None,
        "inference": None,
        "csv": None,
        "error": None,
    }

    try:
        # Étape 1 : Fetch
        run_dir = step_fetch(run_dt, skip_existing)
        results["fetch"] = run_dir

        # Étape 2 : Parse
        gdas_nc_path = step_parse(run_dt, run_dir, skip_existing)
        results["parse"] = gdas_nc_path

        # Étape 3 : Inférence (utilise le modèle pré-chargé)
        prediction_nc_path = step_inference(
            run_dt, gdas_nc_path, run_forward_jitted,
            task_config, static_vars_global, skip_existing,
        )
        results["inference"] = prediction_nc_path

        # Étape 4 : CSV
        csv_path = step_csv(run_dt, prediction_nc_path, skip_existing)
        results["csv"] = csv_path

        elapsed = time.time() - t_start
        logger.info(f"\n✅ Pipeline {run_dt.strftime('%Y-%m-%d %Hz')} OK en {elapsed:.1f}s")

    except Exception as e:
        results["error"] = str(e)
        elapsed = time.time() - t_start
        logger.error(f"\n❌ Pipeline {run_dt.strftime('%Y-%m-%d %Hz')} ÉCHEC en {elapsed:.1f}s : {e}")

    return results


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def main():
    args = parse_arguments()
    dates = get_dates_to_process(args)

    # Banner
    logger.info("╔" + "═" * 68 + "╗")
    if len(dates) == 1:
        msg = f"🚀 PIPELINE OPÉRATIONNEL GRAPHCAST — {dates[0].strftime('%Y-%m-%d %Hz UTC')}"
    else:
        msg = f"🚀 PIPELINE OPÉRATIONNEL GRAPHCAST — BATCH {len(dates)} RUNS"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")

    logger.info(f"   Nombre de runs : {len(dates)}")
    logger.info(f"   Mode           : {'BATCH' if len(dates) > 1 else 'SINGLE'}")
    logger.info(f"   Skip existing  : {args.skip_existing}")
    logger.info(f"\n📅 Runs à traiter :")
    for dt in dates:
        target = dt + timedelta(hours=24)
        logger.info(
            f"   • {dt.strftime('%Y-%m-%d %Hz')} "
            f"→ prédit jusqu'au {target.strftime('%Y-%m-%d %Hz')}"
        )

    t_global_start = time.time()

    # ═══════════════════════════════════════════════════════════════════
    # CHARGEMENT DU MODÈLE — UNE SEULE FOIS POUR TOUT LE BATCH
    # ═══════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 70)
    logger.info("📦 CHARGEMENT DU MODÈLE GRAPHCAST (une seule fois)")
    logger.info("=" * 70)
    (
        params,
        state,
        model_config,
        task_config,
        stats,
        static_vars_global,
    ) = load_graphcast_model()

    logger.info("\n🔧 Construction JIT...")
    run_forward_jitted = build_jit_functions(
        params, state, model_config, task_config, stats
    )
    logger.info("   ✅ JIT construit (compilation à la 1ère inférence)")

    # ═══════════════════════════════════════════════════════════════════
    # EXÉCUTION DU PIPELINE POUR CHAQUE DATE
    # ═══════════════════════════════════════════════════════════════════
    all_results = []
    for i, run_dt in enumerate(dates, 1):
        logger.info(f"\n{'█' * 70}")
        logger.info(f"RUN {i}/{len(dates)}")
        logger.info(f"{'█' * 70}")

        result = run_pipeline_for_date(
            run_dt, run_forward_jitted, task_config,
            static_vars_global, args.skip_existing,
        )
        all_results.append(result)

    # ═══════════════════════════════════════════════════════════════════
    # RÉCAP FINAL
    # ═══════════════════════════════════════════════════════════════════
    elapsed_min = (time.time() - t_global_start) / 60
    success = [r for r in all_results if r["error"] is None]
    failed = [r for r in all_results if r["error"] is not None]

    logger.info("\n" + "╔" + "═" * 68 + "╗")
    msg = f"✅ PIPELINE OPÉRATIONNEL TERMINÉ en {elapsed_min:.1f} min"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")

    logger.info(f"\n📊 Résultats :")
    logger.info(f"   Succès : {len(success)}/{len(dates)}")
    logger.info(f"   Échecs : {len(failed)}/{len(dates)}")

    if failed:
        logger.warning("\n⚠️ Runs en échec :")
        for r in failed:
            logger.warning(f"   • {r['run_dt'].strftime('%Y-%m-%d %Hz')} : {r['error']}")

    if success:
        logger.info("\n📁 Fichiers CSV produits :")
        for r in success:
            logger.info(f"   • {r['csv'].name}")

    logger.info(f"\n📁 Dossier sortie : {CSV_OUTPUT_DIR}")

    # Code de sortie : 0 si tout OK, 1 si au moins un échec
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompu par l'utilisateur")
        sys.exit(1)
