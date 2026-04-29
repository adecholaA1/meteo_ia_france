"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Export CSV des prédictions GraphCast pour DB
FICHIER  : scripts/graphcast_gfs/export_graphcast_csv.py
RÔLE     : Extrait les variables surface des NetCDF GraphCast, calcule les
           variables dérivées (vitesse/direction vent, TOA astronomique),
           et exporte un CSV par run au format LONG prêt pour la DB.
═══════════════════════════════════════════════════════════════════════════

ARCHITECTURE DE STOCKAGE
-------------------------
  data/graphcast_predictions/      ← NetCDF (source de vérité, archive)
  data/graphcast_predictions_csv/  ← CSV (pour DB + export public v1.1)

Les NetCDF sont CONSERVÉS. Les CSV sont REGÉNÉRÉS depuis les NetCDF
chaque fois qu'on ajoute de nouvelles variables dérivées.

VARIABLES EXPORTÉES (v1.0 — surface uniquement)
-----------------------------------------------
  Pour l'éolien :
    - u10_ms               : composante U vent à 10m
    - v10_ms               : composante V vent à 10m
    - wind_speed_10m_ms    : vitesse vent (= sqrt(u² + v²))
    - wind_direction_10m_deg : direction vent (d'où vient, convention météo)

  Pour le solaire :
    - toa_wm2              : irradiation solaire TOA (astronomique)
    - t2m_celsius          : température à 2m (rendement PV)
    - msl_hpa              : pression réduite au niveau mer

  Générales :
    - tp_6h_mm             : précipitation cumulée 6h

FORMAT CSV (LONG)
-----------------
  run_datetime_utc,forecast_timestamp_utc,lead_hours,lat,lon,variable_name,value,unit

EXEMPLE
-------
  run_datetime_utc,forecast_timestamp_utc,lead_hours,lat,lon,variable_name,value,unit
  2026-04-16T00:00:00Z,2026-04-16T06:00:00Z,6,41.00,-6.00,t2m_celsius,8.45,°C
  2026-04-16T00:00:00Z,2026-04-16T06:00:00Z,6,41.00,-6.00,wind_speed_10m_ms,3.53,m/s

USAGE
-----
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts
    python -m graphcast_gfs.export_graphcast_csv

TEMPS ESTIMÉ
------------
~30 sec pour les 8 runs (93 600 lignes × 8 = 750 000 lignes CSV)
═══════════════════════════════════════════════════════════════════════════
"""

import csv
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import xarray as xr


# Import solar_utils pour calculer TOA astronomique
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.solar_utils import calculate_toa_grid_fast


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ───────────────────────────────────────────────────────────────────────────

BASE_DIR = Path.home() / "Desktop" / "PROJETS" / "Dev_meteo" / "meteo_ia_france"
INPUT_DIR = BASE_DIR / "data" / "graphcast_predictions"
OUTPUT_DIR = BASE_DIR / "data" / "graphcast_predictions_csv"


# Header du CSV (cohérent avec la table graphcast_predictions)
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
# EXTRACTION DES VARIABLES POUR 1 RUN
# ───────────────────────────────────────────────────────────────────────────

def extract_surface_variables(ds: xr.Dataset) -> dict:
    """
    Extrait les variables surface du dataset GraphCast et fait les conversions
    d'unités + calculs dérivés.

    GraphCast retourne les prédictions avec une dim batch=1 dans un ordre
    imprévisible (parfois avant time, parfois après). On utilise np.squeeze()
    pour enlever toutes les dimensions de taille 1.

    Retourne un dict {variable_name: (values_array, unit)}.
    Les arrays ont shape (time, lat, lon) = (4, 45, 65).
    """
    variables = {}

    def squeeze_batch(arr: np.ndarray) -> np.ndarray:
        """Enlève toutes les dims de taille 1 (typiquement la dim batch)."""
        return np.squeeze(arr)

    # ═══ Variables directes (avec conversions d'unités) ═══

    # t2m : K → °C
    t2m_raw = squeeze_batch(ds["2m_temperature"].values)
    t2m_c = (t2m_raw - 273.15).astype(np.float32)
    variables["t2m_celsius"] = (t2m_c, "°C")

    # u10 : m/s → m/s (pas de conversion)
    u10 = squeeze_batch(ds["10m_u_component_of_wind"].values).astype(np.float32)
    variables["u10_ms"] = (u10, "m/s")

    # v10 : m/s → m/s
    v10 = squeeze_batch(ds["10m_v_component_of_wind"].values).astype(np.float32)
    variables["v10_ms"] = (v10, "m/s")

    # msl : Pa → hPa
    msl_raw = squeeze_batch(ds["mean_sea_level_pressure"].values)
    msl_hpa = (msl_raw / 100.0).astype(np.float32)
    variables["msl_hpa"] = (msl_hpa, "hPa")

    # Total precipitation 6h : m → mm (GraphCast retourne en mètres)
    tp_raw = squeeze_batch(ds["total_precipitation_6hr"].values)
    # Certaines valeurs peuvent être légèrement négatives à cause du modèle
    # On les clip à 0 (pas de pluie négative)
    tp_mm = np.maximum(tp_raw * 1000.0, 0.0).astype(np.float32)
    variables["tp_6h_mm"] = (tp_mm, "mm")

    # ═══ Variables dérivées ═══

    # Vitesse du vent = sqrt(u² + v²)
    wind_speed = np.sqrt(u10**2 + v10**2).astype(np.float32)
    variables["wind_speed_10m_ms"] = (wind_speed, "m/s")

    # Direction du vent (convention météo : d'où vient le vent)
    # atan2(-u, -v) en degrés, ajusté dans [0, 360)
    wind_direction = np.rad2deg(np.arctan2(-u10, -v10)).astype(np.float32)
    wind_direction = (wind_direction + 360.0) % 360.0
    variables["wind_direction_10m_deg"] = (wind_direction, "°")

    return variables


def compute_toa_forcing(ds: xr.Dataset, forecast_timestamps: list) -> np.ndarray:
    """
    Calcule le forcing TOA astronomique pour chaque timestamp de prévision.

    GraphCast ne prédit PAS le TOA (c'est une forçage input). On le calcule
    astronomiquement via solar_utils.py pour cohérence entre GraphCast, ERA5
    et AROME (toutes sources auront le même TOA calculé).

    Retourne un array (4, 45, 65) = (horizons, lat, lon).
    """
    lats = ds.lat.values
    lons = ds.lon.values
    n_times = len(forecast_timestamps)

    toa_array = np.zeros((n_times, len(lats), len(lons)), dtype=np.float32)

    for t_idx, ts in enumerate(forecast_timestamps):
        # S'assurer que le timestamp est timezone-aware
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        toa_grid = calculate_toa_grid_fast(ts, lats, lons)
        toa_array[t_idx, :, :] = toa_grid

    return toa_array


def parse_run_datetime(nc_path: Path) -> datetime:
    """
    Parse la date de run depuis le nom du fichier.
    Ex: graphcast_20260416_00h.nc → 2026-04-16 00:00:00 UTC
    """
    name = nc_path.stem  # graphcast_20260416_00h
    parts = name.split("_")
    date_str = parts[1]  # 20260416
    hour_str = parts[2].rstrip("h")  # 00
    return datetime.strptime(date_str, "%Y%m%d").replace(
        hour=int(hour_str), tzinfo=timezone.utc
    )


def compute_forecast_timestamps(
    run_datetime: datetime, ds: xr.Dataset
) -> list:
    """
    Calcule les timestamps absolus des prévisions en combinant run_datetime
    + les lead_times (timedeltas) du dataset.

    GraphCast retourne time comme des timedeltas : [6h, 12h, 18h, 24h].
    On ajoute run_datetime pour obtenir les timestamps absolus.
    """
    leads = ds.time.values  # timedelta64

    timestamps = []
    for lead_td in leads:
        # Conversion timedelta64 → timedelta Python
        lead_seconds = int(lead_td / np.timedelta64(1, "s"))
        forecast_ts = run_datetime + timedelta(seconds=lead_seconds)
        timestamps.append(forecast_ts)

    return timestamps


# ───────────────────────────────────────────────────────────────────────────
# EXPORT CSV POUR 1 RUN
# ───────────────────────────────────────────────────────────────────────────

def export_run_to_csv(nc_path: Path, output_dir: Path) -> Path:
    """
    Lit le NetCDF d'un run et exporte toutes les observations en CSV LONG.

    Structure du CSV :
        run_datetime_utc, forecast_timestamp_utc, lead_hours,
        lat, lon, variable_name, value, unit

    Nombre de lignes par CSV :
        8 variables × 4 horizons × 45 lat × 65 lon = 93 600 lignes
    """
    run_dt = parse_run_datetime(nc_path)
    logger.info(f"\n📂 Lecture {nc_path.name}")

    # Charger le dataset
    ds = xr.open_dataset(nc_path)

    # Calculer les timestamps de prévision
    forecast_timestamps = compute_forecast_timestamps(run_dt, ds)
    logger.info(
        f"   Run        : {run_dt.strftime('%Y-%m-%d %Hh UTC')}"
    )
    logger.info(f"   Horizons   : {len(forecast_timestamps)}")
    for ts in forecast_timestamps:
        lead_h = int((ts - run_dt).total_seconds() / 3600)
        logger.info(f"     +{lead_h}h = {ts.strftime('%Y-%m-%d %Hh UTC')}")
    logger.info(f"   Grille     : {ds.sizes['lat']} lat × {ds.sizes['lon']} lon")

    # Extraire les variables surface + dérivées
    logger.info(f"   🔧 Extraction des variables surface...")
    variables = extract_surface_variables(ds)
    logger.info(f"      ✅ {len(variables)} variables directes + dérivées")

    # Calculer le forcing TOA
    logger.info(f"   🔧 Calcul TOA astronomique...")
    toa_array = compute_toa_forcing(ds, forecast_timestamps)
    variables["toa_wm2"] = (toa_array, "W/m²")
    logger.info(f"      ✅ TOA calculé pour {len(forecast_timestamps)} horizons")

    # Coordonnées spatiales
    lats = ds.lat.values
    lons = ds.lon.values

    # ═══ Écriture du CSV ═══
    date_str = run_dt.strftime("%Y%m%d")
    hour_str = run_dt.strftime("%H")
    output_path = output_dir / f"graphcast_{date_str}_{hour_str}h.csv"

    logger.info(f"   📝 Écriture CSV...")

    # Vérification de sécurité : toutes les variables doivent avoir la même shape 3D
    expected_shape = (len(forecast_timestamps), len(lats), len(lons))
    for var_name, (values_array, _) in variables.items():
        if values_array.shape != expected_shape:
            raise ValueError(
                f"Shape inattendue pour '{var_name}' : {values_array.shape}, "
                f"attendu {expected_shape}"
            )

    t0 = time.time()
    run_iso = run_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    n_rows = 0

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(CSV_HEADER)

        # Parcourir dans l'ordre : time → lat → lon → variable
        for t_idx, fcst_ts in enumerate(forecast_timestamps):
            fcst_iso = fcst_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
            lead_h = int((fcst_ts - run_dt).total_seconds() / 3600)

            for lat_idx, lat in enumerate(lats):
                for lon_idx, lon in enumerate(lons):
                    for var_name, (values_array, unit) in variables.items():
                        value = float(values_array[t_idx, lat_idx, lon_idx])
                        # Gérer les NaN éventuels
                        if np.isnan(value):
                            continue
                        writer.writerow(
                            [
                                run_iso,
                                fcst_iso,
                                lead_h,
                                f"{float(lat):.4f}",
                                f"{float(lon):.4f}",
                                var_name,
                                f"{value:.4f}",
                                unit,
                            ]
                        )
                        n_rows += 1

    elapsed = time.time() - t0
    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ {output_path.name} ({n_rows:,} lignes, {size_mb:.1f} Mo, {elapsed:.1f}s)")

    return output_path


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 70)
    logger.info("📊 EXPORT CSV GRAPHCAST → pour alimentation DB")
    logger.info("=" * 70)
    logger.info(f"   Entrée : {INPUT_DIR}")
    logger.info(f"   Sortie : {OUTPUT_DIR}")

    if not INPUT_DIR.exists():
        logger.error(f"❌ Dossier d'entrée introuvable : {INPUT_DIR}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Lister les fichiers NetCDF
    nc_files = sorted(INPUT_DIR.glob("graphcast_*.nc"))
    if not nc_files:
        logger.error(f"❌ Aucun fichier graphcast_*.nc trouvé")
        sys.exit(1)

    logger.info(f"\n📅 Fichiers à traiter : {len(nc_files)}")
    for f in nc_files:
        logger.info(f"   • {f.name}")

    # Export
    t_start = time.time()
    results = {"success": [], "failed": []}

    for nc_path in nc_files:
        try:
            csv_path = export_run_to_csv(nc_path, OUTPUT_DIR)
            results["success"].append(csv_path)
        except Exception as e:
            logger.error(f"   ❌ Erreur : {e}")
            import traceback
            logger.error(traceback.format_exc())
            results["failed"].append(nc_path.name)

    # Récap final
    elapsed_min = (time.time() - t_start) / 60
    logger.info(f"\n{'=' * 70}")
    logger.info(f"✅ EXPORT TERMINÉ en {elapsed_min:.1f} min")
    logger.info(f"{'=' * 70}")
    logger.info(f"   Succès : {len(results['success'])}/{len(nc_files)}")
    logger.info(f"   Échecs : {len(results['failed'])}/{len(nc_files)}")

    if results["failed"]:
        logger.warning("\n⚠️ Fichiers en échec :")
        for name in results["failed"]:
            logger.warning(f"   • {name}")

    total_mb = sum(f.stat().st_size for f in results["success"]) / (1024 * 1024)
    logger.info(f"\n📊 CSV générés : {total_mb:.1f} Mo")
    logger.info(f"📁 Sortie : {OUTPUT_DIR}")

    # Aperçu d'un CSV
    if results["success"]:
        logger.info(f"\n📋 Aperçu des 3 premières lignes de {results['success'][0].name} :")
        with open(results["success"][0], "r") as f:
            for i, line in enumerate(f):
                if i >= 4:
                    break
                logger.info(f"   {line.rstrip()}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompu par l'utilisateur")
        sys.exit(1)
