"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Export CSV ERA5 (vérité terrain) pour DB
FICHIER  : scripts/era5/export_era5_csv.py
RÔLE     : Lit les NetCDF ERA5 (J + J-1 pour le cumul tp) et génère un
           CSV au format DB avec les 8 variables harmonisées avec GraphCast.
═══════════════════════════════════════════════════════════════════════════

ENTRÉES (.nc dans data/era5_raw/)
---------------------------------
  - era5_YYYYMMDD_full.nc      : jour J, 24h horaires, 5 variables
  - era5_(YYYYMMDD-1)_tp_only.nc : jour J-1, 24h horaires, tp uniquement
                                   (utile pour cumul tp_6h à 00h du J)

SORTIE (CSV dans data/era5_csv/)
--------------------------------
  era5_YYYYMMDD.csv : 4 timestamps × 8 variables × 45 lat × 65 lon
                    = 93 600 lignes au format LONG

VARIABLES DU CSV (8 total)
--------------------------
  Directes (5, prises depuis le .nc) :
    - t2m_celsius          (depuis 2m_temperature en K → °C)
    - u10_ms               (depuis 10m_u_component_of_wind)
    - v10_ms               (depuis 10m_v_component_of_wind)
    - msl_hpa              (depuis mean_sea_level_pressure en Pa → hPa)
    - tp_6h_mm             (cumul 6h calculé depuis tp horaire en m → mm)

  Dérivées (3, calculées) :
    - wind_speed_10m_ms    = sqrt(u10² + v10²)
    - wind_direction_10m_deg = atan2(-u10, -v10) en degrés (convention météo)
    - toa_wm2              = calcul astronomique via solar_utils.py

LOGIQUE DU CUMUL tp_6h_mm
-------------------------
ERA5 fournit total_precipitation HORAIRE (= cumul de 1h entre H-1 et H).
Pour matcher GraphCast (qui prédit cumul 6h se terminant au timestamp),
on somme les 6 valeurs horaires se terminant au timestamp :

  À 00h UTC du J : tp(19h_J-1) + tp(20h_J-1) + tp(21h_J-1) + tp(22h_J-1) + tp(23h_J-1) + tp(00h_J)
  À 06h UTC du J : tp(01h_J) + tp(02h_J) + tp(03h_J) + tp(04h_J) + tp(05h_J) + tp(06h_J)
  À 12h UTC du J : tp(07h_J) + tp(08h_J) + tp(09h_J) + tp(10h_J) + tp(11h_J) + tp(12h_J)
  À 18h UTC du J : tp(13h_J) + tp(14h_J) + tp(15h_J) + tp(16h_J) + tp(17h_J) + tp(18h_J)

USAGE
-----
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts

    # Pour 1 jour spécifique
    python -m era5.export_era5_csv --date 2026-04-17

TEMPS ESTIMÉ : ~5 secondes par jour
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
# CONSTANTES
# ───────────────────────────────────────────────────────────────────────────

BASE_DIR = Path.home() / "Desktop" / "PROJETS" / "Dev_meteo" / "meteo_ia_france"
INPUT_DIR = BASE_DIR / "data" / "era5_raw"
OUTPUT_DIR = BASE_DIR / "data" / "era5_csv"

# Header du CSV (cohérent avec la table era5_truth)
CSV_HEADER = [
    "timestamp_utc",
    "lat",
    "lon",
    "variable_name",
    "value",
    "unit",
]

# Les 4 timestamps qu'on garde dans le CSV
TARGET_HOURS = [0, 6, 12, 18]


# ───────────────────────────────────────────────────────────────────────────
# DÉTECTION DES NOMS DE VARIABLES (varient selon version CDS)
# ───────────────────────────────────────────────────────────────────────────

# Mapping nom-canonique → liste de noms possibles dans le NetCDF ERA5
VAR_NAME_CANDIDATES = {
    "t2m": ["t2m", "2m_temperature"],
    "u10": ["u10", "10m_u_component_of_wind"],
    "v10": ["v10", "10m_v_component_of_wind"],
    "msl": ["msl", "mean_sea_level_pressure"],
    "tp":  ["tp",  "total_precipitation"],
}


def find_variable(ds: xr.Dataset, canonical_name: str) -> str:
    """Trouve le nom réel de la variable dans le dataset selon les candidats."""
    candidates = VAR_NAME_CANDIDATES.get(canonical_name, [canonical_name])
    for cand in candidates:
        if cand in ds.data_vars:
            return cand
    raise KeyError(f"Variable '{canonical_name}' introuvable. Candidats: {candidates}, Dispo: {list(ds.data_vars)}")


