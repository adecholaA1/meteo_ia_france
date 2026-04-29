"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Parsing AROME GRIB2 → NetCDF propre
FICHIER  : scripts/arome/parse_arome.py
RÔLE     : Lit les 4 fichiers GRIB2 SP1 d'un run AROME et produit un NetCDF
           propre avec :
             - Zone géographique filtrée (France métropolitaine)
             - Sous-échantillonné à 0.25° (matching GraphCast/ERA5)
             - 4 timestamps cibles uniquement (00h, 06h, 12h, 18h UTC J+1)
             - 5 variables : t2m, u10, v10, msl, tp_6h_mm (cumul calculé)
═══════════════════════════════════════════════════════════════════════════

ENTRÉES (4 GRIB2 par run dans data/arome_raw/)
-----------------------------------------------
  - arome__0025__SP1__00H06H__YYYY-MM-DDTHH:00:00Z.grib2
  - arome__0025__SP1__07H12H__YYYY-MM-DDTHH:00:00Z.grib2
  - arome__0025__SP1__13H18H__YYYY-MM-DDTHH:00:00Z.grib2
  - arome__0025__SP1__19H24H__YYYY-MM-DDTHH:00:00Z.grib2

SORTIE (1 NetCDF par run dans data/arome_ready/)
-------------------------------------------------
  arome_YYYY-MM-DD_HHz.nc

  Contenu :
    - Dimensions : (time=4, latitude=45, longitude=65)
    - Variables  : t2m (K), u10 (m/s), v10 (m/s), msl (Pa), tp_6h_mm (mm)
    - Coords     : time, latitude, longitude, run_timestamp

CONVENTIONS TEMPORELLES
-----------------------
Pour run 18z du jour J :
  T+6h  → timestamp = 00h UTC J+1
  T+12h → timestamp = 06h UTC J+1
  T+18h → timestamp = 12h UTC J+1
  T+24h → timestamp = 18h UTC J+1

CALCUL DU CUMUL tp_6h
---------------------
AROME donne tp en cumul depuis T0 du forecast. Pour avoir cumul 6h :
  tp_6h(T+6h)  = tp_cumul(T+6h)                       (cumul 0→6h depuis T0)
  tp_6h(T+12h) = tp_cumul(T+12h) - tp_cumul(T+6h)
  tp_6h(T+18h) = tp_cumul(T+18h) - tp_cumul(T+12h)
  tp_6h(T+24h) = tp_cumul(T+24h) - tp_cumul(T+18h)

ZONE GÉOGRAPHIQUE (mêmes bornes que GraphCast/ERA5)
----------------------------------------------------
  - Latitude  : 41° à 52° N
  - Longitude : -6° à +10° E
  - Résolution cible : 0.25° × 0.25° = 45 × 65 = 2925 points

USAGE
-----
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts

    # Parser un run unique
    python -m arome.parse_arome --date 2026-04-23 --run 18

    # Parser une plage de dates
    python -m arome.parse_arome --start-date 2026-04-16 --end-date 2026-04-23 --run 18

    # Skip si NetCDF déjà présent
    python -m arome.parse_arome --start-date 2026-04-16 --end-date 2026-04-23 --run 18 --skip-existing

