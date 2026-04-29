"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Pipeline COMPLET quotidien MAE (PRODUCTION)
FICHIER  : scripts/mae/run_daily_pipeline.py
RÔLE     : Calcule automatiquement les métriques MAE/RMSE/Bias pour la
           date qui vient juste d'avoir sa vérité ERA5 ingérée (J-6).
═══════════════════════════════════════════════════════════════════════════

USAGE EN PRODUCTION (CRON sur VPS OVH)
---------------------------------------
    # Lancé à 03h UTC chaque jour (1h après ERA5)
    0 3 * * * cd /path/to/scripts && conda run -n meteo_ia \
              python -m mae.run_daily_pipeline

LOGIQUE AUTOMATIQUE
-------------------
Par défaut (sans --date) :
  - Calcule la date cible = aujourd'hui UTC - 6 jours (= dernière vérité ERA5 dispo)
  - Lance les 2 comparaisons :
    * graphcast_vs_era5
    * arome_vs_era5

USAGE MANUEL
------------
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts

    # Mode auto (calcule J-6)
    python -m mae.run_daily_pipeline

    # Mode manuel (backfill date spécifique)
    python -m mae.run_daily_pipeline --date 2026-04-17

    # Skip une comparaison
    python -m mae.run_daily_pipeline --skip-arome

PIPELINE COMPLET (3 ÉTAPES par comparaison)
-------------------------------------------
  1. Lecture prédictions depuis DB (graphcast_predictions_fresh ou arome_forecasts_fresh)
  2. Lecture vérité ERA5 depuis DB (era5_truth)
  3. Calcul MAE/RMSE/Bias par (variable × horizon) + UPSERT en DB

CHAQUE CALCUL A UN RETRY AUTOMATIQUE 3× AVEC PAUSE 30 MIN.

CODE DE SORTIE
--------------
  0 : succès complet
  1 : au moins une comparaison a échoué après 3 retries
