"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Pipeline COMPLET quotidien ERA5 (PRODUCTION)
FICHIER  : scripts/era5/run_daily_pipeline.py
RÔLE     : Pipeline complet de bout en bout : téléchargement CDS → export
           CSV (avec cumuls 6h + variables dérivées) → ingestion DB.
           Fait pour être lancé par cron automatiquement.
═══════════════════════════════════════════════════════════════════════════

USAGE EN PRODUCTION (CRON sur VPS OVH)
---------------------------------------
    # Lancé à 02h UTC chaque jour (heure creuse)
    # Calcule automatiquement J-6 pour garantir 24h complètes ERA5
    0 2 * * * cd /path/to/scripts && conda run -n meteo_ia \
              python -m era5.run_daily_pipeline

LOGIQUE AUTOMATIQUE
-------------------
Par défaut (sans --date) :
  - Calcule la date cible = aujourd'hui UTC - 6 jours
  - Pourquoi J-6 au lieu de J-5 (latence officielle ERA5T) ?
    → ERA5T à J-5 est parfois partiel (16h sur 24h)
    → J-6 garantit toujours 24h complètes
  - 1 jour de retard supplémentaire = impact négligeable

USAGE MANUEL
------------
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts

    # Mode auto (calcule J-6) → ERA5 du jour il y a 6 jours
    python -m era5.run_daily_pipeline

    # Mode manuel (backfill date spécifique)
    python -m era5.run_daily_pipeline --date 2026-04-19

    # Avec skip si fichiers déjà présents
    python -m era5.run_daily_pipeline --skip-existing

    # Skip l'ingestion DB (utile pour debug)
    python -m era5.run_daily_pipeline --no-db

PIPELINE COMPLET (3 ÉTAPES)
---------------------------
  1. Téléchargement CDS (J-1 + J en 1 requête, 5 vars × 48h)         ~30s-15min
  2. Export CSV (cumuls 6h + variables dérivées + 4 timestamps)       ~2s
  3. Ingestion CSV → PostgreSQL (UPSERT idempotent)                   ~5-10s

CHAQUE ÉTAPE A UN RETRY AUTOMATIQUE 3× AVEC PAUSE 30 MIN.

FICHIERS PRODUITS
-----------------
  - data/era5_raw/era5_YYYYMMDD_full.nc        (J : toutes vars × 24h)
  - data/era5_raw/era5_(YYYYMMDD-1)_tp_only.nc (J-1 : tp uniquement × 24h)
  - data/era5_csv/era5_YYYYMMDD.csv            (4 timestamps × 8 vars × 2925 pts)
  - DB era5_truth                              (+93 600 lignes)

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

# Imports des modules du pipeline ERA5
from era5.fetch_era5 import (
    fetch_era5_for_date,
    OUTPUT_DIR as FETCH_OUTPUT_DIR,
)
from era5.export_era5_csv import (
    export_era5_for_date,
    OUTPUT_DIR as CSV_OUTPUT_DIR,
)
from era5.ingest_era5_to_db import ingest_csv_to_db

# Import du helper de connexion DB (depuis utils/)
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db_connection import get_db_connection

# 🆕 Logging centralisé : console + fichier logs/era5.log (append, historique cumulatif)
from utils.logging_setup import setup_pipeline_logging
setup_pipeline_logging("era5")
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ───────────────────────────────────────────────────────────────────────────

# Latence ERA5 par défaut : J-6 (pour garantir 24h complètes)
ERA5_LATENCY_DAYS = 6