TEMPS ESTIMÉ : ~5-10 sec par run
═══════════════════════════════════════════════════════════════════════════
"""

# Suppression warnings cfgrib bénins
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*ecCodes.*")

import argparse
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
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
INPUT_DIR = BASE_DIR / "data" / "arome_raw"
OUTPUT_DIR = BASE_DIR / "data" / "arome_ready"

# Zone géographique (mêmes bornes que GraphCast/ERA5)
LAT_MIN, LAT_MAX = 41.0, 52.0
LON_MIN, LON_MAX = -6.0, 10.0
GRID_RESOLUTION = 0.25

# Grille cible 0.25°
TARGET_LATS = np.arange(LAT_MIN, LAT_MAX + GRID_RESOLUTION / 2, GRID_RESOLUTION)
TARGET_LONS = np.arange(LON_MIN, LON_MAX + GRID_RESOLUTION / 2, GRID_RESOLUTION)

# Les 4 ranges (= 4 fichiers par run)
TIME_RANGES = ["00H06H", "07H12H", "13H18H", "19H24H"]

# Les 4 horizons cibles (T+6h, T+12h, T+18h, T+24h)
# = 00h, 06h, 12h, 18h UTC J+1 (si run 18z)
TARGET_HORIZONS_H = [6, 12, 18, 24]

# Mapping horizon → range qui le contient
HORIZON_TO_RANGE = {
    6:  "00H06H",
    12: "07H12H",
    18: "13H18H",
    24: "19H24H",
}

# Filtres cfgrib pour extraire chaque variable depuis SP1
VARIABLE_FILTERS = {
    "t2m": {
        "filter_by_keys": {
            "stepType": "instant",
            "typeOfLevel": "heightAboveGround",
            "level": 2,
        },
        "var_name": "t2m",
        "units": "K",
    },
    "u10": {
        "filter_by_keys": {
            "stepType": "instant",
            "typeOfLevel": "heightAboveGround",
            "level": 10,
            "shortName": "10u",
        },
        "var_name": "u10",
        "units": "m/s",
    },
    "v10": {
        "filter_by_keys": {
            "stepType": "instant",
            "typeOfLevel": "heightAboveGround",
            "level": 10,
            "shortName": "10v",
        },
        "var_name": "v10",
        "units": "m/s",
    },
    "msl": {
        "filter_by_keys": {
            "stepType": "instant",
            "typeOfLevel": "meanSea",
        },
        "var_name": "prmsl",
        "units": "Pa",
    },
    "tp": {
        "filter_by_keys": {
            "stepType": "accum",
            "typeOfLevel": "surface",
            "shortName": "tp",
        },
        "var_name": "tp",
        "units": "kg/m²",  # = mm
    },
}


# ───────────────────────────────────────────────────────────────────────────
# CHEMINS DE FICHIERS
# ───────────────────────────────────────────────────────────────────────────

def get_grib_path(run_dt: datetime, time_range: str) -> Path:
    """Retourne le chemin d'un fichier GRIB2 d'entrée."""
    run_iso = run_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    filename = f"arome__0025__SP1__{time_range}__{run_iso}.grib2"
    return INPUT_DIR / filename


def get_output_path(run_dt: datetime) -> Path:
    """Retourne le chemin du NetCDF de sortie."""
    return OUTPUT_DIR / f"arome_{run_dt.strftime('%Y-%m-%d_%Hz')}.nc"


# ───────────────────────────────────────────────────────────────────────────
# EXTRACTION D'UNE VARIABLE D'UN FICHIER GRIB2
# ───────────────────────────────────────────────────────────────────────────

def extract_variable_from_grib(grib_path: Path, var_canonical: str) -> xr.DataArray:
    """
    Extrait une variable d'un fichier GRIB2 AROME via le filtre cfgrib approprié.

    Args:
        grib_path: chemin vers le fichier GRIB2
        var_canonical: nom canonique de la variable (t2m, u10, v10, msl, tp)

    Returns:
        DataArray avec dims (step, latitude, longitude)
    """
    config = VARIABLE_FILTERS[var_canonical]
    filter_keys = config["filter_by_keys"]
    var_name = config["var_name"]

    ds = xr.open_dataset(
        grib_path,
        engine="cfgrib",
        backend_kwargs={
            "filter_by_keys": filter_keys,
            "indexpath": "",  # éviter création .idx
        },
    )

    if var_name not in ds.data_vars:
        ds.close()
        raise KeyError(f"Variable '{var_name}' introuvable dans {grib_path.name} avec filtre {filter_keys}")

    da = ds[var_name].copy()  # copie pour pouvoir fermer le dataset
    ds.close()

    return da


# ───────────────────────────────────────────────────────────────────────────
# FILTRAGE ZONE + SOUS-ÉCHANTILLONNAGE 0.25°
# ───────────────────────────────────────────────────────────────────────────

def crop_and_resample(da: xr.DataArray) -> xr.DataArray:
    """
    Filtre la zone géographique (France) puis sous-échantillonne à 0.25°
    via plus proche voisin (méthode validée).

    AROME fournit des données à 0.025° sur lat 37.5-55.4, lon -12 à 16.
    On cible : lat 41-52, lon -6 à 10, à 0.25° = 45 × 65 = 2925 points.
    """
    # 1. Filtrer la zone (un peu plus large pour avoir une marge)
    da_cropped = da.sel(
        latitude=slice(LAT_MAX + 0.1, LAT_MIN - 0.1),  # AROME est ordonné nord→sud
        longitude=slice(LON_MIN - 0.1, LON_MAX + 0.1),
    )

    # 2. Sous-échantillonnage par plus proche voisin
    da_resampled = da_cropped.sel(
        latitude=TARGET_LATS,
        longitude=TARGET_LONS,
        method="nearest",
    )

    return da_resampled


# ───────────────────────────────────────────────────────────────────────────
# EXTRACTION D'UN HORIZON SPÉCIFIQUE
# ───────────────────────────────────────────────────────────────────────────

def extract_horizon_value(da: xr.DataArray, horizon_h: int) -> np.ndarray:
    """
    Extrait la valeur d'une variable à un horizon spécifique (en heures depuis T0).

    AROME utilise la coord 'step' = timedelta depuis T0 du run.
    """
    target_step = np.timedelta64(horizon_h, "h")

    # Sélection par valeur de step
    if "step" in da.dims:
        # Trouver l'index correspondant
        step_values = da.step.values
        # Conversion de timedelta64 vers heures
        step_hours = step_values.astype("timedelta64[h]").astype(int)

        if horizon_h not in step_hours:
            available = list(step_hours)
            raise ValueError(f"Horizon T+{horizon_h}h non disponible. Disponibles : {available}")

        idx = list(step_hours).index(horizon_h)
        return da.isel(step=idx).values
    else:
        # Pas de dim step → la variable n'a qu'1 timestep, on prend tel quel
        return da.values


# ───────────────────────────────────────────────────────────────────────────
# PARSING D'UN RUN (les 4 fichiers GRIB2)
# ───────────────────────────────────────────────────────────────────────────

def parse_one_run(run_dt: datetime) -> xr.Dataset:
    """
    Parse les 4 fichiers GRIB2 d'un run AROME et retourne un Dataset propre.

    Returns:
        xr.Dataset avec :
          - Dims : (time=4, latitude=45, longitude=65)
          - Vars : t2m, u10, v10, msl, tp_6h_mm
    """
    logger.info(f"\n📂 Parsing run {run_dt.strftime('%Y-%m-%d %Hz UTC')}")

    # Vérifier que les 4 fichiers GRIB2 existent
    grib_paths = {tr: get_grib_path(run_dt, tr) for tr in TIME_RANGES}
    for tr, path in grib_paths.items():
        if not path.exists():
            raise FileNotFoundError(f"GRIB2 manquant : {path}")

    # ═══ Extraction des variables INSTANTANÉES (t2m, u10, v10, msl) ═══
    # Pour chaque variable, on lit les 4 fichiers et on extrait les 4 horizons cibles
    logger.info(f"   🔧 Extraction variables instantanées (t2m, u10, v10, msl)")

    instant_vars = {}
    for var_canonical in ["t2m", "u10", "v10", "msl"]:
        values_per_horizon = []

        for horizon_h in TARGET_HORIZONS_H:
            time_range = HORIZON_TO_RANGE[horizon_h]
            grib_path = grib_paths[time_range]

            # Lire la variable dans le bon fichier
            da_full = extract_variable_from_grib(grib_path, var_canonical)
            # Crop + resample à 0.25°
            da_resampled = crop_and_resample(da_full)
            # Extraire la valeur à l'horizon voulu
            values_2d = extract_horizon_value(da_resampled, horizon_h)
            values_per_horizon.append(values_2d)

        # Empiler les 4 horizons → shape (4, lat, lon)
        instant_vars[var_canonical] = np.stack(values_per_horizon, axis=0)
        logger.info(f"      ✅ {var_canonical:5s} : shape={instant_vars[var_canonical].shape}")

    # ═══ Extraction CUMUL tp ═══
    # On lit tp dans les 4 fichiers, on extrait les valeurs cumulées aux horizons 6, 12, 18, 24
    # Puis on calcule les cumuls 6h par soustraction
    logger.info(f"   🔧 Extraction cumul tp + calcul tp_6h")

    tp_cumul = {}  # {horizon_h: array(lat, lon)}
    for horizon_h in TARGET_HORIZONS_H:
        time_range = HORIZON_TO_RANGE[horizon_h]
        grib_path = grib_paths[time_range]

        da_full = extract_variable_from_grib(grib_path, "tp")
        da_resampled = crop_and_resample(da_full)
        tp_cumul[horizon_h] = extract_horizon_value(da_resampled, horizon_h)

    # Calcul des cumuls 6h par soustraction
    tp_6h_per_horizon = []
    prev_cumul = None  # T+0h = 0 mm

    for horizon_h in TARGET_HORIZONS_H:
        cumul_now = tp_cumul[horizon_h]
        if prev_cumul is None:
            # T+6h : cumul 0h→6h = cumul actuel (pas de soustraction)
            cumul_6h = cumul_now
        else:
            cumul_6h = cumul_now - prev_cumul

        # Clip à 0 (pas de pluie négative possible)
        cumul_6h = np.maximum(cumul_6h, 0.0).astype(np.float32)
        tp_6h_per_horizon.append(cumul_6h)
        prev_cumul = cumul_now

    tp_6h_array = np.stack(tp_6h_per_horizon, axis=0)
    logger.info(f"      ✅ tp_6h : shape={tp_6h_array.shape}, min={tp_6h_array.min():.3f}mm, max={tp_6h_array.max():.3f}mm, moy={tp_6h_array.mean():.3f}mm")

    # ═══ Construction du Dataset final ═══
    target_timestamps = [
        run_dt + timedelta(hours=h) for h in TARGET_HORIZONS_H
    ]

    ds = xr.Dataset(
        data_vars={
            "t2m": (["time", "latitude", "longitude"], instant_vars["t2m"], {"units": "K", "long_name": "2 metre temperature"}),
            "u10": (["time", "latitude", "longitude"], instant_vars["u10"], {"units": "m/s", "long_name": "10 metre U wind component"}),
            "v10": (["time", "latitude", "longitude"], instant_vars["v10"], {"units": "m/s", "long_name": "10 metre V wind component"}),
            "msl": (["time", "latitude", "longitude"], instant_vars["msl"], {"units": "Pa", "long_name": "Mean sea level pressure"}),
            "tp_6h_mm": (["time", "latitude", "longitude"], tp_6h_array, {"units": "mm", "long_name": "Total precipitation cumulated over 6h"}),
        },
        coords={
            "time": np.array([t.replace(tzinfo=None) for t in target_timestamps], dtype="datetime64[ns]"),
            "latitude": TARGET_LATS,
            "longitude": TARGET_LONS,
        },
        attrs={
            "source": "AROME 0.025° (Météo-France) via data.gouv.fr",
            "run_timestamp": run_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "resampled_to": "0.25° (nearest neighbor)",
            "zone": f"lat {LAT_MIN}-{LAT_MAX}°N, lon {LON_MIN}-{LON_MAX}°E",
        },
    )

    return ds


# ───────────────────────────────────────────────────────────────────────────
# PARSING + SAUVEGARDE D'UN RUN
# ───────────────────────────────────────────────────────────────────────────

def parse_and_save_run(run_dt: datetime, skip_existing: bool = False) -> Path:
    """
    Parse un run et sauvegarde le NetCDF.
    Retourne le chemin du NetCDF.
    """
    output_path = get_output_path(run_dt)

    if skip_existing and output_path.exists():
        logger.info(f"\n📂 Run {run_dt.strftime('%Y-%m-%d %Hz')} : NetCDF déjà présent, skip ({output_path.name})")
        return output_path

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    ds = parse_one_run(run_dt)

    logger.info(f"   💾 Sauvegarde {output_path.name}")
    ds.to_netcdf(output_path)
    ds.close()

    size_kb = output_path.stat().st_size / 1024
    elapsed = time.time() - t0
    logger.info(f"      ✅ {output_path.name} ({size_kb:.0f} Ko, {elapsed:.1f}s)")

    return output_path


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Parsing AROME GRIB2 → NetCDF propre",
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
                        help="Skip si NetCDF déjà présent")
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Validation
    if args.date and (args.start_date or args.end_date):
        logger.error("❌ Utilise SOIT --date SOIT --start-date/--end-date")
        sys.exit(1)
    if not args.date and not (args.start_date and args.end_date):
        logger.error("❌ Spécifie --date OU --start-date/--end-date")
        sys.exit(1)

    # Banner
    logger.info("╔" + "═" * 68 + "╗")
    msg = "🇫🇷 PARSING AROME GRIB2 → NetCDF"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")

    t_start = time.time()
    results = {"success": [], "failed": [], "skipped": []}

    # Liste des dates à traiter
    if args.date:
        try:
            dates = [datetime.strptime(args.date, "%Y-%m-%d")]
        except ValueError:
            logger.error(f"❌ Format date invalide : {args.date}")
            sys.exit(1)
    else:
        try:
            start = datetime.strptime(args.start_date, "%Y-%m-%d")
            end = datetime.strptime(args.end_date, "%Y-%m-%d")
        except ValueError as e:
            logger.error(f"❌ Format date invalide : {e}")
            sys.exit(1)

        if start > end:
            logger.error(f"❌ start-date doit être <= end-date")
            sys.exit(1)

        dates = []
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)

    logger.info(f"\n📅 {len(dates)} run(s) à parser")

    # Boucle
    for d in dates:
        run_dt = d.replace(hour=args.run, tzinfo=timezone.utc)
        try:
            output_path = parse_and_save_run(run_dt, skip_existing=args.skip_existing)
            results["success"].append((run_dt, output_path))
        except FileNotFoundError as e:
            logger.error(f"❌ {run_dt.strftime('%Y-%m-%d %Hz')} : {e}")
            results["failed"].append((run_dt, str(e)))
        except Exception as e:
            logger.error(f"❌ {run_dt.strftime('%Y-%m-%d %Hz')} : {e}")
            import traceback
            logger.error(traceback.format_exc())
            results["failed"].append((run_dt, str(e)))

    # Récap
    elapsed_min = (time.time() - t_start) / 60
    logger.info("\n" + "╔" + "═" * 68 + "╗")
    msg = f"✅ PARSING TERMINÉ en {elapsed_min:.1f} min"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")
    logger.info(f"\n📊 Résultats :")
    logger.info(f"   Succès : {len(results['success'])}/{len(dates)}")
    logger.info(f"   Échecs : {len(results['failed'])}/{len(dates)}")

    if results["failed"]:
        logger.warning(f"\n⚠️ Runs en échec :")
        for run_dt, err in results["failed"]:
            logger.warning(f"   • {run_dt.strftime('%Y-%m-%d %Hz')} : {err[:80]}")

    sys.exit(0 if not results["failed"] else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompu")
        sys.exit(1)