def find_time_dim(ds: xr.Dataset) -> str:
    """Trouve le nom de la dimension temporelle (varie selon version)."""
    for cand in ["valid_time", "time"]:
        if cand in ds.coords:
            return cand
    raise KeyError(f"Aucune dimension temporelle trouvée dans {list(ds.coords)}")


# ───────────────────────────────────────────────────────────────────────────
# CALCUL DU CUMUL tp_6h
# ───────────────────────────────────────────────────────────────────────────

def compute_tp_6h_for_target_hours(
    ds_curr: xr.Dataset,
    ds_prev: xr.Dataset,
    target_date: datetime,
) -> dict:
    """
    Calcule les 4 cumuls tp_6h (à 00h, 06h, 12h, 18h du jour J).

    Retourne un dict {timestamp_utc: array(lat, lon)} avec les cumuls en mm.

    Args:
        ds_curr: dataset du jour J (24h horaires, contient au moins 'tp')
        ds_prev: dataset du jour J-1 (24h horaires, contient au moins 'tp')
        target_date: jour J
    """
    tp_var_curr = find_variable(ds_curr, "tp")
    tp_var_prev = find_variable(ds_prev, "tp")
    time_dim_curr = find_time_dim(ds_curr)
    time_dim_prev = find_time_dim(ds_prev)

    logger.info(f"   🔧 Calcul cumuls tp_6h pour les 4 timestamps :")

    cumuls = {}

    for target_hour in TARGET_HOURS:
        target_ts = target_date.replace(hour=target_hour, minute=0, second=0, tzinfo=None)

        if target_hour == 0:
            # Cumul à 00h du J = somme des heures (19h, 20h, 21h, 22h, 23h) du J-1 + 00h du J
            prev_hours_needed = [19, 20, 21, 22, 23]
            curr_hours_needed = [0]

            try:
                tp_prev_values = []
                for h in prev_hours_needed:
                    ts = (target_date - timedelta(days=1)).replace(hour=h, minute=0, second=0, tzinfo=None)
                    val = ds_prev[tp_var_prev].sel({time_dim_prev: ts.strftime("%Y-%m-%dT%H:%M:%S")}).values
                    tp_prev_values.append(val)

                tp_curr_value = ds_curr[tp_var_curr].sel(
                    {time_dim_curr: target_ts.strftime("%Y-%m-%dT%H:%M:%S")}
                ).values

                # Somme des 6 valeurs (5 du J-1 + 1 du J)
                cumul = np.sum(tp_prev_values, axis=0) + tp_curr_value

            except KeyError as e:
                logger.warning(f"      ⚠️  Heure manquante pour cumul à {target_hour:02d}h : {e}")
                continue

        else:
            # Cumul à 06h, 12h, 18h du J = somme des 6h précédentes (toutes dans le J)
            curr_hours_needed = [target_hour - 5, target_hour - 4, target_hour - 3,
                                 target_hour - 2, target_hour - 1, target_hour]

            try:
                tp_values = []
                for h in curr_hours_needed:
                    ts = target_date.replace(hour=h, minute=0, second=0, tzinfo=None)
                    val = ds_curr[tp_var_curr].sel({time_dim_curr: ts.strftime("%Y-%m-%dT%H:%M:%S")}).values
                    tp_values.append(val)

                cumul = np.sum(tp_values, axis=0)

            except KeyError as e:
                logger.warning(f"      ⚠️  Heure manquante pour cumul à {target_hour:02d}h : {e}")
                continue

        # Conversion m → mm + clip à 0 (pas de pluie négative)
        cumul_mm = np.maximum(cumul * 1000.0, 0.0).astype(np.float32)

        cumuls[target_hour] = cumul_mm
        logger.info(f"      ✅ Cumul à {target_hour:02d}h : min={cumul_mm.min():.3f}mm, max={cumul_mm.max():.3f}mm, moy={cumul_mm.mean():.3f}mm")

    return cumuls


# ───────────────────────────────────────────────────────────────────────────
# EXTRACTION DES VARIABLES DIRECTES POUR LES 4 TIMESTAMPS
# ───────────────────────────────────────────────────────────────────────────

