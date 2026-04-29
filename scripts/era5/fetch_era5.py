"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Téléchargement ERA5 via cdsapi
FICHIER  : scripts/era5/fetch_era5.py
RÔLE     : Télécharge ERA5 reanalysis depuis Copernicus CDS pour 1 jour cible.
           Pour le cumul tp_6h_mm à 00h, télécharge aussi le jour précédent
           (avec uniquement total_precipitation).
═══════════════════════════════════════════════════════════════════════════

NOTE TECHNIQUE — FORMAT ZIP CDS
-------------------------------
L'API CDS renvoie systématiquement un ZIP quand on demande plusieurs variables
(comportement officiellement reconnu par ECMWF mais non-corrigé). Le paramètre
'download_format: unarchived' n'est plus respecté.

Solution : dézippage systématique dans extract_and_merge_zip().

STRATÉGIE DE TÉLÉCHARGEMENT
---------------------------
Pour collecter le jour cible D, on fait UNE SEULE requête CDS pour J-1 + J,
puis on extrait et stocke différemment :

  • J (jour cible)         → toutes les 5 variables × 24h horaires
                              → era5_YYYYMMDD_full.nc
  • J-1 (jour précédent)   → uniquement total_precipitation × 24h horaires
                              (utile pour cumul tp_6h à 00h du J)
                              → era5_YYYYMMDD_tp_only.nc

VARIABLES TÉLÉCHARGÉES (5 surface)
----------------------------------
  - 2m_temperature
  - 10m_u_component_of_wind
  - 10m_v_component_of_wind
  - mean_sea_level_pressure
  - total_precipitation

Variables dérivées (calculées plus tard dans export_era5_csv.py) :
  - wind_speed_10m_ms (depuis u10, v10)
  - wind_direction_10m_deg (depuis u10, v10)
  - toa_wm2 (formule astronomique via solar_utils.py)

ZONE GÉOGRAPHIQUE (mêmes bornes que GraphCast)
-----------------------------------------------
  - Latitude  : 41° à 52° N
  - Longitude : -6° à +10° E
  - Résolution : 0.25° × 0.25° = 45 × 65 = 2925 points

USAGE
-----
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts

    # Télécharger pour 1 jour spécifique
    python -m era5.fetch_era5 --date 2026-04-19

