"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Inférence GraphCast Operational sur CPU Mac
FICHIER  : scripts/graphcast_gfs/inference_graphcast.py
RÔLE     : Lance GraphCast Operational 13 niveaux sur chaque NetCDF GDAS
           et produit 8 fichiers de prédictions J+1 (4 horizons).
═══════════════════════════════════════════════════════════════════════════

PIPELINE COMPLET
----------------
Pour chaque fichier gdas_YYYYMMDD_00.nc (8 fichiers) :

  1. Charger le dataset GDAS (2 timestamps : T-6h, T0)
  2. Télécharger les statiques DeepMind si pas en cache
  3. Ajouter geopotential_at_surface + land_sea_mask au dataset
  4. Étendre à 6 timestamps (2 inputs + 4 targets = +6h, +12h, +18h, +24h)
  5. Ajouter coord 'datetime' en 2D (batch, time)
  6. Calculer TOA astronomiquement (via solar_utils.py)
  7. Ajouter year_progress, day_progress via data_utils.add_derived_vars()
  8. Extraire inputs/targets/forcings avec target_lead_times=slice("6h","24h")
  9. Lancer inférence GraphCast Operational
  10. Extraire zone France
  11. Sauvegarder en NetCDF

SORTIE
------
data/graphcast_predictions/
├── graphcast_20260416_00h.nc
├── graphcast_20260417_00h.nc
└── ... (8 fichiers)

USAGE
-----
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts
    python -m graphcast_gfs.inference_graphcast

