"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Téléchargement AROME (production)
FICHIER  : scripts/arome/fetch_arome.py
RÔLE     : Télécharge les 4 fichiers GRIB2 SP1 par run AROME depuis
           data.gouv.fr (gratuit, sans clé API).
           Mode 1-jour OU mode plage de dates (batch).
═══════════════════════════════════════════════════════════════════════════

POURQUOI 4 FICHIERS ?
---------------------
Chaque fichier GRIB2 SP1 contient les variables sur un range de 6 horizons :
  - 00H06H : T+1 à T+6   (jusqu'à 00h UTC J+1 si run 18z)
  - 07H12H : T+7 à T+12  (jusqu'à 06h UTC J+1)
  - 13H18H : T+13 à T+18 (jusqu'à 12h UTC J+1)
  - 19H24H : T+19 à T+24 (jusqu'à 18h UTC J+1)

Pour calculer le cumul tp_6h aux 4 timestamps cibles (00h, 06h, 12h, 18h),
on a besoin de SOUSTRAIRE des cumuls successifs :
  tp_6h(T+12h) = tp_cumul(T+12h) - tp_cumul(T+6h)  → 2 fichiers !
  tp_6h(T+18h) = tp_cumul(T+18h) - tp_cumul(T+12h) → 2 fichiers !
  tp_6h(T+24h) = tp_cumul(T+24h) - tp_cumul(T+18h) → 2 fichiers !

→ Donc les 4 fichiers sont OBLIGATOIRES.

FICHIERS PRODUITS (par run)
---------------------------
data/arome_raw/
├── arome__0025__SP1__00H06H__YYYY-MM-DDT18:00:00Z.grib2  (~50 Mo)
├── arome__0025__SP1__07H12H__YYYY-MM-DDT18:00:00Z.grib2
├── arome__0025__SP1__13H18H__YYYY-MM-DDT18:00:00Z.grib2
└── arome__0025__SP1__19H24H__YYYY-MM-DDT18:00:00Z.grib2

Total : ~200 Mo par run, ~5-10 sec de téléchargement (data.gouv.fr est rapide)

USAGE
-----
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts

    # Mode 1 jour spécifique (pour run_daily_pipeline)
    python -m arome.fetch_arome --date 2026-04-23 --run 18

    # Mode plage de dates (batch historique)
    python -m arome.fetch_arome --start-date 2026-04-16 --end-date 2026-04-23 --run 18

    # Skip si déjà téléchargés (utile pour reprises)
    python -m arome.fetch_arome --start-date 2026-04-16 --end-date 2026-04-23 \
                                 --run 18 --skip-existing

LIMITATION
----------
data.gouv.fr garde les fichiers AROME pendant ~15 jours seulement.
Au-delà, les téléchargements retourneront 404.
═══════════════════════════════════════════════════════════════════════════
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable

import requests


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ───────────────────────────────────────────────────────────────────────────

BASE_DIR = Path.home() / "Desktop" / "PROJETS" / "Dev_meteo" / "meteo_ia_france"
OUTPUT_DIR = BASE_DIR / "data" / "arome_raw"

# URL pattern data.gouv.fr (officiel Météo-France, gratuit, sans token)
URL_PATTERN = (
    "https://object.data.gouv.fr/meteofrance-pnt/pnt/"
    "{run_iso}/arome/0025/{package}/"
    "arome__0025__{package}__{time_range}__{run_iso}.grib2"
)

# Les 4 ranges pour couvrir T+1 à T+24 (= J+1 si run 18z)
TIME_RANGES = ["00H06H", "07H12H", "13H18H", "19H24H"]

# Package qui contient nos 5 variables (validé par fetch_arome_test.py)
PACKAGE = "SP1"

# Taille minimum d'un fichier GRIB2 valide (~30 Mo)
MIN_FILE_SIZE_MB = 30

# Configuration retry
RETRY_MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 30  # plus court qu'ERA5 car HTTP rapide


# ───────────────────────────────────────────────────────────────────────────
# CONSTRUCTION DES URL ET CHEMINS
# ───────────────────────────────────────────────────────────────────────────

def build_url(run_dt: datetime, time_range: str, package: str = PACKAGE) -> str:
    """Construit l'URL complète pour un fichier GRIB2 AROME."""
    run_iso = run_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return URL_PATTERN.format(
        run_iso=run_iso,
        package=package,
        time_range=time_range,
    )


def get_output_path(run_dt: datetime, time_range: str, package: str = PACKAGE) -> Path:
    """Retourne le chemin de sortie pour un fichier."""
    run_iso = run_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    filename = f"arome__0025__{package}__{time_range}__{run_iso}.grib2"
    return OUTPUT_DIR / filename


# ───────────────────────────────────────────────────────────────────────────
# RETRY UTILITAIRE
# ───────────────────────────────────────────────────────────────────────────

def retry(fn: Callable, name: str, attempts: int = RETRY_MAX_ATTEMPTS, delay: int = RETRY_DELAY_SECONDS):
    """Exécute une fonction avec retry automatique."""
    last_exception = None
    for attempt in range(1, attempts + 1):
        try:
            if attempt > 1:
                logger.info(f"      🔄 Tentative {attempt}/{attempts}...")
            return fn()
        except Exception as e:
            last_exception = e
            logger.warning(f"      ⚠️  Tentative {attempt}/{attempts} échouée : {e}")
            if attempt < attempts:
                time.sleep(delay)

    logger.error(f"      ❌ ÉCHEC DÉFINITIF après {attempts} tentatives")
    raise last_exception


# ───────────────────────────────────────────────────────────────────────────
# TÉLÉCHARGEMENT D'UN FICHIER
# ───────────────────────────────────────────────────────────────────────────

def download_one_file(url: str, output_path: Path, log_progress: bool = False) -> Path:
    """
    Télécharge un fichier GRIB2.
    Retourne le chemin si succès, lève une exception sinon.
    """
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0
    chunk_size = 1024 * 1024  # 1 Mo
    last_log = 0

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if log_progress and (downloaded - last_log > 10 * 1024 * 1024):
                    if total_size > 0:
                        pct = 100 * downloaded / total_size
                        logger.info(f"      ⏳ {downloaded / (1024 * 1024):.1f} / {total_size / (1024 * 1024):.1f} Mo ({pct:.0f}%)")
                    last_log = downloaded

    # Validation taille
    size_mb = output_path.stat().st_size / (1024 * 1024)
    if size_mb < MIN_FILE_SIZE_MB:
        output_path.unlink()
        raise RuntimeError(f"Fichier trop petit ({size_mb:.1f} Mo < {MIN_FILE_SIZE_MB} Mo) — probablement corrompu")

    return output_path


# ───────────────────────────────────────────────────────────────────────────
# TÉLÉCHARGEMENT D'UN RUN (4 FICHIERS)
# ───────────────────────────────────────────────────────────────────────────

def fetch_one_run(run_dt: datetime, skip_existing: bool = False) -> dict:
    """
    Télécharge les 4 fichiers SP1 d'un run AROME.

    Args:
        run_dt: datetime du run (ex: 2026-04-23 18h UTC)
        skip_existing: si True, skip les fichiers déjà présents

    Returns:
        dict {"success": [paths], "failed": [time_ranges], "skipped": [paths]}
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"\n📅 Run {run_dt.strftime('%Y-%m-%d %Hz UTC')}")

    results = {"success": [], "failed": [], "skipped": []}
    t_start = time.time()

    for time_range in TIME_RANGES:
        url = build_url(run_dt, time_range)
        output_path = get_output_path(run_dt, time_range)

        # Skip si déjà présent (et taille valide)
        if skip_existing and output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            if size_mb >= MIN_FILE_SIZE_MB:
                logger.info(f"   ✅ {time_range} : déjà présent ({size_mb:.1f} Mo), skip")
                results["skipped"].append(output_path)
                continue
            else:
                logger.warning(f"   ⚠️  {time_range} : fichier existant mais trop petit ({size_mb:.1f} Mo), retéléchargement")
                output_path.unlink()

        # Téléchargement avec retry
        logger.info(f"   📥 {time_range} : téléchargement...")
        try:
            def _download():
                return download_one_file(url, output_path, log_progress=False)

            retry(_download, f"download {time_range}")
            size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"      ✅ Téléchargé ({size_mb:.1f} Mo)")
            results["success"].append(output_path)

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            logger.error(f"   ❌ {time_range} : HTTP {status}")
            if status == 404:
                logger.error(f"      → Fichier non trouvé sur data.gouv.fr (run trop ancien ?)")
            results["failed"].append(time_range)
        except Exception as e:
            logger.error(f"   ❌ {time_range} : {e}")
            results["failed"].append(time_range)

    elapsed = time.time() - t_start
    n_ok = len(results["success"]) + len(results["skipped"])
    logger.info(f"   📊 Bilan : {n_ok}/4 fichiers OK ({elapsed:.1f}s)")

    return results


# ───────────────────────────────────────────────────────────────────────────
# TÉLÉCHARGEMENT D'UNE PLAGE DE DATES
# ───────────────────────────────────────────────────────────────────────────

def fetch_date_range(
    start_date: datetime,
    end_date: datetime,
    run_hour: int,
    skip_existing: bool = False,
) -> dict:
    """
    Télécharge les runs sur une plage de dates [start, end] (inclus).

    Returns:
        dict avec stats globales : {"runs_ok": N, "runs_partial": N, "runs_failed": N, "files_total": N}
    """
    n_days = (end_date - start_date).days + 1
    logger.info(f"\n🗓️  Plage : {start_date.date()} → {end_date.date()} ({n_days} jours)")
    logger.info(f"   Run horaire : {run_hour:02d}z UTC")
    logger.info(f"   Total fichiers attendus : {n_days * 4}")

    stats = {
        "runs_ok": 0,
        "runs_partial": 0,
        "runs_failed": 0,
        "files_success": 0,
        "files_skipped": 0,
        "files_failed": 0,
    }

    current = start_date
    while current <= end_date:
        run_dt = current.replace(hour=run_hour, tzinfo=timezone.utc)
        results = fetch_one_run(run_dt, skip_existing=skip_existing)

        n_ok = len(results["success"]) + len(results["skipped"])
        n_failed = len(results["failed"])

        stats["files_success"] += len(results["success"])
        stats["files_skipped"] += len(results["skipped"])
        stats["files_failed"] += n_failed

        if n_ok == 4:
            stats["runs_ok"] += 1
        elif n_ok > 0:
            stats["runs_partial"] += 1
        else:
            stats["runs_failed"] += 1

        current += timedelta(days=1)

    return stats


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Téléchargement AROME (production)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--date", type=str, default=None,
                        help="Date d'un run unique (YYYY-MM-DD)")
    parser.add_argument("--start-date", type=str, default=None,
                        help="Date de début du batch (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None,
                        help="Date de fin du batch (YYYY-MM-DD)")
    parser.add_argument("--run", type=int, default=18, choices=[0, 3, 6, 9, 12, 15, 18, 21],
                        help="Heure UTC du run (défaut: 18)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip les fichiers déjà téléchargés")
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Validation des arguments
    if args.date and (args.start_date or args.end_date):
        logger.error("❌ Utilise SOIT --date SOIT --start-date/--end-date, pas les deux")
        sys.exit(1)

    if args.start_date and not args.end_date:
        logger.error("❌ --start-date nécessite --end-date")
        sys.exit(1)

    if args.end_date and not args.start_date:
        logger.error("❌ --end-date nécessite --start-date")
        sys.exit(1)

    if not args.date and not args.start_date:
        logger.error("❌ Spécifie --date OU --start-date/--end-date")
        sys.exit(1)

    # Banner
    logger.info("╔" + "═" * 68 + "╗")
    msg = "🇫🇷 TÉLÉCHARGEMENT AROME (PRODUCTION)"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")

    t_global_start = time.time()

    try:
        # ═══ MODE 1 JOUR ═══
        if args.date:
            try:
                run_date = datetime.strptime(args.date, "%Y-%m-%d")
            except ValueError:
                logger.error(f"❌ Format date invalide : {args.date} (attendu YYYY-MM-DD)")
                sys.exit(1)

            run_dt = run_date.replace(hour=args.run, tzinfo=timezone.utc)
            results = fetch_one_run(run_dt, skip_existing=args.skip_existing)

            elapsed = time.time() - t_global_start
            logger.info("\n" + "╔" + "═" * 68 + "╗")
            n_ok = len(results["success"]) + len(results["skipped"])
            if n_ok == 4:
                msg = f"✅ TÉLÉCHARGEMENT COMPLET en {elapsed:.1f}s (4/4 fichiers)"
            else:
                msg = f"⚠️  TÉLÉCHARGEMENT PARTIEL : {n_ok}/4 fichiers"
            logger.info(f"║  {msg:<66s}║")
            logger.info("╚" + "═" * 68 + "╝")

            sys.exit(0 if n_ok == 4 else 1)

        # ═══ MODE PLAGE DE DATES ═══
        else:
            try:
                start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
                end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
            except ValueError as e:
                logger.error(f"❌ Format date invalide : {e}")
                sys.exit(1)

            if start_date > end_date:
                logger.error(f"❌ start-date ({args.start_date}) doit être <= end-date ({args.end_date})")
                sys.exit(1)

            stats = fetch_date_range(
                start_date, end_date, args.run,
                skip_existing=args.skip_existing,
            )

            # Récap
            elapsed_min = (time.time() - t_global_start) / 60
            logger.info("\n" + "╔" + "═" * 68 + "╗")
            msg = f"✅ BATCH AROME TERMINÉ en {elapsed_min:.1f} min"
            logger.info(f"║  {msg:<66s}║")
            logger.info("╚" + "═" * 68 + "╝")
            logger.info(f"\n📊 Statistiques :")
            logger.info(f"   Runs complets (4/4)    : {stats['runs_ok']}")
            logger.info(f"   Runs partiels          : {stats['runs_partial']}")
            logger.info(f"   Runs échoués (0/4)     : {stats['runs_failed']}")
            logger.info(f"\n   Fichiers téléchargés   : {stats['files_success']}")
            logger.info(f"   Fichiers déjà présents : {stats['files_skipped']}")
            logger.info(f"   Fichiers échoués       : {stats['files_failed']}")

            sys.exit(0 if stats["runs_failed"] == 0 else 1)

    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Erreur : {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
