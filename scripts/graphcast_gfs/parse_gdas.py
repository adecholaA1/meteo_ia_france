"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Conversion GDAS → NetCDF format GraphCast
FICHIER  : scripts/graphcast_gfs/parse_gdas.py
RÔLE     : Lit les GRIB2 téléchargés par fetch_gdas_nomads.py et produit
           un NetCDF par run au format attendu par GraphCast Operational.
═══════════════════════════════════════════════════════════════════════════

ENTRÉE
------
data/gdas_raw/20260416_00/
├── t_minus_6h/
│   ├── surface.grib2        (4 variables 2D : t2m, u10, v10, prmsl)
│   ├── level_50.grib2       (6 variables 3D pour 50 mb)
│   ├── level_100.grib2
│   └── ... (13 niveaux)
└── t_zero/
    ├── surface.grib2
    ├── level_50.grib2
    └── ...

SORTIE
------
data/gdas_ready/gdas_20260416_00.nc
   NetCDF avec structure GraphCast :
   - Dimensions : (batch=1, time=2, level=13, lat=45, lon=65)
   - Variables surface (4) : (batch, time, lat, lon)
   - Variables 3D (6) : (batch, time, level, lat, lon)
   - Coord time = [T-6h, T0] en numpy datetime64

MAPPING VARIABLES GDAS → GraphCast
-----------------------------------
    t2m   → 2m_temperature
    u10   → 10m_u_component_of_wind
    v10   → 10m_v_component_of_wind
    prmsl → mean_sea_level_pressure
    t     → temperature
    u     → u_component_of_wind
    v     → v_component_of_wind
    q     → specific_humidity
    w     → vertical_velocity
    gh    → geopotential (après × 9.80665 pour passer de m à m²/s²)

USAGE
-----
    conda activate meteo_ia
    cd ~/Dev_meteo/meteo_ia_france/scripts
    python -m graphcast_gfs.parse_gdas
═══════════════════════════════════════════════════════════════════════════
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import xarray as xr


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

INPUT_DIR = Path.home() / "Desktop" / "PROJETS" / "Dev_meteo" / "meteo_ia_france" / "data" / "gdas_raw"
OUTPUT_DIR = Path.home() / "Desktop" / "PROJETS" / "Dev_meteo" / "meteo_ia_france" / "data" / "gdas_ready"

# Les 13 niveaux de pression GraphCast Operational
PRESSURE_LEVELS = [50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 850, 925, 1000]

# Mapping GDAS (cfgrib) → GraphCast
# Format : (nom_cfgrib, nom_graphcast, facteur_conversion)
SURFACE_MAPPING = {
    "t2m":   "2m_temperature",
    "u10":   "10m_u_component_of_wind",
    "v10":   "10m_v_component_of_wind",
    "prmsl": "mean_sea_level_pressure",
}

PRESSURE_MAPPING = {
    # (nom_graphcast, conversion)
    "t":  ("temperature",         None),      # K → K
    "u":  ("u_component_of_wind", None),      # m/s → m/s
    "v":  ("v_component_of_wind", None),      # m/s → m/s
    "q":  ("specific_humidity",   None),      # kg/kg → kg/kg
    "w":  ("vertical_velocity",   None),      # Pa/s → Pa/s
    "gh": ("geopotential",        9.80665),   # m → m²/s² (×g)
}

# Constante gravité (pour convertir geopotential height en geopotential)
GRAVITY = 9.80665


# ───────────────────────────────────────────────────────────────────────────
# LECTURE DES FICHIERS GRIB2
# ───────────────────────────────────────────────────────────────────────────

def read_surface_file(grib_path: Path) -> xr.Dataset:
    """
    Lit surface.grib2 et retourne un xr.Dataset avec les 4 variables 2D.

    surface.grib2 contient plusieurs types de level, on les lit séparément
    puis on les fusionne.
    """
    datasets = []

    # Variables @ 2m (t2m)
    try:
        ds = xr.open_dataset(
            grib_path,
            engine="cfgrib",
            filter_by_keys={"typeOfLevel": "heightAboveGround", "level": 2},
        )
        datasets.append(ds)
    except Exception as e:
        logger.warning(f"    ⚠️ Lecture 2m : {e}")

    # Variables @ 10m (u10, v10)
    try:
        ds = xr.open_dataset(
            grib_path,
            engine="cfgrib",
            filter_by_keys={"typeOfLevel": "heightAboveGround", "level": 10},
        )
        datasets.append(ds)
    except Exception as e:
        logger.warning(f"    ⚠️ Lecture 10m : {e}")

    # PRMSL (meanSea)
    try:
        ds = xr.open_dataset(
            grib_path,
            engine="cfgrib",
            filter_by_keys={"typeOfLevel": "meanSea"},
        )
        datasets.append(ds)
    except Exception as e:
        logger.warning(f"    ⚠️ Lecture meanSea : {e}")

    if not datasets:
        raise ValueError(f"Aucune variable surface trouvée dans {grib_path}")

    # Fusionner (xr.merge gère les dimensions différentes)
    merged = xr.merge(datasets, compat="override")

    # Supprimer les coords inutiles pour GraphCast
    for coord in ["heightAboveGround", "meanSea", "step", "time", "valid_time"]:
        if coord in merged.coords:
            merged = merged.drop_vars(coord, errors="ignore")

    return merged


