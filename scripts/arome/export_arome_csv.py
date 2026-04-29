"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Export CSV AROME pour DB
FICHIER  : scripts/arome/export_arome_csv.py
RÔLE     : Lit le NetCDF AROME parsé et génère un CSV au format DB
           avec les 8 variables harmonisées avec GraphCast et ERA5.
═══════════════════════════════════════════════════════════════════════════

ENTRÉE (.nc dans data/arome_ready/)
-----------------------------------
  arome_YYYY-MM-DD_HHz.nc : 4 timestamps × 5 variables × 45×65

SORTIE (.csv dans data/arome_csv/)
----------------------------------
  arome_YYYY-MM-DD_HHz.csv : 4 timestamps × 8 variables × 45×65 = 93 600 lignes

VARIABLES DU CSV (8 total)
--------------------------
  Directes (5, prises depuis le .nc) :
    - t2m_celsius          (depuis t2m en K → °C)
    - u10_ms               (depuis u10)
    - v10_ms               (depuis v10)
    - msl_hpa              (depuis msl en Pa → hPa)
    - tp_6h_mm             (déjà calculé dans parse_arome.py)

  Dérivées (3, calculées) :
    - wind_speed_10m_ms    = sqrt(u10² + v10²)
    - wind_direction_10m_deg = atan2(-u10, -v10) en degrés (convention météo)
    - toa_wm2              = formule astronomique (solar_utils.py)

FORMAT CSV (compatible avec graphcast_predictions et arome_forecasts)
---------------------------------------------------------------------
  run_datetime_utc,forecast_timestamp_utc,lead_hours,lat,lon,variable_name,value,unit

USAGE
-----
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts

    # Pour 1 run unique
    python -m arome.export_arome_csv --date 2026-04-23 --run 18

    # Pour une plage de dates
    python -m arome.export_arome_csv --start-date 2026-04-16 --end-date 2026-04-23 --run 18

    # Skip si CSV déjà présent
    python -m arome.export_arome_csv --start-date 2026-04-16 --end-date 2026-04-23 \
                                      --run 18 --skip-existing