TEMPS ESTIMÉ
------------
- Attente file CDS : 1-10 min selon charge
- Téléchargement   : 30-60 sec
- Total            : 2-15 min selon charge
═══════════════════════════════════════════════════════════════════════════
"""

# Suppression des warnings xarray bénins lors de la fusion
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="xarray")
warnings.filterwarnings("ignore", message=".*conflicting attribute.*")
warnings.filterwarnings("ignore", message=".*combine.*")
warnings.filterwarnings("ignore", message=".*overriding.*")

import argparse
import logging
import shutil
import sys
import time
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import cdsapi
import xarray as xr


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
OUTPUT_DIR = BASE_DIR / "data" / "era5_raw"

# Zone géographique France (mêmes bornes que GraphCast)
# Format CDS area : [North, West, South, East]
AREA_NORTH = 52.0
AREA_WEST = -6.0
AREA_SOUTH = 41.0
AREA_EAST = 10.0
GRID_RESOLUTION = 0.25

# Variables à télécharger (5 variables surface)
ALL_VARIABLES = [
    "2m_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "mean_sea_level_pressure",
    "total_precipitation",
]

# 24h horaires
ALL_HOURS = [f"{h:02d}:00" for h in range(24)]


# ───────────────────────────────────────────────────────────────────────────
# REQUÊTE CDS POUR 2 JOURS (J-1 + J)
# ───────────────────────────────────────────────────────────────────────────

def download_two_days(target_date: datetime, output_zip_path: Path) -> Path:
    """
    Télécharge ERA5 pour 2 jours consécutifs (J-1 et J) en UNE seule
    requête CDS, avec les 5 variables surface.

    L'API CDS renvoie un ZIP contenant 1 ou 2 fichiers .nc selon les
    variables demandées (instantanées vs accumulées séparées).
    """
    prev_date = target_date - timedelta(days=1)

    logger.info(f"\n📥 Requête CDS : {prev_date.strftime('%Y-%m-%d')} + {target_date.strftime('%Y-%m-%d')}")
    logger.info(f"   Variables : {len(ALL_VARIABLES)}")
    logger.info(f"   Heures    : {len(ALL_HOURS)} × 2 jours = 48h")
    logger.info(f"   Zone      : lat [{AREA_SOUTH}, {AREA_NORTH}] × lon [{AREA_WEST}, {AREA_EAST}]")

    output_zip_path.parent.mkdir(parents=True, exist_ok=True)

    # Construire le request CDS
    years = sorted(set([prev_date.strftime("%Y"), target_date.strftime("%Y")]))
    months = sorted(set([prev_date.strftime("%m"), target_date.strftime("%m")]))
    days = sorted(set([prev_date.strftime("%d"), target_date.strftime("%d")]))

    request_params = {
        "product_type": ["reanalysis"],
        "variable": ALL_VARIABLES,
        "year": years,
        "month": months,
        "day": days,
        "time": ALL_HOURS,
        "area": [AREA_NORTH, AREA_WEST, AREA_SOUTH, AREA_EAST],
        "grid": [GRID_RESOLUTION, GRID_RESOLUTION],
        "data_format": "netcdf",
    }

    logger.info(f"\n   ⏳ Soumission de la requête CDS...")
    logger.info(f"      (Attente 1-10 min selon charge serveur)")

    t0 = time.time()
    client = cdsapi.Client(quiet=True)  # quiet=True pour réduire les logs CDS verbeux
    client.retrieve(
        "reanalysis-era5-single-levels",
        request_params,
        str(output_zip_path),
    )
    elapsed = time.time() - t0

    size_mb = output_zip_path.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ Téléchargé en {elapsed:.1f}s ({size_mb:.1f} Mo)")

    return output_zip_path


# ───────────────────────────────────────────────────────────────────────────
# EXTRACTION DU ZIP + FUSION DES NETCDF
# ───────────────────────────────────────────────────────────────────────────

def extract_and_merge_zip(zip_path: Path) -> xr.Dataset:
    """
    Extrait le ZIP CDS et fusionne les fichiers .nc en un seul Dataset.

    CDS sépare souvent les variables en 2 fichiers :
      - data_stream-oper_stepType-instant.nc  (variables instantanées)
      - data_stream-oper_stepType-accum.nc    (variables accumulées comme tp)

    Cette fonction les fusionne automatiquement.
    """
    logger.info(f"\n📦 Extraction du ZIP CDS")

    # Créer un dossier temporaire pour l'extraction
    extract_dir = zip_path.parent / f"_extract_{zip_path.stem}"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir()

    # Extraire le ZIP
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.namelist()
        logger.info(f"   📋 Contenu : {members}")
        zf.extractall(extract_dir)

    # Trouver tous les .nc extraits
    nc_files = sorted(extract_dir.glob("*.nc"))
    if not nc_files:
        raise RuntimeError(f"Aucun fichier .nc trouvé dans le ZIP : {members}")

    logger.info(f"   ✅ {len(nc_files)} fichier(s) .nc extrait(s)")

    # Charger et fusionner
    if len(nc_files) == 1:
        ds = xr.open_dataset(nc_files[0])
    else:
        # Plusieurs fichiers : on les fusionne
        # compat="override" : si conflit d'attributs, on prend le premier
        datasets = [xr.open_dataset(f) for f in nc_files]
        ds = xr.merge(datasets, compat="override")
        for d in datasets:
            d.close()

    # Retourner le dataset chargé en mémoire (les fichiers temporaires
    # seront nettoyés après par le caller)
    ds.load()  # force le chargement complet en mémoire
    return ds


def cleanup_zip_extraction(zip_path: Path):
    """Supprime le ZIP source et le dossier d'extraction temporaire."""
    if zip_path.exists():
        zip_path.unlink()

    extract_dir = zip_path.parent / f"_extract_{zip_path.stem}"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)


# ───────────────────────────────────────────────────────────────────────────
# SPLIT DU DATASET EN 2 .nc DISTINCTS
# ───────────────────────────────────────────────────────────────────────────