def read_pressure_level_file(grib_path: Path, level_mb: int) -> xr.Dataset:
    """
    Lit un fichier level_XXX.grib2 et retourne un xr.Dataset avec les 6 variables 3D.

    Toutes les variables sont au même niveau (typeOfLevel=isobaricInhPa, level=XXX).
    """
    ds = xr.open_dataset(
        grib_path,
        engine="cfgrib",
        filter_by_keys={"typeOfLevel": "isobaricInhPa"},
    )

    # Supprimer les coords inutiles
    for coord in ["step", "time", "valid_time", "isobaricInhPa"]:
        if coord in ds.coords:
            ds = ds.drop_vars(coord, errors="ignore")

    return ds


def load_snapshot(snapshot_dir: Path) -> xr.Dataset:
    """
    Charge un snapshot complet (1 fichier surface + 13 fichiers pressure levels).

    Retourne un xr.Dataset avec :
    - Variables surface (2D) : dims = (lat, lon)
    - Variables 3D : dims = (level, lat, lon)
    """
    logger.info(f"    📖 Lecture snapshot {snapshot_dir.name}")

    # ═══ 1. Surface ═══
    surface_path = snapshot_dir / "surface.grib2"
    if not surface_path.exists():
        raise FileNotFoundError(f"Manquant : {surface_path}")

    ds_surface = read_surface_file(surface_path)
    logger.info(f"       ✅ surface : {list(ds_surface.data_vars)}")

    # ═══ 2. Pressure levels ═══
    pressure_arrays = {gc_name: [] for _, (gc_name, _) in PRESSURE_MAPPING.items()}
    levels_found = []
    lat_coords = None
    lon_coords = None

    for lvl in PRESSURE_LEVELS:
        level_path = snapshot_dir / f"level_{lvl}.grib2"
        if not level_path.exists():
            logger.warning(f"       ⚠️ level_{lvl}.grib2 manquant")
            continue

        try:
            ds_lvl = read_pressure_level_file(level_path, lvl)
        except Exception as e:
            logger.warning(f"       ⚠️ Erreur lecture level_{lvl} : {e}")
            continue

        levels_found.append(lvl)

        # Extraire chaque variable et sauvegarder les coords lat/lon
        for cfgrib_name, (gc_name, conversion) in PRESSURE_MAPPING.items():
            if cfgrib_name not in ds_lvl.data_vars:
                continue
            values = ds_lvl[cfgrib_name].values.astype(np.float32)
            if conversion is not None:
                values = values * conversion
            pressure_arrays[gc_name].append(values)

            if lat_coords is None:
                lat_coords = ds_lvl.latitude.values.astype(np.float64)
                lon_coords = ds_lvl.longitude.values.astype(np.float64)

    logger.info(f"       ✅ pressure : {len(levels_found)} niveaux ({levels_found})")

    # ═══ 3. Construction du Dataset final ═══

    # Rename surface variables en noms GraphCast
    surface_renamed = {}
    for cfgrib_name, gc_name in SURFACE_MAPPING.items():
        if cfgrib_name in ds_surface.data_vars:
            surface_renamed[gc_name] = ds_surface[cfgrib_name].astype(np.float32)

    # Coords communes
    if lat_coords is None:
        lat_coords = ds_surface.latitude.values.astype(np.float64)
        lon_coords = ds_surface.longitude.values.astype(np.float64)

    # Note : cfgrib retourne latitude en ordre décroissant (52 → 41).
    # GraphCast attend ordre croissant → on re-trie à la fin.

    # Construction du Dataset
    ds = xr.Dataset(
        coords={
            "lat": lat_coords,
            "lon": lon_coords,
            "level": np.array(levels_found, dtype=np.int32),
        }
    )

    # Variables surface (2D)
    for gc_name, data_array in surface_renamed.items():
        ds[gc_name] = (("lat", "lon"), data_array.values)

    # Variables 3D (stack level axis)
    for gc_name, arrays in pressure_arrays.items():
        if arrays:
            stacked = np.stack(arrays, axis=0)  # (level, lat, lon)
            ds[gc_name] = (("level", "lat", "lon"), stacked)

    # Tri des coords en ordre croissant (GraphCast l'exige)
    ds = ds.sortby("lat", ascending=True)
    ds = ds.sortby("lon", ascending=True)
    ds = ds.sortby("level", ascending=True)

    return ds