TEMPS ESTIMÉ SUR CPU MAC
------------------------
- 1re inférence : 5-8 min (compilation JIT)
- Inférences suivantes : 1-2 min chacune
- Total 8 runs : ~15-25 min
═══════════════════════════════════════════════════════════════════════════
"""

# ───────────────────────────────────────────────────────────────────────────
# Suppression des warnings bénins et forçage CPU
# (DOIT être avant l'import de jax, xarray, graphcast)
# ───────────────────────────────────────────────────────────────────────────
import os
os.environ["JAX_PLATFORMS"] = "cpu"             # force CPU, évite recherche TPU
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"        # masque les logs TensorFlow
os.environ["GRPC_VERBOSITY"] = "ERROR"           # masque les logs gRPC

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message="Skipping gradient checkpointing")
warnings.filterwarnings("ignore", message=".*Dataset.dims.*")
warnings.filterwarnings("ignore", message=".*xarray.concat.*")

import logging
# Masquer aussi les logs absl (utilisé par JAX)
logging.getLogger("absl").setLevel(logging.ERROR)
logging.getLogger("jax").setLevel(logging.ERROR)

import dataclasses
import functools
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import xarray as xr
import jax
import haiku as hk
import gcsfs

from graphcast import (
    autoregressive,
    casting,
    checkpoint,
    data_utils,
    graphcast,
    normalization,
    rollout,
)


# Import solar_utils depuis le parent package
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
INPUT_DIR = BASE_DIR / "data" / "gdas_ready"
OUTPUT_DIR = BASE_DIR / "data" / "graphcast_predictions"
CACHE_DIR = BASE_DIR / "data" / ".graphcast_cache"

GCS_BUCKET = "dm_graphcast"
GRAPHCAST_PARAMS_FILE = (
    "GraphCast_operational - ERA5-HRES 1979-2021 - resolution 0.25 - "
    "pressure levels 13 - mesh 2to6 - precipitation output only.npz"
)

AREA_FRANCE = [52, -6, 41, 10]  # [Nord, Ouest, Sud, Est]


# ───────────────────────────────────────────────────────────────────────────
# CHARGEMENT DU MODÈLE
# ───────────────────────────────────────────────────────────────────────────

def download_from_gcs(gcs_path: str, local_path: Path):
    """Télécharge un fichier du bucket GCS s'il n'est pas en cache."""
    if local_path.exists():
        return local_path

    logger.info(f"  📥 Téléchargement {gcs_path} ...")
    local_path.parent.mkdir(parents=True, exist_ok=True)

    gcs = gcsfs.GCSFileSystem(token="anon")
    with gcs.open(gcs_path, "rb") as src:
        with open(local_path, "wb") as dst:
            dst.write(src.read())

    size_mb = local_path.stat().st_size / (1024 * 1024)
    logger.info(f"     ✅ {local_path.name} ({size_mb:.1f} Mo)")
    return local_path


def load_graphcast_model():
    """Charge GraphCast Operational 13 niveaux + stats + statiques."""
    logger.info("=" * 70)
    logger.info("📦 CHARGEMENT GRAPHCAST OPERATIONAL 13 NIVEAUX")
    logger.info("=" * 70)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    params_local = CACHE_DIR / "graphcast_operational_params.npz"
    download_from_gcs(f"{GCS_BUCKET}/params/{GRAPHCAST_PARAMS_FILE}", params_local)

    logger.info("\n📖 Lecture des poids...")
    with open(params_local, "rb") as f:
        ckpt = checkpoint.load(f, graphcast.CheckPoint)

    params = ckpt.params
    state = {}
    model_config = ckpt.model_config
    task_config = ckpt.task_config

    logger.info(f"  ✅ Pressure levels : {task_config.pressure_levels}")

    stats_files = {
        "diffs_stddev_by_level": "stats/diffs_stddev_by_level.nc",
        "mean_by_level": "stats/mean_by_level.nc",
        "stddev_by_level": "stats/stddev_by_level.nc",
    }
    stats = {}
    logger.info("\n📊 Chargement stats de normalisation...")
    for key, rel_path in stats_files.items():
        local = CACHE_DIR / Path(rel_path).name
        download_from_gcs(f"{GCS_BUCKET}/{rel_path}", local)
        stats[key] = xr.load_dataset(local).compute()

    logger.info("  ✅ 3 stats chargées")

    logger.info("\n🗺️  Chargement statiques...")
    REF_PATH = "dm_graphcast/dataset/source-era5_date-2022-01-01_res-0.25_levels-37_steps-01.nc"
    ref_local = CACHE_DIR / "reference_statics.nc"
    download_from_gcs(REF_PATH, ref_local)

    reference = xr.open_dataset(ref_local, decode_timedelta=True).compute()
    static_vars_global = reference[["geopotential_at_surface", "land_sea_mask"]]

    if static_vars_global.lon.max() > 180:
        static_vars_global = static_vars_global.assign_coords(
            lon=(((static_vars_global.lon + 180) % 360) - 180)
        ).sortby("lon")

    logger.info(f"  ✅ Statiques globales : {dict(static_vars_global.sizes)}")

    return params, state, model_config, task_config, stats, static_vars_global


def build_jit_functions(params, state, model_config, task_config, stats):
    """Construit run_forward_jitted."""

    def construct_wrapped_graphcast(model_config, task_config):
        predictor = graphcast.GraphCast(model_config, task_config)
        predictor = casting.Bfloat16Cast(predictor)
        predictor = normalization.InputsAndResiduals(
            predictor,
            diffs_stddev_by_level=stats["diffs_stddev_by_level"],
            mean_by_level=stats["mean_by_level"],
            stddev_by_level=stats["stddev_by_level"],
        )
        predictor = autoregressive.Predictor(predictor, gradient_checkpointing=True)
        return predictor

    @hk.transform_with_state
    def run_forward(model_config, task_config, inputs, targets_template, forcings):
        predictor = construct_wrapped_graphcast(model_config, task_config)
        return predictor(inputs, targets_template=targets_template, forcings=forcings)

    def with_configs(fn):
        return functools.partial(fn, model_config=model_config, task_config=task_config)

    def with_params(fn):
        return functools.partial(fn, params=params, state=state)

    def drop_state(fn):
        return lambda **kw: fn(**kw)[0]

    run_forward_jitted = drop_state(
        with_params(jax.jit(with_configs(run_forward.apply)))
    )
    return run_forward_jitted


# ───────────────────────────────────────────────────────────────────────────
# PRÉPARATION D'UN RUN
# ───────────────────────────────────────────────────────────────────────────

def prepare_dataset_for_inference(
    gdas_path: Path,
    run_datetime: datetime,
    static_vars_global: xr.Dataset,
) -> xr.Dataset:
    """Transforme un NetCDF GDAS en dataset prêt pour GraphCast."""
    ds = xr.open_dataset(gdas_path)

    # Interpolation statiques sur grille France
    static_france = static_vars_global.sel(
        lat=slice(ds.lat.min().item(), ds.lat.max().item()),
        lon=slice(ds.lon.min().item(), ds.lon.max().item()),
    ).interp(lat=ds.lat, lon=ds.lon, method="linear")

    ds = xr.merge([ds, static_france], compat="override")

    for var in ["geopotential_at_surface", "land_sea_mask"]:
        if var in ds.data_vars and "batch" in ds[var].dims:
            ds[var] = ds[var].squeeze("batch", drop=True)

    # Étendre à 6 timestamps
    t_minus_6h = run_datetime - timedelta(hours=6)
    timestamps = [
        t_minus_6h,
        run_datetime,
        run_datetime + timedelta(hours=6),
        run_datetime + timedelta(hours=12),
        run_datetime + timedelta(hours=18),
        run_datetime + timedelta(hours=24),
    ]
    times_np = np.array([np.datetime64(t) for t in timestamps])

    ds_extended = ds.reindex(time=times_np, fill_value=np.nan)

    # Coord datetime en 2D
    datetime_2d = xr.DataArray(
        data=times_np[np.newaxis, :],
        dims=("batch", "time"),
    )
    ds_extended = ds_extended.assign_coords(datetime=datetime_2d)

    # Calculer TOA pour les 6 timestamps
    lats = ds_extended.lat.values
    lons = ds_extended.lon.values
    toa_6_timestamps = np.zeros((1, 6, len(lats), len(lons)), dtype=np.float32)

    for t_idx, ts in enumerate(timestamps):
        ts_utc = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
        toa_grid = calculate_toa_grid_fast(ts_utc, lats, lons)
        toa_6_timestamps[0, t_idx, :, :] = toa_grid

    ds_extended["toa_incident_solar_radiation"] = (
        ("batch", "time", "lat", "lon"),
        toa_6_timestamps,
    )

    # ═══ FIX : Ajouter total_precipitation_6hr rempli de zéros ═══
    # GraphCast Operational a cette variable en TARGET (pas en input).
    # GDAS ne la fournit pas, mais extract_inputs_targets_forcings() la cherche
    # dans le dataset pour construire la template de targets.
    # On l'ajoute avec des zéros, GraphCast prédira les vraies valeurs.
    tp_6hr_zeros = np.zeros(
        (1, 6, len(lats), len(lons)), dtype=np.float32
    )
    ds_extended["total_precipitation_6hr"] = (
        ("batch", "time", "lat", "lon"),
        tp_6hr_zeros,
    )

    # Ajouter year/day progress (in-place)
    data_utils.add_derived_vars(ds_extended)

    return ds_extended


def run_inference_single_date(
    gdas_path: Path,
    run_datetime: datetime,
    run_forward_jitted,
    task_config,
    static_vars_global: xr.Dataset,
    output_dir: Path,
) -> Path:
    """Prépare + inférence + sauvegarde pour 1 run."""
    import threading

    logger.info(f"\n🔧 Préparation dataset...")
    t_prep = time.time()
    ds_ready = prepare_dataset_for_inference(gdas_path, run_datetime, static_vars_global)
    logger.info(f"   ⏱️  Préparation : {time.time() - t_prep:.1f}s")

    logger.info(f"🔧 Extraction inputs/targets/forcings...")
    t_extract = time.time()
    eval_inputs, eval_targets, eval_forcings = data_utils.extract_inputs_targets_forcings(
        ds_ready,
        target_lead_times=slice("6h", "24h"),
        **dataclasses.asdict(task_config),
    )
    logger.info(f"   ⏱️  Extraction : {time.time() - t_extract:.1f}s")
    logger.info(f"   📊 Inputs shape    : {dict(eval_inputs.sizes)}")
    logger.info(f"   📊 Targets shape   : {dict(eval_targets.sizes)}")
    logger.info(f"   📊 Forcings shape  : {dict(eval_forcings.sizes)}")

    # ═══ HEARTBEAT — affiche un message toutes les 3 minutes ═══
    stop_heartbeat = threading.Event()

    def heartbeat():
        t0 = time.time()
        dots = 0
        while not stop_heartbeat.is_set():
            elapsed = time.time() - t0
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            spinner = "⏳" if dots % 2 == 0 else "🔄"
            status_msg = (
                f"   {spinner} Inférence en cours... "
                f"({minutes}m{seconds:02d}s écoulées) "
                f"{'🧠 compilation JIT' if elapsed < 300 else '⚡ inférence'}"
            )
            logger.info(status_msg)
            dots += 1
            # Attendre 3 minutes ou jusqu'à ce que le stop soit déclenché
            stop_heartbeat.wait(timeout=180)

    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)

    logger.info(f"🤖 Inférence GraphCast (4 horizons)...")
    logger.info(f"   ℹ️  1ère inférence = compilation JIT (~5-8 min), les suivantes seront rapides")
    heartbeat_thread.start()

    try:
        t_inference = time.time()
        predictions = rollout.chunked_prediction(
            run_forward_jitted,
            rng=jax.random.PRNGKey(0),
            inputs=eval_inputs,
            targets_template=eval_targets * np.nan,
            forcings=eval_forcings,
        )
        inference_time = time.time() - t_inference
    finally:
        # Arrêter le heartbeat
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=2)

    logger.info(f"   ✅ Inférence terminée en {inference_time:.1f}s")

    # Extraction France
    logger.info(f"🗺️  Extraction zone France...")
    predictions_france = predictions.sel(
        lat=slice(AREA_FRANCE[2], AREA_FRANCE[0]),
        lon=slice(AREA_FRANCE[1], AREA_FRANCE[3]),
    )

    date_str = run_datetime.strftime("%Y%m%d")
    hour_str = run_datetime.strftime("%H")
    output_path = output_dir / f"graphcast_{date_str}_{hour_str}h.nc"
    predictions_france.to_netcdf(output_path)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"✅ {output_path.name} ({size_mb:.1f} Mo)")
    return output_path


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 70)
    logger.info("🚀 INFÉRENCE GRAPHCAST OPERATIONAL — 8 RUNS CPU")
    logger.info("=" * 70)
    logger.info(f"   Entrée : {INPUT_DIR}")
    logger.info(f"   Sortie : {OUTPUT_DIR}")
    logger.info(f"   Cache  : {CACHE_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    gdas_files = sorted(INPUT_DIR.glob("gdas_*.nc"))
    if not gdas_files:
        logger.error("❌ Aucun fichier gdas_*.nc trouvé")
        sys.exit(1)

    logger.info(f"\n📅 Runs à traiter : {len(gdas_files)}")
    for f in gdas_files:
        logger.info(f"   • {f.name}")

    t_start = time.time()
    (
        params,
        state,
        model_config,
        task_config,
        stats,
        static_vars_global,
    ) = load_graphcast_model()

    logger.info("\n🔧 Construction JIT...")
    run_forward_jitted = build_jit_functions(
        params, state, model_config, task_config, stats
    )
    logger.info("   ✅ JIT construit (compilation à la 1ère inférence)")

    results = {"success": [], "failed": []}

    for i, gdas_path in enumerate(gdas_files, 1):
        name = gdas_path.stem
        parts = name.split("_")
        date_str = parts[1]
        hour_str = parts[2]

        try:
            run_dt = datetime.strptime(date_str, "%Y%m%d").replace(hour=int(hour_str))
        except ValueError:
            logger.error(f"❌ Format nom inattendu : {name}")
            continue

        logger.info(f"\n{'=' * 70}")
        logger.info(f"[{i}/{len(gdas_files)}] {run_dt.strftime('%A %d %B %Y')} 00h UTC")
        logger.info(f"{'=' * 70}")
        t_run = time.time()

        try:
            output_path = run_inference_single_date(
                gdas_path, run_dt, run_forward_jitted, task_config,
                static_vars_global, OUTPUT_DIR,
            )
            elapsed = time.time() - t_run
            logger.info(f"   ⏱️  Temps : {elapsed:.1f}s")
            results["success"].append(output_path)
        except Exception as e:
            logger.error(f"   ❌ Erreur : {e}")
            import traceback
            logger.error(traceback.format_exc())
            results["failed"].append(gdas_path.name)

    elapsed_min = (time.time() - t_start) / 60
    logger.info(f"\n{'=' * 70}")
    logger.info(f"✅ INFÉRENCE TERMINÉE en {elapsed_min:.1f} min")
    logger.info(f"{'=' * 70}")
    logger.info(f"   Succès : {len(results['success'])}/{len(gdas_files)}")
    logger.info(f"   Échecs : {len(results['failed'])}/{len(gdas_files)}")

    if results["failed"]:
        logger.warning("\n⚠️ Runs en échec :")
        for name in results["failed"]:
            logger.warning(f"   • {name}")

    total_mb = sum(f.stat().st_size for f in results["success"]) / (1024 * 1024)
    logger.info(f"\n📊 Prédictions : {total_mb:.1f} Mo")
    logger.info(f"📁 Sortie : {OUTPUT_DIR}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompu par l'utilisateur")
        sys.exit(1)