def split_to_two_files(ds: xr.Dataset, target_date: datetime) -> tuple:
    """
    Découpe le Dataset (J-1 + J) en 2 fichiers distincts :
      - era5_YYYYMMDD_full.nc        : jour J avec TOUTES les variables
      - era5_YYYYMMDD_tp_only.nc     : jour J-1 avec UNIQUEMENT total_precipitation
    """
    prev_date = target_date - timedelta(days=1)
    target_str = target_date.strftime("%Y%m%d")
    prev_str = prev_date.strftime("%Y%m%d")

    output_full = OUTPUT_DIR / f"era5_{target_str}_full.nc"
    output_tp_prev = OUTPUT_DIR / f"era5_{prev_str}_tp_only.nc"

    logger.info(f"\n🔧 Split du dataset en 2 fichiers")
    logger.info(f"   📊 Dataset : dims={dict(ds.sizes)}, vars={list(ds.data_vars)}")

    # Détecter le nom de la dimension temporelle (varie : 'time' ou 'valid_time')
    time_dim = None
    for candidate in ["valid_time", "time"]:
        if candidate in ds.coords:
            time_dim = candidate
            break

    if time_dim is None:
        raise ValueError(f"Aucune dimension temporelle trouvée. Coords : {list(ds.coords)}")

    logger.info(f"   ⏰ Dim temps : '{time_dim}'")

    # Sélectionner par date
    target_str_iso = target_date.strftime("%Y-%m-%d")
    prev_str_iso = prev_date.strftime("%Y-%m-%d")

    ds_J = ds.sel({time_dim: target_str_iso})
    ds_prev_J = ds.sel({time_dim: prev_str_iso})

    logger.info(f"   📅 J ({target_str_iso}) : {ds_J.sizes[time_dim]} timestamps")
    logger.info(f"   📅 J-1 ({prev_str_iso}) : {ds_prev_J.sizes[time_dim]} timestamps")

    # ═══ Sauvegarder le J avec TOUTES les variables ═══
    logger.info(f"\n   💾 Écriture {output_full.name}")
    ds_J.to_netcdf(output_full)
    size_J_mb = output_full.stat().st_size / (1024 * 1024)
    logger.info(f"      ✅ {size_J_mb:.1f} Mo (toutes vars × 24h)")

    # ═══ Sauvegarder le J-1 avec UNIQUEMENT total_precipitation ═══
    # Le nom de la variable peut être 'tp' ou 'total_precipitation'
    tp_var_name = None
    for candidate in ["tp", "total_precipitation"]:
        if candidate in ds_prev_J.data_vars:
            tp_var_name = candidate
            break

    if tp_var_name is None:
        raise ValueError(f"Variable total_precipitation introuvable. Vars : {list(ds_prev_J.data_vars)}")

    ds_prev_tp = ds_prev_J[[tp_var_name]]
    logger.info(f"\n   💾 Écriture {output_tp_prev.name}")
    ds_prev_tp.to_netcdf(output_tp_prev)
    size_prev_mb = output_tp_prev.stat().st_size / (1024 * 1024)
    logger.info(f"      ✅ {size_prev_mb:.1f} Mo ({tp_var_name} × 24h)")

    return output_full, output_tp_prev


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def fetch_era5_for_date(target_date: datetime) -> tuple:
    """
    Télécharge ERA5 pour 1 jour cible (et le jour précédent pour le cumul tp).

    Returns:
        (path_full_J, path_tp_only_J_minus_1) : chemins des 2 fichiers .nc créés
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    target_str = target_date.strftime("%Y%m%d")
    prev_str = (target_date - timedelta(days=1)).strftime("%Y%m%d")

    output_full = OUTPUT_DIR / f"era5_{target_str}_full.nc"
    output_tp_prev = OUTPUT_DIR / f"era5_{prev_str}_tp_only.nc"

    # Idempotence : si les 2 fichiers existent déjà, skip
    if output_full.exists() and output_tp_prev.exists():
        logger.info(f"✅ Fichiers déjà présents :")
        logger.info(f"   • {output_full.name}")
        logger.info(f"   • {output_tp_prev.name}")
        return output_full, output_tp_prev

    # Téléchargement (= ZIP de CDS)
    zip_path = OUTPUT_DIR / f"era5_temp_{target_str}.zip"
    download_two_days(target_date, zip_path)

    # Extraction + fusion en mémoire
    ds = extract_and_merge_zip(zip_path)

    # Split en 2 fichiers .nc
    try:
        result = split_to_two_files(ds, target_date)
    finally:
        ds.close()
        cleanup_zip_extraction(zip_path)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Téléchargement ERA5 pour 1 jour (avec J-1 pour cumul tp)",
    )
    parser.add_argument(
        "--date", type=str, required=True,
        help="Date cible au format YYYY-MM-DD (ex: 2026-04-19)",
    )
    args = parser.parse_args()

    try:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        logger.error(f"❌ Format de date invalide : {args.date} (attendu YYYY-MM-DD)")
        sys.exit(1)

    # Banner
    logger.info("╔" + "═" * 68 + "╗")
    msg = f"📥 TÉLÉCHARGEMENT ERA5 — {target_date.strftime('%Y-%m-%d')}"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")

    t_start = time.time()

    try:
        path_full, path_tp_prev = fetch_era5_for_date(target_date)

        elapsed_min = (time.time() - t_start) / 60
        logger.info("\n" + "╔" + "═" * 68 + "╗")
        msg = f"✅ TÉLÉCHARGEMENT ERA5 OK en {elapsed_min:.1f} min"
        logger.info(f"║  {msg:<66s}║")
        logger.info("╚" + "═" * 68 + "╝")
        logger.info(f"\n📁 Fichiers produits :")
        logger.info(f"   • {path_full}")
        logger.info(f"   • {path_tp_prev}")
        sys.exit(0)

    except Exception as e:
        elapsed_min = (time.time() - t_start) / 60
        logger.error(f"\n❌ ÉCHEC après {elapsed_min:.1f} min : {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