def extract_direct_variables(ds_curr: xr.Dataset, target_date: datetime) -> dict:
    """
    Extrait t2m, u10, v10, msl pour les 4 timestamps cibles (00h, 06h, 12h, 18h).

    Retourne un dict {(target_hour, var_canonical): array(lat, lon)}.
    """
    time_dim = find_time_dim(ds_curr)

    t2m_var = find_variable(ds_curr, "t2m")
    u10_var = find_variable(ds_curr, "u10")
    v10_var = find_variable(ds_curr, "v10")
    msl_var = find_variable(ds_curr, "msl")

    logger.info(f"   🔧 Extraction des variables directes pour les 4 timestamps :")

    extracted = {}

    for target_hour in TARGET_HOURS:
        target_ts = target_date.replace(hour=target_hour, minute=0, second=0, tzinfo=None)
        ts_str = target_ts.strftime("%Y-%m-%dT%H:%M:%S")

        try:
            ds_t = ds_curr.sel({time_dim: ts_str})

            # t2m : K → °C
            t2m_c = (ds_t[t2m_var].values - 273.15).astype(np.float32)
            extracted[(target_hour, "t2m_celsius")] = (t2m_c, "°C")

            # u10, v10 : m/s
            u10 = ds_t[u10_var].values.astype(np.float32)
            v10 = ds_t[v10_var].values.astype(np.float32)
            extracted[(target_hour, "u10_ms")] = (u10, "m/s")
            extracted[(target_hour, "v10_ms")] = (v10, "m/s")

            # msl : Pa → hPa
            msl_hpa = (ds_t[msl_var].values / 100.0).astype(np.float32)
            extracted[(target_hour, "msl_hpa")] = (msl_hpa, "hPa")

            logger.info(f"      ✅ {target_hour:02d}h extrait")

        except KeyError as e:
            logger.warning(f"      ⚠️  Heure {target_hour:02d}h manquante : {e}")

    return extracted


# ───────────────────────────────────────────────────────────────────────────
# CALCUL DES VARIABLES DÉRIVÉES (wind_speed, wind_direction, toa)
# ───────────────────────────────────────────────────────────────────────────

def compute_derived_variables(extracted: dict, target_date: datetime, lats: np.ndarray, lons: np.ndarray) -> dict:
    """
    Calcule les variables dérivées (wind_speed, wind_direction, toa)
    pour chaque target_hour disponible.
    """
    logger.info(f"   🔧 Calcul des variables dérivées (wind_speed, wind_direction, toa) :")

    derived = {}

    for target_hour in TARGET_HOURS:
        # On a besoin de u10 et v10 pour wind_speed et wind_direction
        u10_key = (target_hour, "u10_ms")
        v10_key = (target_hour, "v10_ms")

        if u10_key not in extracted or v10_key not in extracted:
            continue  # heure manquante

        u10, _ = extracted[u10_key]
        v10, _ = extracted[v10_key]

        # Vitesse du vent
        wind_speed = np.sqrt(u10**2 + v10**2).astype(np.float32)
        derived[(target_hour, "wind_speed_10m_ms")] = (wind_speed, "m/s")

        # Direction du vent (convention météo : d'où vient le vent)
        wind_direction = np.rad2deg(np.arctan2(-u10, -v10)).astype(np.float32)
        wind_direction = (wind_direction + 360.0) % 360.0
        derived[(target_hour, "wind_direction_10m_deg")] = (wind_direction, "°")

        # TOA astronomique
        target_ts = target_date.replace(hour=target_hour, minute=0, second=0, tzinfo=timezone.utc)
        toa_grid = calculate_toa_grid_fast(target_ts, lats, lons).astype(np.float32)
        derived[(target_hour, "toa_wm2")] = (toa_grid, "W/m²")

        logger.info(f"      ✅ {target_hour:02d}h : wind_speed, wind_direction, toa")

    return derived


# ───────────────────────────────────────────────────────────────────────────
# ÉCRITURE DU CSV
# ───────────────────────────────────────────────────────────────────────────

