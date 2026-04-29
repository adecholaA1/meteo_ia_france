"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Collecte GDAS pour inputs GraphCast Operational
FICHIER  : scripts/graphcast_gfs/fetch_gdas_nomads.py
RÔLE     : Télécharge les analyses GDAS (NOAA) via l'API NOMADS filter
           pour les 8 derniers jours + le jour précédent (T-6h).
═══════════════════════════════════════════════════════════════════════════

POURQUOI CE SCRIPT ?
--------------------
GraphCast Operational nécessite 2 états météo en entrée (current + T-6h)
pour prédire les 4 horizons suivants (+6h, +12h, +18h, +24h).

Source de données : NOAA GDAS (Global Data Assimilation System) via
l'API NOMADS filter qui permet de télécharger des subsets GRIB2 filtrés
par zone géographique + variables + niveaux.

Avantages de NOMADS vs téléchargement direct du GRIB2 global :
- Fichiers ~25 Ko au lieu de 500 Mo
- Pas de saturation RAM
- Téléchargement rapide (~1 sec par fichier)

STRUCTURE DE SORTIE
-------------------
data/gdas_raw/
├── 20260416_00/              ← run du 16 avril 00h UTC
│   ├── t_minus_6h/           ← snapshot du 15 avril 18h UTC
│   │   ├── surface.grib2
│   │   ├── level_50.grib2
│   │   ├── level_100.grib2
│   │   ├── ... (13 niveaux)
│   │   └── level_1000.grib2
│   └── t_zero/               ← snapshot du 16 avril 00h UTC
│       ├── surface.grib2
│       ├── level_50.grib2
│       └── ...
├── 20260417_00/
└── ... (8 jours au total)

USAGE
-----
    conda activate meteo_ia
    cd ~/Dev_meteo/meteo_ia_france/scripts
    python -m graphcast_gfs.fetch_gdas_nomads

TEMPS ESTIMÉ : ~10 min pour les 8 jours (224 fichiers)
═══════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests


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
# CONSTANTES
# ───────────────────────────────────────────────────────────────────────────

# URL de base de l'API NOMADS filter pour GDAS 0.25°
NOMADS_BASE_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gdas_0p25.pl"

# Zone France (GraphCast accepte -180/180)
LAT_TOP = 52
LAT_BOTTOM = 41
LON_LEFT = -6
LON_RIGHT = 10

# Les 13 niveaux de pression attendus par GraphCast Operational
PRESSURE_LEVELS = [50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 850, 925, 1000]

# Nombre de jours à collecter
NUM_DAYS = 8

# Heure du run (MVP v1.0 : 1 run/jour à 00h UTC)
RUN_HOUR_UTC = 0

# Dossier de sortie
OUTPUT_DIR = Path.home() / "Desktop" / "PROJETS" / "Dev_meteo" / "meteo_ia_france" / "data" / "gdas_raw"

# Pause entre requêtes (NOMADS demande 10s pour éviter blacklist, mais 1s suffit
# pour un petit batch personnel)
REQUEST_DELAY_SECONDS = 1.0


# ───────────────────────────────────────────────────────────────────────────
# CONSTRUCTION DES URLs NOMADS
# ───────────────────────────────────────────────────────────────────────────

def build_url_surface(target_datetime: datetime) -> str:
    """
    URL NOMADS pour les variables surface d'un snapshot GDAS.

    Variables incluses :
    - TMP @ 2m    → 2m_temperature
    - UGRD @ 10m  → 10m_u_component_of_wind
    - VGRD @ 10m  → 10m_v_component_of_wind
    - PRMSL       → mean_sea_level_pressure
    """
    date_str = target_datetime.strftime("%Y%m%d")
    hour_str = target_datetime.strftime("%H")

    params = [
        f"file=gdas.t{hour_str}z.pgrb2.0p25.f000",
        f"dir=/gdas.{date_str}/{hour_str}/atmos",
        "subregion=",
        f"leftlon={LON_LEFT}",
        f"rightlon={LON_RIGHT}",
        f"toplat={LAT_TOP}",
        f"bottomlat={LAT_BOTTOM}",
        "var_TMP=on",
        "var_UGRD=on",
        "var_VGRD=on",
        "var_PRMSL=on",
        "lev_2_m_above_ground=on",
        "lev_10_m_above_ground=on",
        "lev_mean_sea_level=on",
    ]
    return NOMADS_BASE_URL + "?" + "&".join(params)