# Configuration retry (production = 30 min, dev = ajuste si besoin)
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
        description="Pipeline COMPLET quotidien ERA5 (PRODUCTION)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help="Date cible au format YYYY-MM-DD (défaut: aujourd'hui UTC - 6 jours)",
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


def get_target_date(args) -> datetime:
    """
    Calcule la date cible.

    - Si --date fourni : utilise cette date (mode manuel/backfill)
    - Sinon : calcule J-6 par défaut (mode auto production)
    """
    if args.date:
        # Mode manuel : date explicite
        try:
            return datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            logger.error(f"❌ Format de date invalide : {args.date} (attendu YYYY-MM-DD)")
            sys.exit(1)
    else:
    # Mode auto : J-6
        today_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        target = today_utc - timedelta(days=ERA5_LATENCY_DAYS)
        logger.info(
            f"   ℹ️  Mode auto : aujourd'hui UTC = {today_utc.date()} → "
            f"J-{ERA5_LATENCY_DAYS} = {target.date()}"
        )
        return target


# ───────────────────────────────────────────────────────────────────────────
# ÉTAPES DU PIPELINE (avec retry)
# ───────────────────────────────────────────────────────────────────────────

def step_fetch(target_date: datetime, skip_existing: bool) -> tuple:
    """Étape 1 : Téléchargement CDS (J-1 + J)."""
    logger.info(f"\n📥 [1/3] Téléchargement ERA5 pour {target_date.strftime('%Y-%m-%d')}")

    target_str = target_date.strftime("%Y%m%d")
    prev_str = (target_date - timedelta(days=1)).strftime("%Y%m%d")
    full_path = FETCH_OUTPUT_DIR / f"era5_{target_str}_full.nc"
    tp_prev_path = FETCH_OUTPUT_DIR / f"era5_{prev_str}_tp_only.nc"

    if skip_existing and full_path.exists() and tp_prev_path.exists():
        logger.info(f"   ✅ Fichiers déjà présents :")
        logger.info(f"      • {full_path.name}")
        logger.info(f"      • {tp_prev_path.name}")
        return full_path, tp_prev_path

    def _fetch():
        return fetch_era5_for_date(target_date)

    t0 = time.time()
    paths = retry(_fetch, f"fetch ERA5 {target_date.strftime('%Y-%m-%d')}")
    elapsed = time.time() - t0

    logger.info(f"   ✅ Téléchargement OK ({elapsed:.1f}s)")
    return paths


def step_export_csv(target_date: datetime, skip_existing: bool) -> Path:
    """Étape 2 : Export CSV (cumuls + variables dérivées)."""
    logger.info(f"\n📊 [2/3] Export CSV ERA5 pour {target_date.strftime('%Y-%m-%d')}")

    target_str = target_date.strftime("%Y%m%d")
    csv_path = CSV_OUTPUT_DIR / f"era5_{target_str}.csv"

    if skip_existing and csv_path.exists():
        logger.info(f"   ✅ {csv_path.name} déjà présent, skip")
        return csv_path

    def _export():
        # Note : export_era5_csv attend une date sans timezone
        target_date_naive = target_date.replace(tzinfo=None)
        return export_era5_for_date(target_date_naive)

    t0 = time.time()
    result = retry(_export, f"export CSV ERA5 {target_date.strftime('%Y-%m-%d')}")
    elapsed = time.time() - t0

    size_mb = result.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ {result.name} ({size_mb:.1f} Mo, {elapsed:.1f}s)")
    return result


def step_ingest_db(target_date: datetime, csv_path: Path) -> dict:
    """Étape 3 : Ingestion CSV → PostgreSQL."""
    logger.info(f"\n💾 [3/3] Ingestion DB pour {target_date.strftime('%Y-%m-%d')}")

    def _ingest():
        conn = get_db_connection()
        try:
            stats = ingest_csv_to_db(csv_path, conn, dry_run=False)
            return stats
        finally:
            conn.close()

    t0 = time.time()
    stats = retry(_ingest, f"DB ingest ERA5 {target_date.strftime('%Y-%m-%d')}")
    elapsed = time.time() - t0

    rows = stats.get("rows_affected", 0)
    logger.info(f"   ✅ Ingestion OK ({rows:,} lignes, {elapsed:.1f}s)")
    return stats


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def main():
    args = parse_arguments()
    target_date = get_target_date(args)
    prev_date = target_date - timedelta(days=1)

    # Banner
    logger.info("╔" + "═" * 68 + "╗")
    msg = "🌍 PIPELINE QUOTIDIEN ERA5 — PRODUCTION COMPLÈTE"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╠" + "═" * 68 + "╣")

    if args.date:
        msg = f"Mode      : MANUEL (--date {args.date})"
    else:
        msg = f"Mode      : AUTO (J-{ERA5_LATENCY_DAYS} calculé automatiquement)"
    logger.info(f"║  {msg:<66s}║")

    msg = f"Date cible: {target_date.strftime('%Y-%m-%d')} (J)"
    logger.info(f"║  {msg:<66s}║")
    msg = f"Téléchargé: {prev_date.strftime('%Y-%m-%d')} (J-1, pour cumul tp à 00h)"
    logger.info(f"║  {msg:<66s}║")
    msg = "Étapes    : Fetch CDS → Export CSV → Ingestion DB"
    logger.info(f"║  {msg:<66s}║")
    msg = f"Retry     : {RETRY_MAX_ATTEMPTS}x (pause {RETRY_DELAY_SECONDS}s)"
    logger.info(f"║  {msg:<66s}║")
    msg = f"DB        : {'SKIP' if args.no_db else 'ENABLED'}"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")

    t_start = time.time()

    try:
        # ═══ ÉTAPE 1 : Fetch ═══
        full_path, tp_prev_path = step_fetch(target_date, args.skip_existing)

        # ═══ ÉTAPE 2 : Export CSV ═══
        csv_path = step_export_csv(target_date, args.skip_existing)

        # ═══ ÉTAPE 3 : Ingestion DB ═══
        ingest_stats = None
        if not args.no_db:
            ingest_stats = step_ingest_db(target_date, csv_path)
        else:
            logger.info("\n💾 [3/3] Ingestion DB SKIPPED (--no-db)")

        # ═══ RÉCAP ═══
        elapsed_min = (time.time() - t_start) / 60
        logger.info("\n" + "╔" + "═" * 68 + "╗")
        msg = f"✅ PIPELINE ERA5 COMPLET OK en {elapsed_min:.1f} min"
        logger.info(f"║  {msg:<66s}║")
        logger.info("╚" + "═" * 68 + "╝")
        logger.info(f"\n📁 Fichiers produits :")
        logger.info(f"   • NetCDF J    : {full_path}")
        logger.info(f"   • NetCDF J-1  : {tp_prev_path}")
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
        msg = f"❌ PIPELINE ERA5 ÉCHEC après {elapsed_min:.1f} min"
        logger.error(f"║  {msg:<66s}║")
        logger.error("╚" + "═" * 68 + "╝")
        logger.error(f"\nErreur : {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