# ───────────────────────────────────────────────────────────────────────────
# ASSEMBLAGE DES 2 SNAPSHOTS T-6h + T0
# ───────────────────────────────────────────────────────────────────────────

def assemble_run(run_datetime: datetime, run_dir: Path) -> xr.Dataset:
    """
    Assemble les 2 snapshots (T-6h, T0) d'un run en 1 Dataset GraphCast.

    Structure finale :
    - Dimensions : (batch=1, time=2, level=13, lat=45, lon=65)
    - time = [T-6h, T0] en datetime64
    """
    logger.info(f"\n🔧 Assemblage run {run_datetime.strftime('%Y-%m-%d %Hh UTC')}")

    t_minus_6h = run_datetime - timedelta(hours=6)
    t_zero = run_datetime

    # Charger les 2 snapshots
    ds_t_minus = load_snapshot(run_dir / "t_minus_6h")
    ds_t_zero = load_snapshot(run_dir / "t_zero")

    # Ajouter dimension time à chaque snapshot
    ds_t_minus = ds_t_minus.expand_dims(time=[np.datetime64(t_minus_6h)])
    ds_t_zero = ds_t_zero.expand_dims(time=[np.datetime64(t_zero)])

    # Concaténer sur axe time
    ds_combined = xr.concat([ds_t_minus, ds_t_zero], dim="time")

    # Ajouter dimension batch=1 (exigée par GraphCast)
    ds_final = ds_combined.expand_dims(batch=[0], axis=0)

    return ds_final


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def parse_all_runs():
    """Parse tous les runs présents dans INPUT_DIR."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Lister tous les dossiers de runs (format YYYYMMDD_HH)
    run_dirs = sorted(
        [d for d in INPUT_DIR.iterdir() if d.is_dir() and len(d.name) == 11]
    )

    logger.info("=" * 70)
    logger.info(f"🔧 PARSING GDAS → NetCDF")
    logger.info("=" * 70)
    logger.info(f"   Entrée  : {INPUT_DIR}")
    logger.info(f"   Sortie  : {OUTPUT_DIR}")
    logger.info(f"   Runs trouvés : {len(run_dirs)}")

    results = {"success": [], "failed": []}

    for i, run_dir in enumerate(run_dirs, 1):
        # Parser le datetime depuis le nom (ex: "20260416_00")
        try:
            date_part, hour_part = run_dir.name.split("_")
            run_dt = datetime.strptime(date_part, "%Y%m%d").replace(
                hour=int(hour_part)
            )
        except ValueError:
            logger.warning(f"   ⚠️ Format inattendu : {run_dir.name}")
            continue

        logger.info(f"\n{'=' * 70}")
        logger.info(f"[{i}/{len(run_dirs)}] {run_dir.name}")
        logger.info(f"{'=' * 70}")

        try:
            ds = assemble_run(run_dt, run_dir)

            # Sauvegarde NetCDF
            output_path = OUTPUT_DIR / f"gdas_{run_dir.name}.nc"
            ds.to_netcdf(output_path)

            size_kb = output_path.stat().st_size / 1024
            logger.info(f"\n  ✅ Sauvegardé : {output_path.name} ({size_kb:.1f} Ko)")
            logger.info(f"     Dimensions : {dict(ds.sizes)}")
            logger.info(f"     Variables  : {len(ds.data_vars)}")

            results["success"].append(run_dir.name)
        except Exception as e:
            logger.error(f"\n  ❌ Erreur : {e}")
            import traceback
            logger.error(traceback.format_exc())
            results["failed"].append(run_dir.name)

    # Récap
    logger.info(f"\n{'=' * 70}")
    logger.info(f"✅ PARSING TERMINÉ")
    logger.info(f"{'=' * 70}")
    logger.info(f"   Succès : {len(results['success'])}/{len(run_dirs)}")
    logger.info(f"   Échecs : {len(results['failed'])}/{len(run_dirs)}")

    if results["failed"]:
        logger.warning(f"\n⚠️ Runs en échec :")
        for name in results["failed"]:
            logger.warning(f"   • {name}")

    # Taille totale sortie
    total_size_mb = sum(f.stat().st_size for f in OUTPUT_DIR.glob("*.nc")) / (1024 * 1024)
    logger.info(f"\n📊 Taille totale NetCDF : {total_size_mb:.1f} Mo")
    logger.info(f"📁 Sortie : {OUTPUT_DIR}")


if __name__ == "__main__":
    try:
        parse_all_runs()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompu par l'utilisateur")
        sys.exit(1)