def build_url_pressure_level(target_datetime: datetime, level_mb: int) -> str:
    """
    URL NOMADS pour UN niveau de pression (toutes les variables 3D).

    Variables incluses pour ce niveau :
    - TMP    → temperature
    - UGRD   → u_component_of_wind
    - VGRD   → v_component_of_wind
    - SPFH   → specific_humidity
    - VVEL   → vertical_velocity
    - HGT    → geopotential_height (à convertir en geopotential × 9.80665 ensuite)
    """
    date_str = target_datetime.strftime("%Y%m%d")
    hour_str = target_datetime.strftime("%H")

    params = [
        f"file=gdas.t{hour_str}z.pgrb2.0p25.f000",
        f"dir=/gdas.{date_str}/{hour_str}/atmos",
        "subregion=",
        f"leftlon={LON_LEFT}",
        f"rightlon={LON_RIGHT}",
        f"toplat={LAT_TOP}",
        f"bottomlat={LAT_BOTTOM}",
        "var_TMP=on",
        "var_UGRD=on",
        "var_VGRD=on",
        "var_SPFH=on",
        "var_VVEL=on",
        "var_HGT=on",
        f"lev_{level_mb}_mb=on",
    ]
    return NOMADS_BASE_URL + "?" + "&".join(params)


# ───────────────────────────────────────────────────────────────────────────
# TÉLÉCHARGEMENT
# ───────────────────────────────────────────────────────────────────────────

def download_file(url: str, output_path: Path, description: str = "") -> Optional[int]:
    """
    Télécharge un fichier depuis une URL et le sauvegarde.

    Returns:
        Taille du fichier en Ko, ou None en cas d'échec.
    """
    if output_path.exists() and output_path.stat().st_size > 500:
        # Skip si déjà téléchargé (idempotence)
        size_kb = output_path.stat().st_size / 1024
        return size_kb

    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"    ❌ {description} : {e}")
        return None

    if len(response.content) < 500:
        logger.error(
            f"    ❌ {description} : réponse trop petite ({len(response.content)} bytes)"
        )
        logger.error(f"       Contenu : {response.text[:300]}")
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.content)

    size_kb = len(response.content) / 1024
    return size_kb


def download_snapshot(target_datetime: datetime, snapshot_dir: Path) -> bool:
    """
    Télécharge tous les GRIB2 d'un snapshot GDAS (surface + 13 niveaux).

    Returns:
        True si tous les fichiers ont été téléchargés avec succès.
    """
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    total = 1 + len(PRESSURE_LEVELS)  # surface + 13 niveaux

    # 1. Fichier surface
    surface_path = snapshot_dir / "surface.grib2"
    size = download_file(
        build_url_surface(target_datetime),
        surface_path,
        description=f"surface {target_datetime}",
    )
    if size is not None:
        logger.info(f"    [1/{total}] surface ({size:.1f} Ko)")
        success_count += 1
    time.sleep(REQUEST_DELAY_SECONDS)

    # 2. Fichiers par niveau de pression
    for i, lvl in enumerate(PRESSURE_LEVELS, 2):
        level_path = snapshot_dir / f"level_{lvl}.grib2"
        size = download_file(
            build_url_pressure_level(target_datetime, lvl),
            level_path,
            description=f"level {lvl} mb {target_datetime}",
        )
        if size is not None:
            logger.info(f"    [{i}/{total}] level_{lvl} ({size:.1f} Ko)")
            success_count += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    return success_count == total