═══════════════════════════════════════════════════════════════════════════
"""

import argparse
import logging
import sys
import time
import warnings
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Callable

# Suppression du warning pandas/SQLAlchemy bénin
warnings.filterwarnings("ignore", message=".*SQLAlchemy.*")

# Imports du module mae
from mae.compute_mae import (
    compute_one_comparison,
    show_table_state,
    COMPARISONS,
)

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db_connection import get_db_connection

# 🆕 Logging centralisé : console + fichier logs/mae.log (append, historique cumulatif)
from utils.logging_setup import setup_pipeline_logging
setup_pipeline_logging("mae")
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ───────────────────────────────────────────────────────────────────────────

# Latence MAE par défaut : J-6 (= dernière vérité ERA5 dispo, cohérent avec ERA5)
MAE_LATENCY_DAYS = 6

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
        description="Pipeline quotidien MAE (PRODUCTION)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help=f"Date d'évaluation au format YYYY-MM-DD (défaut: aujourd'hui UTC - {MAE_LATENCY_DAYS} jours)",
    )
    parser.add_argument(
        "--skip-graphcast", action="store_true",
        help="Skip la comparaison graphcast_vs_era5",
    )
    parser.add_argument(
        "--skip-arome", action="store_true",
        help="Skip la comparaison arome_vs_era5",
    )
    parser.add_argument(
        "--no-validation", action="store_true",
        help="Skip la validation post-calcul",
    )
    return parser.parse_args()


def get_target_date(args) -> date:
    """Calcule la date cible (mode auto J-6 ou manuel)."""
    if args.date:
        try:
            return datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"❌ Format de date invalide : {args.date} (attendu YYYY-MM-DD)")
            sys.exit(1)
    else:
        # Mode auto : J-6
        today_utc = datetime.now(timezone.utc).date()
        target = today_utc - timedelta(days=MAE_LATENCY_DAYS)
        return target


# ───────────────────────────────────────────────────────────────────────────
# ÉTAPE D'UNE COMPARAISON (avec retry)
# ───────────────────────────────────────────────────────────────────────────

def run_comparison(conn, comparison_name: str, target_date: date) -> dict:
    """Lance une comparaison avec retry."""
    label = COMPARISONS[comparison_name]["label"]
    logger.info(f"\n📊 {label}")

    def _compute():
        return compute_one_comparison(conn, comparison_name, target_date, dry_run=False)

    t0 = time.time()
    result = retry(_compute, f"compute MAE {label}")
    elapsed = time.time() - t0

    n_upserted = result.get("rows_upserted", 0)
    logger.info(f"   ✅ {label} OK ({n_upserted} lignes upserted, {elapsed:.1f}s)")
    return result


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def main():
    args = parse_arguments()
    target_date = get_target_date(args)

    # Banner
    logger.info("╔" + "═" * 68 + "╗")
    msg = "📊 PIPELINE QUOTIDIEN MAE — PRODUCTION COMPLÈTE"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╠" + "═" * 68 + "╣")

    if args.date:
        msg = f"Mode      : MANUEL (--date {args.date})"
    else:
        msg = f"Mode      : AUTO (J-{MAE_LATENCY_DAYS} calculé automatiquement)"
    logger.info(f"║  {msg:<66s}║")

    msg = f"Date cible: {target_date}"
    logger.info(f"║  {msg:<66s}║")

    comp_status = []
    if not args.skip_graphcast:
        comp_status.append("graphcast_vs_era5")
    if not args.skip_arome:
        comp_status.append("arome_vs_era5")
    msg = f"Compar.   : {' + '.join(comp_status) if comp_status else '(aucune!)'}"
    logger.info(f"║  {msg:<66s}║")

    msg = f"Retry     : {RETRY_MAX_ATTEMPTS}x (pause {RETRY_DELAY_SECONDS}s)"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")

    if not comp_status:
        logger.error("❌ Aucune comparaison à calculer (--skip-graphcast ET --skip-arome)")
        sys.exit(1)

    t_start = time.time()

    # Connexion DB
    logger.info("\n🔌 Connexion à la DB...")
    try:
        conn = get_db_connection()
    except Exception as e:
        logger.error(f"❌ Impossible de se connecter à la DB : {e}")
        sys.exit(1)

    results = {"success": [], "failed": []}
    total_upserted = 0

    try:
        # ═══ COMPARAISON 1 : GraphCast vs ERA5 ═══
        if not args.skip_graphcast:
            try:
                stats = run_comparison(conn, "graphcast_vs_era5", target_date)
                results["success"].append(("graphcast_vs_era5", stats))
                total_upserted += stats.get("rows_upserted", 0)
            except Exception as e:
                logger.error(f"❌ Échec graphcast_vs_era5 : {e}")
                results["failed"].append(("graphcast_vs_era5", str(e)))

        # ═══ COMPARAISON 2 : AROME vs ERA5 ═══
        if not args.skip_arome:
            try:
                stats = run_comparison(conn, "arome_vs_era5", target_date)
                results["success"].append(("arome_vs_era5", stats))
                total_upserted += stats.get("rows_upserted", 0)
            except Exception as e:
                logger.error(f"❌ Échec arome_vs_era5 : {e}")
                results["failed"].append(("arome_vs_era5", str(e)))

        # ═══ VALIDATION ═══
        if not args.no_validation and results["success"]:
            try:
                show_table_state(conn)
            except Exception as e:
                logger.warning(f"\n⚠️ Validation échouée : {e}")

    finally:
        conn.close()

    # ═══ RÉCAP ═══
    elapsed_min = (time.time() - t_start) / 60
    logger.info("\n" + "╔" + "═" * 68 + "╗")
    if not results["failed"]:
        msg = f"✅ PIPELINE MAE COMPLET OK en {elapsed_min:.1f} min"
    else:
        msg = f"⚠️  PIPELINE MAE PARTIEL en {elapsed_min:.1f} min"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")
    logger.info(f"\n📊 Résultats :")
    logger.info(f"   Succès            : {len(results['success'])}/{len(results['success']) + len(results['failed'])}")
    logger.info(f"   Échecs            : {len(results['failed'])}")
    logger.info(f"   Lignes upserted   : {total_upserted}")

    if results["failed"]:
        logger.warning(f"\n⚠️ Comparaisons en échec :")
        for comp_name, err in results["failed"]:
            logger.warning(f"   • {comp_name} : {err[:100]}")

    # ═══════════════════════════════════════════════════════════════════
    # HOOK : régénération automatique du JSON statique frontend
    # Ne s'exécute que si la DB a été modifiée (total_upserted > 0).
    # Tolérant aux pannes : ne fait pas échouer le pipeline si le backend
    # Express n'est pas lancé (warning loggé, exit code conservé).
    # ═══════════════════════════════════════════════════════════════════
    if total_upserted > 0:
        try:
            from utils.regenerate_frontend_json import regenerate_frontend_json
            logger.info("\n🔄 Hook : régénération JSON statique frontend...")
            regenerate_frontend_json()
        except Exception as hook_err:
            logger.warning(f"   ⚠️  Hook frontend ignoré : {hook_err}")

    sys.exit(0 if not results["failed"] else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Erreur fatale : {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
