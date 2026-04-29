"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Pipeline COMPLET quotidien AROME (PRODUCTION)
FICHIER  : scripts/arome/run_daily_pipeline.py
RÔLE     : Pipeline complet de bout en bout : téléchargement GRIB2 → parsing
           NetCDF → export CSV → ingestion DB.
           Fait pour être lancé par cron automatiquement.
═══════════════════════════════════════════════════════════════════════════

USAGE EN PRODUCTION (CRON sur VPS OVH — timezone UTC pur)
---------------------------------------------------------
    # 00h00 UTC chaque jour (= 02h00 Paris été / 01h00 Paris hiver)
    0 0 * * * cd /path/to/scripts && conda run -n meteo_ia \
              python -m arome.run_daily_pipeline

LOGIQUE AUTOMATIQUE (mode auto sans --date)
-------------------------------------------
RÈGLE : on prend toujours le DERNIER run 18z UTC complet et publié.

Le run 18z UTC AROME (data.gouv.fr) est publié vers ~22h UTC (~4h après).
Marge de sécurité : on attend 23h UTC (= 1h après publication théorique).

Algorithme :
  - Si heure actuelle UTC >= 23h → on prend le run 18z UTC du jour MÊME
  - Sinon                        → on prend le run 18z UTC du jour PRÉCÉDENT

Vérification avec cron à 00h00 UTC :
  - Été  (UTC+2) : 00h00 UTC = 02h00 Paris (J+1 Paris)
                   → hour=0, < 23, veille UTC = J-1 UTC
                   → Run 18z UTC publié il y a ~2h ✅
  - Hiver (UTC+1): 00h00 UTC = 01h00 Paris (J+1 Paris)
                   → hour=0, < 23, veille UTC = J-1 UTC
                   → Run 18z UTC publié il y a ~2h ✅

Le run 18z UTC J-1 fournit les prédictions pour J aux 4 timestamps :
  - T+6h  = J 00h UTC
  - T+12h = J 06h UTC
  - T+18h = J 12h UTC
  - T+24h = J 18h UTC

USAGE MANUEL
------------
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts

    # Mode auto (= dernier run 18z UTC dispo via logique seuil 23h UTC)
    python -m arome.run_daily_pipeline

    # Mode manuel (backfill date spécifique)
    python -m arome.run_daily_pipeline --date 2026-04-23

    # Avec skip si fichiers déjà présents
    python -m arome.run_daily_pipeline --skip-existing

    # Skip l'ingestion DB (utile pour debug)
    python -m arome.run_daily_pipeline --no-db

PIPELINE COMPLET (4 ÉTAPES)
---------------------------
  1. Téléchargement GRIB2 (4 fichiers SP1, ~200 Mo)         ~10s
  2. Parsing GRIB2 → NetCDF (1 fichier propre, ~250 Ko)     ~7s
  3. Export CSV (93 600 lignes)                             ~2s
  4. Ingestion CSV → PostgreSQL                             ~7s

CHAQUE ÉTAPE A UN RETRY AUTOMATIQUE 3× AVEC PAUSE 30 MIN.

CODE DE SORTIE
--------------
  0 : succès complet (toutes étapes OK)
  1 : au moins une étape a échoué après 3 retries
═══════════════════════════════════════════════════════════════════════════
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable

# Imports des modules du pipeline AROME
from arome.fetch_arome import (
    fetch_one_run,
    OUTPUT_DIR as FETCH_OUTPUT_DIR,
)
from arome.parse_arome import (
    parse_and_save_run,
    get_output_path as get_nc_path,
    OUTPUT_DIR as PARSE_OUTPUT_DIR,
)
from arome.export_arome_csv import (
    export_one_run,
    get_output_path as get_csv_path,
    OUTPUT_DIR as CSV_OUTPUT_DIR,
)
from arome.ingest_arome_to_db import ingest_csv_to_db

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db_connection import get_db_connection

# 🆕 Logging centralisé : console + fichier logs/arome.log (append, historique cumulatif)
from utils.logging_setup import setup_pipeline_logging
setup_pipeline_logging("arome")
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ───────────────────────────────────────────────────────────────────────────

# Heure du run par défaut (18z = prédictions pour les 4 timestamps de J)
DEFAULT_RUN_HOUR = 18