def download_run(run_datetime: datetime, run_dir: Path) -> bool:
    """
    Télécharge les 2 snapshots nécessaires pour un run (T-6h et T0).

    Returns:
        True si les 2 snapshots sont complets.
    """
    t_minus_6h = run_datetime - timedelta(hours=6)
    t_zero = run_datetime

    logger.info(f"\n🔄 Run {run_datetime.strftime('%Y-%m-%d %Hh UTC')}")
    logger.info(f"   ├── T-6h  = {t_minus_6h.strftime('%Y-%m-%d %Hh UTC')}")
    logger.info(f"   └── T0    = {t_zero.strftime('%Y-%m-%d %Hh UTC')}")

    # Télécharger T-6h
    logger.info(f"\n  📥 T-6h :")
    success_t_minus = download_snapshot(t_minus_6h, run_dir / "t_minus_6h")

    # Télécharger T0
    logger.info(f"\n  📥 T0 :")
    success_t_zero = download_snapshot(t_zero, run_dir / "t_zero")

    return success_t_minus and success_t_zero


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def get_dates_to_process() -> list[datetime]:
    """Calcule les 8 derniers jours (y compris aujourd'hui) à 00h UTC."""
    today_utc = datetime.now(timezone.utc).replace(
        hour=RUN_HOUR_UTC, minute=0, second=0, microsecond=0, tzinfo=None
    )
    return [today_utc - timedelta(days=i) for i in range(NUM_DAYS - 1, -1, -1)]


def main():
    """Batch principal : télécharge les 8 jours."""
    logger.info("=" * 70)
    logger.info("📥 COLLECTE GDAS — 8 derniers jours")
    logger.info("=" * 70)
    logger.info(f"   Zone France : lat {LAT_BOTTOM}-{LAT_TOP}°N, lon {LON_LEFT}-{LON_RIGHT}°E")
    logger.info(f"   Niveaux    : {PRESSURE_LEVELS}")
    logger.info(f"   Sortie     : {OUTPUT_DIR}")

    dates = get_dates_to_process()
    logger.info(f"\n📅 Dates à traiter :")
    for d in dates:
        logger.info(f"   • {d.strftime('%A %d %B %Y')} 00h UTC")

    # Orchestration
    t_start = time.time()
    results = {"success": [], "failed": []}

    for i, run_date in enumerate(dates, 1):
        logger.info(f"\n{'=' * 70}")
        logger.info(f"[{i}/{len(dates)}] {run_date.strftime('%Y-%m-%d')}")
        logger.info(f"{'=' * 70}")

        run_dir = OUTPUT_DIR / run_date.strftime("%Y%m%d_%H")

        try:
            success = download_run(run_date, run_dir)
            if success:
                results["success"].append(run_date)
                logger.info(f"\n  ✅ Run complet")
            else:
                results["failed"].append(run_date)
                logger.warning(f"\n  ⚠️ Run incomplet (certains fichiers manquants)")
        except Exception as e:
            results["failed"].append(run_date)
            logger.error(f"\n  ❌ Erreur : {e}")

    # Récap final
    elapsed_min = (time.time() - t_start) / 60
    logger.info(f"\n{'=' * 70}")
    logger.info(f"✅ COLLECTE TERMINÉE en {elapsed_min:.1f} min")
    logger.info(f"{'=' * 70}")
    logger.info(f"   Succès : {len(results['success'])}/{len(dates)}")
    logger.info(f"   Échecs : {len(results['failed'])}/{len(dates)}")

    if results["failed"]:
        logger.warning(f"\n⚠️ Dates en échec :")
        for d in results["failed"]:
            logger.warning(f"   • {d.strftime('%Y-%m-%d')}")

    # Taille totale
    total_size_mb = sum(
        f.stat().st_size for f in OUTPUT_DIR.rglob("*.grib2")
    ) / (1024 * 1024)
    logger.info(f"\n📊 Taille totale : {total_size_mb:.1f} Mo")
    logger.info(f"📁 Données dans : {OUTPUT_DIR}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompu par l'utilisateur")
        sys.exit(1)
