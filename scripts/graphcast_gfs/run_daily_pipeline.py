"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Pipeline COMPLET quotidien GraphCast (PRODUCTION)
FICHIER  : scripts/graphcast_gfs/run_daily_pipeline.py
RÔLE     : Pipeline complet de bout en bout : collecte GDAS → inférence
           GraphCast → export CSV → INGESTION DB.
           Fait pour être lancé par cron automatiquement.
═══════════════════════════════════════════════════════════════════════════

USAGE EN PRODUCTION (CRON sur VPS OVH — timezone UTC pur)
---------------------------------------------------------
    # 23h30 UTC chaque jour (= 01h30 Paris été / 00h30 Paris hiver)
    30 23 * * * cd /path/to/scripts && conda run -n meteo_ia \
                python -m graphcast_gfs.run_daily_pipeline

LOGIQUE AUTOMATIQUE (mode auto sans --date)
-------------------------------------------
RÈGLE : on prend toujours le DERNIER run 18z UTC complet et publié.

Le run 18z UTC du jour J est publié vers ~22h UTC (~4h après le run).
Marge de sécurité : on attend 23h UTC (= 1h après publication théorique).

Algorithme :
  - Si heure actuelle UTC >= 23h → on prend le run 18z UTC du jour MÊME
  - Sinon                        → on prend le run 18z UTC du jour PRÉCÉDENT

Vérification avec cron à 23h30 UTC :
  - Été  (UTC+2) : 23h30 UTC = 01h30 Paris (J+1 Paris)
                   → hour=23, ≥ 23, jour MÊME UTC = veille Paris
                   → Run 18z UTC publié il y a ~1h30 ✅
  - Hiver (UTC+1): 23h30 UTC = 00h30 Paris (J+1 Paris)
                   → hour=23, ≥ 23, jour MÊME UTC = veille Paris
                   → Run 18z UTC publié il y a ~1h30 ✅

USAGE MANUEL
------------
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts

    # Mode auto (= dernier run 18z UTC dispo selon logique seuil 23h UTC)
    python -m graphcast_gfs.run_daily_pipeline

    # Date spécifique (backfill)
    python -m graphcast_gfs.run_daily_pipeline --date 2026-04-24

    # Avec skip si fichiers déjà présents
    python -m graphcast_gfs.run_daily_pipeline --skip-existing

    # Skip l'ingestion DB (utile pour debug)
    python -m graphcast_gfs.run_daily_pipeline --no-db

PIPELINE COMPLET (5 ÉTAPES)
---------------------------
  1. Téléchargement GDAS NOMADS  (T-6h + T0 = 28 fichiers GRIB2)   ~45s
  2. Parsing GRIB2 → NetCDF                                         ~4s
  3. Inférence GraphCast Operational (4 horizons J+1)               ~1-8 min
  4. Export CSV format DB (93 600 lignes)                           ~1s
  5. Ingestion CSV → PostgreSQL (UPSERT idempotent)                 ~3s

CHAQUE ÉTAPE A UN RETRY AUTOMATIQUE 3× AVEC PAUSE 30 MIN.

CODE DE SORTIE
--------------
  0 : succès complet (toutes étapes OK)
  1 : au moins une étape a échoué après 3 retries
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
from typing import Callable

# Imports des modules du pipeline
from graphcast_gfs.fetch_gdas_nomads import download_run, OUTPUT_DIR as FETCH_OUTPUT_DIR
from graphcast_gfs.parse_gdas import assemble_run, OUTPUT_DIR as PARSE_OUTPUT_DIR
from graphcast_gfs.export_graphcast_csv import export_run_to_csv, OUTPUT_DIR as CSV_OUTPUT_DIR
from graphcast_gfs.inference_graphcast import (
    load_graphcast_model,
    build_jit_functions,
    run_inference_single_date,
    OUTPUT_DIR as INFERENCE_OUTPUT_DIR,
)
from graphcast_gfs.ingest_graphcast_to_db import ingest_csv_to_db

# Import du helper de connexion DB (depuis utils/)
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db_connection import get_db_connection

# 🆕 Logging centralisé : console + fichier logs/graphcast.log (append, historique cumulatif)
from utils.logging_setup import setup_pipeline_logging
setup_pipeline_logging("graphcast")
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ───────────────────────────────────────────────────────────────────────────

RETRY_MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1800  # 30 min en production

# Heure UTC à partir de laquelle on considère que le run 18z UTC du jour MÊME est publié
# 18z UTC publié vers 22h UTC, on attend 1h de marge → seuil = 23h UTC
GDAS_PUBLICATION_THRESHOLD_HOUR_UTC = 23