# Heure UTC à partir de laquelle on considère que le run 18z UTC du jour MÊME est publié
# 18z UTC AROME publié vers 22h UTC, on attend 1h de marge → seuil = 23h UTC
AROME_PUBLICATION_THRESHOLD_HOUR_UTC = 23

# Configuration retry
RETRY_MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1800  # 30 min en production


# ───────────────────────────────────────────────────────────────────────────
# RETRY DECORATOR
# ───────────────────────────────────────────────────────────────────────────

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
        description="Pipeline COMPLET quotidien AROME (PRODUCTION)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help="Date du run au format YYYY-MM-DD (défaut: dernier run 18z UTC dispo via logique seuil 23h UTC)",
    )
    parser.add_argument(
        "--run", type=int, default=DEFAULT_RUN_HOUR, choices=[0, 3, 6, 9, 12, 15, 18, 21],
        help=f"Heure UTC du run (défaut: {DEFAULT_RUN_HOUR}z = prédictions J+1)",
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
      Utilise la date fournie + heure --run (défaut 18).

    Mode auto (sans --date) :
      Récupère le DERNIER run 18z UTC complet et publié, selon la logique :
        - Si heure actuelle UTC >= 23h → run 18z UTC du jour MÊME
        - Sinon                        → run 18z UTC du jour PRÉCÉDENT
      
      Cette logique garantit qu'on demande toujours un run publié depuis ≥ 1h
      (le run 18z UTC AROME est typiquement publié vers 22h UTC, dispo à 23h UTC).
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
            hour=args.run, minute=0, second=0,
            tzinfo=timezone.utc,
        )

    # Mode auto : logique seuil 23h UTC
    now_utc = datetime.now(timezone.utc)

    if now_utc.hour >= AROME_PUBLICATION_THRESHOLD_HOUR_UTC:
        # >= 23h UTC : le run 18z UTC du jour MÊME est dispo
        target_date = now_utc.date()
        logger.info(
            f"   ℹ️  Mode auto : il est {now_utc.strftime('%H:%M')} UTC "
            f"(>= {AROME_PUBLICATION_THRESHOLD_HOUR_UTC}h UTC) → "
            f"run 18z UTC du jour MÊME ({target_date})"
        )
    else:
        # < 23h UTC : le run 18z UTC du jour MÊME pas encore garanti, on prend la veille
        target_date = (now_utc - timedelta(days=1)).date()
        logger.info(
            f"   ℹ️  Mode auto : il est {now_utc.strftime('%H:%M')} UTC "
            f"(< {AROME_PUBLICATION_THRESHOLD_HOUR_UTC}h UTC) → "
            f"run 18z UTC du jour PRÉCÉDENT ({target_date})"
        )

    return datetime(
        year=target_date.year, month=target_date.month, day=target_date.day,
        hour=args.run, minute=0, second=0,
        tzinfo=timezone.utc,
    )


# ───────────────────────────────────────────────────────────────────────────
# ÉTAPES DU PIPELINE (avec retry)
# ───────────────────────────────────────────────────────────────────────────

def step_fetch(run_dt: datetime, skip_existing: bool) -> dict:
    """Étape 1 : Téléchargement des 4 GRIB2."""
    logger.info(f"\n📥 [1/4] Téléchargement GRIB2 AROME run {run_dt.strftime('%Y-%m-%d %Hz UTC')}")

    def _fetch():
        results = fetch_one_run(run_dt, skip_existing=skip_existing)
        n_ok = len(results["success"]) + len(results["skipped"])
        if n_ok != 4:
            raise RuntimeError(f"Fetch incomplet : {n_ok}/4 fichiers OK")
        return results

    t0 = time.time()
    results = retry(_fetch, f"fetch AROME {run_dt.strftime('%Y-%m-%d %Hz')}")
    elapsed = time.time() - t0

    n_ok = len(results["success"]) + len(results["skipped"])
    logger.info(f"   ✅ Fetch OK (4/4 fichiers, {elapsed:.1f}s)")
    return results


def step_parse(run_dt: datetime, skip_existing: bool) -> Path:
    """Étape 2 : Parsing GRIB2 → NetCDF."""
    logger.info(f"\n🔧 [2/4] Parsing AROME GRIB2 → NetCDF run {run_dt.strftime('%Y-%m-%d %Hz')}")

    def _parse():
        return parse_and_save_run(run_dt, skip_existing=skip_existing)

    t0 = time.time()
    nc_path = retry(_parse, f"parse AROME {run_dt.strftime('%Y-%m-%d %Hz')}")
    elapsed = time.time() - t0

    size_kb = nc_path.stat().st_size / 1024
    logger.info(f"   ✅ {nc_path.name} ({size_kb:.0f} Ko, {elapsed:.1f}s)")
    return nc_path