TEMPS ESTIMÉ : ~1-2 sec par run
═══════════════════════════════════════════════════════════════════════════
"""

import argparse
import csv
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import xarray as xr

# Import solar_utils pour le calcul TOA
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.solar_utils import calculate_toa_grid_fast


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
INPUT_DIR = BASE_DIR / "data" / "arome_ready"
OUTPUT_DIR = BASE_DIR / "data" / "arome_csv"

# Header du CSV (cohérent avec arome_forecasts)
CSV_HEADER = [
    "run_datetime_utc",
    "forecast_timestamp_utc",
    "lead_hours",
    "lat",
    "lon",
    "variable_name",
    "value",
    "unit",
]


# ───────────────────────────────────────────────────────────────────────────
# CHEMINS
# ───────────────────────────────────────────────────────────────────────────

def get_input_path(run_dt: datetime) -> Path:
    return INPUT_DIR / f"arome_{run_dt.strftime('%Y-%m-%d_%Hz')}.nc"


def get_output_path(run_dt: datetime) -> Path:
    return OUTPUT_DIR / f"arome_{run_dt.strftime('%Y-%m-%d_%Hz')}.csv"


# ───────────────────────────────────────────────────────────────────────────
# CALCUL DES VARIABLES DÉRIVÉES
# ───────────────────────────────────────────────────────────────────────────

def compute_derived_variables(ds: xr.Dataset, run_dt: datetime) -> dict:
    """
    Calcule wind_speed, wind_direction et toa pour chaque timestamp.

    Returns:
        dict {(timestamp_idx, var_name): array(lat, lon)}
    """
    derived = {}
    lats = ds.latitude.values
    lons = ds.longitude.values
    timestamps = ds.time.values

    for t_idx, ts_np in enumerate(timestamps):
        # Convertir numpy datetime64 en datetime Python aware UTC
        ts_dt = datetime.utcfromtimestamp(
            (ts_np - np.datetime64("1970-01-01T00:00:00")) / np.timedelta64(1, "s")
        ).replace(tzinfo=timezone.utc)

        u10 = ds.u10.isel(time=t_idx).values.astype(np.float32)
        v10 = ds.v10.isel(time=t_idx).values.astype(np.float32)

        # Wind speed
        wind_speed = np.sqrt(u10**2 + v10**2).astype(np.float32)
        derived[(t_idx, "wind_speed_10m_ms")] = (wind_speed, "m/s")

        # Wind direction (convention météo : d'où vient le vent)
        wind_direction = np.rad2deg(np.arctan2(-u10, -v10)).astype(np.float32)
        wind_direction = (wind_direction + 360.0) % 360.0
        derived[(t_idx, "wind_direction_10m_deg")] = (wind_direction, "°")

        # TOA astronomique
        toa_grid = calculate_toa_grid_fast(ts_dt, lats, lons).astype(np.float32)
        derived[(t_idx, "toa_wm2")] = (toa_grid, "W/m²")

    return derived


# ───────────────────────────────────────────────────────────────────────────
# CONVERSION D'UN RUN EN CSV
# ───────────────────────────────────────────────────────────────────────────

def export_one_run(run_dt: datetime, skip_existing: bool = False) -> Path:
    """Exporte le NetCDF d'un run en CSV format DB."""
    input_path = get_input_path(run_dt)
    output_path = get_output_path(run_dt)

    if not input_path.exists():
        raise FileNotFoundError(f"NetCDF manquant : {input_path}")

    if skip_existing and output_path.exists():
        logger.info(f"   ✅ {output_path.name} déjà présent, skip")
        return output_path

    logger.info(f"\n📂 Export {input_path.name}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    ds = xr.open_dataset(input_path)

    lats = ds.latitude.values
    lons = ds.longitude.values
    timestamps = ds.time.values

    logger.info(f"   📊 Dataset : {len(timestamps)} timestamps × {len(lats)} lat × {len(lons)} lon")

    # Calculer les variables dérivées
    derived = compute_derived_variables(ds, run_dt)

    # Mapping variable → (array_func, unit, name_csv)
    # array_func prend (t_idx) et retourne array(lat, lon) avec conversion d'unité
    direct_vars = {
        "t2m_celsius":     (lambda t: (ds.t2m.isel(time=t).values - 273.15).astype(np.float32), "°C"),
        "u10_ms":          (lambda t: ds.u10.isel(time=t).values.astype(np.float32), "m/s"),
        "v10_ms":          (lambda t: ds.v10.isel(time=t).values.astype(np.float32), "m/s"),
        "msl_hpa":         (lambda t: (ds.msl.isel(time=t).values / 100.0).astype(np.float32), "hPa"),
        "tp_6h_mm":        (lambda t: ds.tp_6h_mm.isel(time=t).values.astype(np.float32), "mm"),
    }

    derived_var_names = ["wind_speed_10m_ms", "wind_direction_10m_deg", "toa_wm2"]

    # ═══ Écriture CSV ═══
    n_rows = 0
    run_iso = run_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(CSV_HEADER)

        for t_idx, ts_np in enumerate(timestamps):
            # Convertir le timestamp en datetime Python
            ts_dt = datetime.utcfromtimestamp(
                (ts_np - np.datetime64("1970-01-01T00:00:00")) / np.timedelta64(1, "s")
            ).replace(tzinfo=timezone.utc)
            ts_iso = ts_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            lead_hours = int((ts_dt - run_dt).total_seconds() / 3600)

            # Précalcul de toutes les variables pour ce timestamp
            vars_for_ts = {}
            for var_name, (array_func, unit) in direct_vars.items():
                vars_for_ts[var_name] = (array_func(t_idx), unit)
            for var_name in derived_var_names:
                vars_for_ts[var_name] = derived[(t_idx, var_name)]

            # Écrire les lignes
            for lat_idx, lat in enumerate(lats):
                for lon_idx, lon in enumerate(lons):
                    for var_name, (values_array, unit) in vars_for_ts.items():
                        value = float(values_array[lat_idx, lon_idx])
                        if np.isnan(value):
                            continue
                        writer.writerow([
                            run_iso,
                            ts_iso,
                            lead_hours,
                            f"{float(lat):.4f}",
                            f"{float(lon):.4f}",
                            var_name,
                            f"{value:.4f}",
                            unit,
                        ])
                        n_rows += 1

    ds.close()

    elapsed = time.time() - t0
    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ {output_path.name} ({n_rows:,} lignes, {size_mb:.1f} Mo, {elapsed:.1f}s)")
    return output_path


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def parse_arguments():
    parser = argparse.ArgumentParser(description="Export CSV AROME pour DB")
    parser.add_argument("--date", type=str, default=None,
                        help="Date d'un run unique (YYYY-MM-DD)")
    parser.add_argument("--start-date", type=str, default=None,
                        help="Date de début (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None,
                        help="Date de fin (YYYY-MM-DD)")
    parser.add_argument("--run", type=int, default=18, choices=[0, 3, 6, 9, 12, 15, 18, 21],
                        help="Heure UTC du run (défaut: 18)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip si CSV déjà présent")
    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.date and (args.start_date or args.end_date):
        logger.error("❌ Utilise SOIT --date SOIT --start-date/--end-date")
        sys.exit(1)
    if not args.date and not (args.start_date and args.end_date):
        logger.error("❌ Spécifie --date OU --start-date/--end-date")
        sys.exit(1)

    # Banner
    logger.info("╔" + "═" * 68 + "╗")
    msg = "🇫🇷 EXPORT CSV AROME"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")

    t_start = time.time()
    results = {"success": [], "failed": []}

    # Liste des dates
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

        dates = []
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)

    logger.info(f"\n📅 {len(dates)} run(s) à exporter")

    # Boucle
    for d in dates:
        run_dt = d.replace(hour=args.run, tzinfo=timezone.utc)
        try:
            output_path = export_one_run(run_dt, skip_existing=args.skip_existing)
            results["success"].append((run_dt, output_path))
        except Exception as e:
            logger.error(f"❌ {run_dt.strftime('%Y-%m-%d %Hz')} : {e}")
            import traceback
            logger.error(traceback.format_exc())
            results["failed"].append((run_dt, str(e)))

    # Récap
    elapsed_min = (time.time() - t_start) / 60
    logger.info("\n" + "╔" + "═" * 68 + "╗")
    msg = f"✅ EXPORT CSV TERMINÉ en {elapsed_min:.1f} min"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")
    logger.info(f"\n📊 Résultats :")
    logger.info(f"   Succès : {len(results['success'])}/{len(dates)}")
    logger.info(f"   Échecs : {len(results['failed'])}/{len(dates)}")

    sys.exit(0 if not results["failed"] else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompu")
        sys.exit(1)