def retry(fn: Callable, name: str):
    """Exécute une fonction avec retry automatique 3× pause 30 min."""
    last_exception = None
    for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
        try:
            if attempt > 1:
                logger.warning(f"   🔄 Tentative {attempt}/{RETRY_MAX_ATTEMPTS} pour '{name}'...")
            return fn()
        except Exception as e:
            last_exception = e
            logger.error(f"   ⚠️  Tentative {attempt}/{RETRY_MAX_ATTEMPTS} échouée pour '{name}' : {e}")
            if attempt < RETRY_MAX_ATTEMPTS:
                logger.info(f"   ⏳ Pause {RETRY_DELAY_SECONDS}s avant prochaine tentative...")
                time.sleep(RETRY_DELAY_SECONDS)

    logger.error(f"   ❌ ÉCHEC DÉFINITIF après {RETRY_MAX_ATTEMPTS} tentatives : {name}")
    raise last_exception


# ───────────────────────────────────────────────────────────────────────────
# GESTION DES ARGUMENTS CLI
# ───────────────────────────────────────────────────────────────────────────

def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Pipeline COMPLET quotidien GraphCast (PRODUCTION)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help="Date du run au format YYYY-MM-DD (défaut: dernier run 18z UTC dispo via logique seuil 23h UTC)",
    )
    parser.add_argument(
        "--hour", type=int, default=18, choices=[0, 6, 12, 18],
        help="Heure UTC du run (défaut: 18 = opérationnel J+1)",
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="Skip les étapes dont le fichier de sortie existe déjà",
    )
    parser.add_argument(
        "--no-db", action="store_true",
        help="Skip l'ingestion DB (utile pour debug)",
    )
    return parser.parse_args()


def get_run_datetime(args) -> datetime:
    """
    Calcule le datetime du run.

    Mode manuel (--date fourni) :
      Utilise la date fournie + heure --hour (défaut 18).

    Mode auto (sans --date) :
      Récupère le DERNIER run 18z UTC complet et publié, selon la logique :
        - Si heure actuelle UTC >= 23h → run 18z UTC du jour MÊME
        - Sinon                        → run 18z UTC du jour PRÉCÉDENT
      
      Cette logique garantit qu'on demande toujours un run publié depuis ≥ 1h
      (le run 18z UTC est typiquement publié vers 22h UTC, donc dispo à 23h UTC).
    """
    if args.date is not None:
        # Mode manuel
        try:
            run_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"❌ Format de date invalide : {args.date} (attendu YYYY-MM-DD)")
            sys.exit(1)

        return datetime(
            year=run_date.year, month=run_date.month, day=run_date.day,
            hour=args.hour, minute=0, second=0,
            tzinfo=timezone.utc,
        )

    # Mode auto : logique seuil 23h UTC
    now_utc = datetime.now(timezone.utc)

    if now_utc.hour >= GDAS_PUBLICATION_THRESHOLD_HOUR_UTC:
        # >= 23h UTC : le run 18z UTC du jour MÊME est dispo
        target_date = now_utc.date()
        logger.info(
            f"   ℹ️  Mode auto : il est {now_utc.strftime('%H:%M')} UTC "
            f"(>= {GDAS_PUBLICATION_THRESHOLD_HOUR_UTC}h UTC) → "
            f"run 18z UTC du jour MÊME ({target_date})"
        )
    else:
        # < 23h UTC : le run 18z UTC du jour MÊME pas encore garanti, on prend la veille
        target_date = (now_utc - timedelta(days=1)).date()
        logger.info(
            f"   ℹ️  Mode auto : il est {now_utc.strftime('%H:%M')} UTC "
            f"(< {GDAS_PUBLICATION_THRESHOLD_HOUR_UTC}h UTC) → "
            f"run 18z UTC du jour PRÉCÉDENT ({target_date})"
        )

    return datetime(
        year=target_date.year, month=target_date.month, day=target_date.day,
        hour=args.hour, minute=0, second=0,
        tzinfo=timezone.utc,
    )


# ───────────────────────────────────────────────────────────────────────────
# ÉTAPES DU PIPELINE (avec retry)
# ───────────────────────────────────────────────────────────────────────────