def step_export_csv(run_dt: datetime, skip_existing: bool) -> Path:
    """Étape 3 : Export NetCDF → CSV."""
    logger.info(f"\n📊 [3/4] Export CSV AROME run {run_dt.strftime('%Y-%m-%d %Hz')}")

    def _export():
        return export_one_run(run_dt, skip_existing=skip_existing)

    t0 = time.time()
    csv_path = retry(_export, f"export CSV AROME {run_dt.strftime('%Y-%m-%d %Hz')}")
    elapsed = time.time() - t0

    size_mb = csv_path.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ {csv_path.name} ({size_mb:.1f} Mo, {elapsed:.1f}s)")
    return csv_path


def step_ingest_db(run_dt: datetime, csv_path: Path) -> dict:
    """Étape 4 : Ingestion CSV → PostgreSQL."""
    logger.info(f"\n💾 [4/4] Ingestion DB run {run_dt.strftime('%Y-%m-%d %Hz')}")

    def _ingest():
        conn = get_db_connection()
        try:
            stats = ingest_csv_to_db(csv_path, conn, dry_run=False)
            return stats
        finally:
            conn.close()

    t0 = time.time()
    stats = retry(_ingest, f"DB ingest AROME {run_dt.strftime('%Y-%m-%d %Hz')}")
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
    target_date = run_dt + timedelta(days=1)

    # Banner
    logger.info("╔" + "═" * 68 + "╗")
    msg = "🇫🇷 PIPELINE QUOTIDIEN AROME — PRODUCTION COMPLÈTE"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╠" + "═" * 68 + "╣")

    if args.date:
        msg = f"Mode      : MANUEL (--date {args.date})"
    else:
        msg = "Mode      : AUTO (logique seuil 23h UTC)"
    logger.info(f"║  {msg:<66s}║")

    msg = f"Run       : {run_dt.strftime('%Y-%m-%d %Hz UTC')}"
    logger.info(f"║  {msg:<66s}║")
    msg = f"Prédit    : jusqu'au {target_date.strftime('%Y-%m-%d %Hz UTC')} (J+1)"
    logger.info(f"║  {msg:<66s}║")
    msg = "Étapes    : Fetch → Parse → Export CSV → Ingestion DB"
    logger.info(f"║  {msg:<66s}║")
    msg = f"Retry     : {RETRY_MAX_ATTEMPTS}x (pause {RETRY_DELAY_SECONDS}s)"
    logger.info(f"║  {msg:<66s}║")
    msg = f"DB        : {'SKIP' if args.no_db else 'ENABLED'}"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")

    t_start = time.time()

    try:
        # ═══ ÉTAPE 1 : Fetch ═══
        step_fetch(run_dt, args.skip_existing)

        # ═══ ÉTAPE 2 : Parse ═══
        nc_path = step_parse(run_dt, args.skip_existing)

        # ═══ ÉTAPE 3 : Export CSV ═══
        csv_path = step_export_csv(run_dt, args.skip_existing)

        # ═══ ÉTAPE 4 : Ingestion DB ═══
        ingest_stats = None
        if not args.no_db:
            ingest_stats = step_ingest_db(run_dt, csv_path)
        else:
            logger.info("\n💾 [4/4] Ingestion DB SKIPPED (--no-db)")

        # ═══ RÉCAP ═══
        elapsed_min = (time.time() - t_start) / 60
        logger.info("\n" + "╔" + "═" * 68 + "╗")
        msg = f"✅ PIPELINE AROME COMPLET OK en {elapsed_min:.1f} min"
        logger.info(f"║  {msg:<66s}║")
        logger.info("╚" + "═" * 68 + "╝")
        logger.info(f"\n📁 Fichiers produits :")
        logger.info(f"   • NetCDF     : {nc_path}")
        logger.info(f"   • CSV DB     : {csv_path}")
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
        msg = f"❌ PIPELINE AROME ÉCHEC après {elapsed_min:.1f} min"
        logger.error(f"║  {msg:<66s}║")
        logger.error("╚" + "═" * 68 + "╝")
        logger.error(f"\nErreur : {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