def write_csv(
    output_path: Path,
    target_date: datetime,
    lats: np.ndarray,
    lons: np.ndarray,
    extracted_direct: dict,
    derived_vars: dict,
    cumuls_tp: dict,
):
    """
    Écrit le CSV final au format LONG.

    Format : timestamp_utc,lat,lon,variable_name,value,unit
    """
    logger.info(f"   📝 Écriture CSV...")
    t0 = time.time()
    n_rows = 0

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(CSV_HEADER)

        # Pour chaque target_hour, on écrit toutes les variables
        for target_hour in TARGET_HOURS:
            target_ts = target_date.replace(hour=target_hour, minute=0, second=0, tzinfo=timezone.utc)
            ts_iso = target_ts.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Collecter toutes les variables disponibles pour ce timestamp
            vars_for_this_hour = {}

            # Variables directes (t2m, u10, v10, msl)
            for var_name in ["t2m_celsius", "u10_ms", "v10_ms", "msl_hpa"]:
                key = (target_hour, var_name)
                if key in extracted_direct:
                    vars_for_this_hour[var_name] = extracted_direct[key]

            # Variables dérivées (wind_speed, wind_direction, toa)
            for var_name in ["wind_speed_10m_ms", "wind_direction_10m_deg", "toa_wm2"]:
                key = (target_hour, var_name)
                if key in derived_vars:
                    vars_for_this_hour[var_name] = derived_vars[key]

            # Cumul tp_6h
            if target_hour in cumuls_tp:
                vars_for_this_hour["tp_6h_mm"] = (cumuls_tp[target_hour], "mm")

            if not vars_for_this_hour:
                logger.warning(f"      ⚠️  Aucune variable disponible pour {target_hour:02d}h, skip")
                continue

            # Écriture par lat × lon × variable
            for lat_idx, lat in enumerate(lats):
                for lon_idx, lon in enumerate(lons):
                    for var_name, (values_array, unit) in vars_for_this_hour.items():
                        value = float(values_array[lat_idx, lon_idx])
                        if np.isnan(value):
                            continue
                        writer.writerow([
                            ts_iso,
                            f"{float(lat):.4f}",
                            f"{float(lon):.4f}",
                            var_name,
                            f"{value:.4f}",
                            unit,
                        ])
                        n_rows += 1

    elapsed = time.time() - t0
    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ {output_path.name} ({n_rows:,} lignes, {size_mb:.1f} Mo, {elapsed:.1f}s)")
    return n_rows


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def export_era5_for_date(target_date: datetime) -> Path:
    """
    Génère le CSV ERA5 pour 1 jour cible.

    Lit :
      - era5_YYYYMMDD_full.nc      (jour J, toutes vars)
      - era5_(YYYYMMDD-1)_tp_only.nc (jour J-1, tp uniquement)

    Écrit :
      - era5_YYYYMMDD.csv
    """
    target_str = target_date.strftime("%Y%m%d")
    prev_str = (target_date - timedelta(days=1)).strftime("%Y%m%d")

    full_path = INPUT_DIR / f"era5_{target_str}_full.nc"
    tp_prev_path = INPUT_DIR / f"era5_{prev_str}_tp_only.nc"

    if not full_path.exists():
        raise FileNotFoundError(f"Fichier manquant : {full_path}")
    if not tp_prev_path.exists():
        raise FileNotFoundError(f"Fichier manquant : {tp_prev_path}")

    logger.info(f"\n📂 Lecture des NetCDF :")
    logger.info(f"   • {full_path.name}")
    logger.info(f"   • {tp_prev_path.name}")

    ds_curr = xr.open_dataset(full_path)
    ds_prev = xr.open_dataset(tp_prev_path)

    # Coordonnées spatiales
    lats = ds_curr.latitude.values if "latitude" in ds_curr.coords else ds_curr.lat.values
    lons = ds_curr.longitude.values if "longitude" in ds_curr.coords else ds_curr.lon.values
    logger.info(f"   📊 Grille : {len(lats)} lat × {len(lons)} lon")

    # Calculs
    cumuls_tp = compute_tp_6h_for_target_hours(ds_curr, ds_prev, target_date)
    extracted_direct = extract_direct_variables(ds_curr, target_date)
    derived_vars = compute_derived_variables(extracted_direct, target_date, lats, lons)

    # Écriture du CSV
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"era5_{target_str}.csv"
    n_rows = write_csv(
        output_path, target_date, lats, lons,
        extracted_direct, derived_vars, cumuls_tp,
    )

    # Cleanup
    ds_curr.close()
    ds_prev.close()

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Export CSV ERA5 (vérité terrain) pour DB",
    )
    parser.add_argument(
        "--date", type=str, required=True,
        help="Date cible au format YYYY-MM-DD (ex: 2026-04-17)",
    )
    args = parser.parse_args()

    try:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        logger.error(f"❌ Format de date invalide : {args.date} (attendu YYYY-MM-DD)")
        sys.exit(1)

    # Banner
    logger.info("╔" + "═" * 68 + "╗")
    msg = f"📊 EXPORT CSV ERA5 — {target_date.strftime('%Y-%m-%d')}"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")

    t_start = time.time()

    try:
        csv_path = export_era5_for_date(target_date)

        elapsed = time.time() - t_start
        logger.info("\n" + "╔" + "═" * 68 + "╗")
        msg = f"✅ EXPORT CSV ERA5 OK en {elapsed:.1f}s"
        logger.info(f"║  {msg:<66s}║")
        logger.info("╚" + "═" * 68 + "╝")
        logger.info(f"\n📁 Fichier produit : {csv_path}")
        sys.exit(0)

    except Exception as e:
        elapsed = time.time() - t_start
        logger.error(f"\n❌ ÉCHEC après {elapsed:.1f}s : {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