def step_fetch(run_dt: datetime, skip_existing: bool) -> Path:
    """Étape 1 : Téléchargement GDAS via NOMADS."""
    logger.info(f"\n📥 [1/5] Collecte GDAS run {run_dt.strftime('%Y-%m-%d %Hz UTC')}")

    run_dir = FETCH_OUTPUT_DIR / run_dt.strftime("%Y%m%d_%H")

    if skip_existing and run_dir.exists():
        n_files = sum(1 for _ in run_dir.rglob("*.grib2"))
        if n_files >= 28:
            logger.info(f"   ✅ Déjà présent ({n_files}/28 fichiers), skip")
            return run_dir

    def _fetch():
        # IMPORTANT : download_run attend un datetime sans timezone (ou en UTC implicite)
        # On passe une copie sans tzinfo pour compatibilité
        run_dt_naive = run_dt.replace(tzinfo=None)
        success = download_run(run_dt_naive, run_dir)
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
    """Étape 2 : Parsing GRIB2 → NetCDF."""
    logger.info(f"\n🔧 [2/5] Parsing GRIB2 → NetCDF run {run_dt.strftime('%Y-%m-%d %Hz')}")

    date_str = run_dt.strftime("%Y%m%d_%H")
    output_path = PARSE_OUTPUT_DIR / f"gdas_{date_str}.nc"

    if skip_existing and output_path.exists():
        logger.info(f"   ✅ {output_path.name} existe déjà, skip")
        return output_path

    PARSE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _parse():
        run_dt_naive = run_dt.replace(tzinfo=None)
        ds = assemble_run(run_dt_naive, run_dir)
        ds.to_netcdf(output_path)
        return output_path

    t0 = time.time()
    result = retry(_parse, f"parse {run_dt.strftime('%Y-%m-%d %Hz')}")
    elapsed = time.time() - t0

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ {output_path.name} ({size_mb:.1f} Mo, {elapsed:.1f}s)")
    return result


def step_inference(run_dt, gdas_nc_path, run_forward_jitted, task_config,
                   static_vars_global, skip_existing):
    """Étape 3 : Inférence GraphCast."""
    logger.info(f"\n🤖 [3/5] Inférence GraphCast run {run_dt.strftime('%Y-%m-%d %Hz')}")

    date_str = run_dt.strftime("%Y%m%d")
    hour_str = run_dt.strftime("%H")
    output_path = INFERENCE_OUTPUT_DIR / f"graphcast_{date_str}_{hour_str}h.nc"

    if skip_existing and output_path.exists():
        logger.info(f"   ✅ {output_path.name} existe déjà, skip")
        return output_path

    INFERENCE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _infer():
        run_dt_naive = run_dt.replace(tzinfo=None)
        return run_inference_single_date(
            gdas_nc_path, run_dt_naive, run_forward_jitted, task_config,
            static_vars_global, INFERENCE_OUTPUT_DIR,
        )

    t0 = time.time()
    result = retry(_infer, f"inference {run_dt.strftime('%Y-%m-%d %Hz')}")
    elapsed = time.time() - t0

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ {output_path.name} ({size_mb:.1f} Mo, {elapsed:.1f}s)")
    return result


def step_csv(run_dt, prediction_nc_path, skip_existing):
    """Étape 4 : Export CSV format DB."""
    logger.info(f"\n📊 [4/5] Export CSV run {run_dt.strftime('%Y-%m-%d %Hz')}")

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


def step_ingest_db(run_dt, csv_path):
    """Étape 5 : Ingestion CSV → PostgreSQL."""
    logger.info(f"\n💾 [5/5] Ingestion DB run {run_dt.strftime('%Y-%m-%d %Hz')}")

    def _ingest():
        conn = get_db_connection()
        try:
            stats = ingest_csv_to_db(csv_path, conn, dry_run=False)
            return stats
        finally:
            conn.close()

    t0 = time.time()
    stats = retry(_ingest, f"db ingest {run_dt.strftime('%Y-%m-%d %Hz')}")
    elapsed = time.time() - t0

    rows = stats.get("rows_affected", 0)
    logger.info(f"   ✅ Ingestion OK ({rows:,} lignes, {elapsed:.1f}s)")
    return stats


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def main():
    args = parse_arguments()
    run_dt = get_run_datetime(args)
    target_date = run_dt + timedelta(hours=24)
    t_minus_6h = run_dt - timedelta(hours=6)

    # Banner
    logger.info("╔" + "═" * 68 + "╗")
    msg = "🚀 PIPELINE QUOTIDIEN GRAPHCAST — PRODUCTION COMPLÈTE"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╠" + "═" * 68 + "╣")

    if args.date:
        msg = f"Mode      : MANUEL (--date {args.date})"
    else:
        msg = "Mode      : AUTO (logique seuil 23h UTC)"
    logger.info(f"║  {msg:<66s}║")

    msg = f"Run       : {run_dt.strftime('%Y-%m-%d %Hz UTC')}"
    logger.info(f"║  {msg:<66s}║")
    msg = f"T-6h      : {t_minus_6h.strftime('%Y-%m-%d %Hz UTC')}"
    logger.info(f"║  {msg:<66s}║")
    msg = f"T0        : {run_dt.strftime('%Y-%m-%d %Hz UTC')}"
    logger.info(f"║  {msg:<66s}║")
    msg = f"Prédit    : jusqu'au {target_date.strftime('%Y-%m-%d %Hz UTC')} (J+1)"
    logger.info(f"║  {msg:<66s}║")
    msg = f"Étapes    : Fetch → Parse → Inference → CSV → DB"
    logger.info(f"║  {msg:<66s}║")
    msg = f"Retry     : {RETRY_MAX_ATTEMPTS}x (pause {RETRY_DELAY_SECONDS}s)"
    logger.info(f"║  {msg:<66s}║")
    msg = f"DB        : {'SKIP' if args.no_db else 'ENABLED'}"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")

    t_start = time.time()

    try:
        # ═══ ÉTAPE 1 : Fetch ═══
        run_dir = step_fetch(run_dt, args.skip_existing)

        # ═══ ÉTAPE 2 : Parse ═══
        gdas_nc_path = step_parse(run_dt, run_dir, args.skip_existing)

        # ═══ Chargement modèle (avant inférence) ═══
        logger.info("\n📦 Chargement du modèle GraphCast...")
        (params, state, model_config, task_config, stats, static_vars_global) = load_graphcast_model()

        logger.info("\n🔧 Construction JIT...")
        run_forward_jitted = build_jit_functions(params, state, model_config, task_config, stats)
        logger.info("   ✅ JIT construit (compilation à la 1ère inférence)")

        # ═══ ÉTAPE 3 : Inférence ═══
        prediction_nc_path = step_inference(
            run_dt, gdas_nc_path, run_forward_jitted, task_config,
            static_vars_global, args.skip_existing,
        )

        # ═══ ÉTAPE 4 : CSV ═══
        csv_path = step_csv(run_dt, prediction_nc_path, args.skip_existing)

        # ═══ ÉTAPE 5 : Ingestion DB ═══
        ingest_stats = None
        if not args.no_db:
            ingest_stats = step_ingest_db(run_dt, csv_path)
        else:
            logger.info("\n💾 [5/5] Ingestion DB SKIPPED (--no-db)")

        # ═══ RÉCAP ═══
        elapsed_min = (time.time() - t_start) / 60
        logger.info("\n" + "╔" + "═" * 68 + "╗")
        msg = f"✅ PIPELINE COMPLET OK en {elapsed_min:.1f} min"
        logger.info(f"║  {msg:<66s}║")
        logger.info("╚" + "═" * 68 + "╝")
        logger.info(f"\n📁 Fichiers produits :")
        logger.info(f"   • GDAS NetCDF : {gdas_nc_path}")
        logger.info(f"   • Prédiction  : {prediction_nc_path}")
        logger.info(f"   • CSV DB      : {csv_path}")
        if ingest_stats:
            logger.info(f"\n💾 Ingestion DB :")
            logger.info(f"   • Lignes ingérées : {ingest_stats.get('rows_affected', 0):,}")

        # ═══════════════════════════════════════════════════════════════════
        # HOOK : régénération automatique du JSON statique frontend
        # Ne s'exécute que si la DB a été modifiée (skippé si --no-db).
        # Tolérant aux pannes : ne fait pas échouer le pipeline si le backend
        # Express n'est pas lancé (warning loggé, exit 0 conservé).
        # ═══════════════════════════════════════════════════════════════════
        if ingest_stats:
            try:
                from utils.regenerate_frontend_json import regenerate_frontend_json
                logger.info("\n🔄 Hook : régénération JSON statique frontend...")
                regenerate_frontend_json()
            except Exception as hook_err:
                logger.warning(f"   ⚠️  Hook frontend ignoré : {hook_err}")

        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompu par l'utilisateur")
        sys.exit(1)

    except Exception as e:
        elapsed_min = (time.time() - t_start) / 60
        logger.error(f"\n" + "╔" + "═" * 68 + "╗")
        msg = f"❌ PIPELINE ÉCHEC après {elapsed_min:.1f} min"
        logger.error(f"║  {msg:<66s}║")
        logger.error("╚" + "═" * 68 + "╝")
        logger.error(f"\nErreur : {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
