"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Calcul des métriques MAE/RMSE/Bias
FICHIER  : scripts/mae/compute_mae.py
RÔLE     : Calcule les métriques de performance des modèles de prévision
           (GraphCast et AROME) contre la vérité terrain ERA5.
═══════════════════════════════════════════════════════════════════════════

COMPARAISONS CALCULÉES
----------------------
1. graphcast_vs_era5 : performance de GraphCast (prédit) vs ERA5 (vérité)
2. arome_vs_era5     : performance d'AROME (prédit) vs ERA5 (vérité)

MÉTRIQUES PAR (comparaison × date × variable × horizon)
--------------------------------------------------------
- MAE   : Mean Absolute Error    = AVG(|prédit - vrai|)
- RMSE  : Root Mean Square Error = SQRT(AVG((prédit - vrai)²))
- Bias  : Mean Error (signé)     = AVG(prédit - vrai)
          → positif = modèle SURESTIME
          → négatif = modèle SOUSESTIME
- Sample count : nombre de points utilisés pour le calcul

LOGIQUE D'AGRÉGATION
--------------------
Pour 1 jour évalué :
  - Chaque variable a 4 horizons (6h, 12h, 18h, 24h)
  - Chaque horizon a 2925 points de grille (45 lat × 65 lon)
  - Le MAE est calculé sur les 2925 points
  - On utilise la prédiction la PLUS RÉCENTE pour chaque timestamp
    (via les vues graphcast_predictions_fresh et arome_forecasts_fresh)

USAGE
-----
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts

    # Calculer pour 1 date spécifique
    python -m mae.compute_mae --date 2026-04-17

    # Calculer pour une plage de dates
    python -m mae.compute_mae --start-date 2026-04-17 --end-date 2026-04-18

    # Mode dry-run (calcule mais n'insère pas)
    python -m mae.compute_mae --date 2026-04-17 --dry-run

    # Skip une comparaison
    python -m mae.compute_mae --date 2026-04-17 --skip-arome
    python -m mae.compute_mae --date 2026-04-17 --skip-graphcast

TEMPS ESTIMÉ : ~5-10 sec par date évaluée
═══════════════════════════════════════════════════════════════════════════
"""

import argparse
import logging
import sys
import time
import warnings
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Optional

# Suppression du warning pandas/SQLAlchemy bénin
warnings.filterwarnings("ignore", message=".*SQLAlchemy.*")

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db_connection import get_db_connection


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ───────────────────────────────────────────────────────────────────────────

# Configuration des 2 comparaisons
COMPARISONS = {
    "graphcast_vs_era5": {
        "predict_view": "graphcast_predictions_fresh",  # vue avec prédiction la plus récente
        "truth_table": "era5_truth",
        "label": "GraphCast vs ERA5",
    },
    "arome_vs_era5": {
        "predict_view": "arome_forecasts_fresh",
        "truth_table": "era5_truth",
        "label": "AROME vs ERA5",
    },
}

# Variables et horizons attendus
VARIABLES = [
    "t2m_celsius",
    "u10_ms",
    "v10_ms",
    "msl_hpa",
    "tp_6h_mm",
    "wind_speed_10m_ms",
    "wind_direction_10m_deg",
    "toa_wm2",
]

HORIZONS = [6, 12, 18, 24]

# Variables cycliques : MAE/RMSE doivent utiliser la formule cyclique
# pour éviter l'erreur 350° entre 5° et 355° (réelle: 10°).
# Le bias n'a pas de sens cyclique simple → on le force à None pour ces variables.
CYCLIC_VARIABLES = {
    "wind_direction_10m_deg": 360.0,  # période en degrés
}


# ───────────────────────────────────────────────────────────────────────────
# CHARGEMENT DES DONNÉES DEPUIS LA DB
# ───────────────────────────────────────────────────────────────────────────

def load_predictions_for_date(conn, predict_view: str, evaluation_date: date) -> pd.DataFrame:
    """
    Charge les prédictions pour les 4 timestamps d'une date.

    Returns:
        DataFrame avec colonnes : timestamp, variable_name, forecast_horizon_h,
                                   latitude, longitude, value
    """
    query = f"""
        SELECT
            timestamp,
            variable_name,
            forecast_horizon_h,
            latitude,
            longitude,
            value
        FROM {predict_view}
        WHERE DATE(timestamp AT TIME ZONE 'UTC') = %s
          AND EXTRACT(HOUR FROM timestamp AT TIME ZONE 'UTC') IN (0, 6, 12, 18)
        ORDER BY variable_name, forecast_horizon_h, latitude, longitude
    """
    df = pd.read_sql(query, conn, params=(evaluation_date,))
    return df


def load_truth_for_date(conn, truth_table: str, evaluation_date: date) -> pd.DataFrame:
    """
    Charge la vérité terrain pour les 4 timestamps d'une date.

    Returns:
        DataFrame avec colonnes : timestamp, variable_name, latitude, longitude, value
    """
    query = f"""
        SELECT
            timestamp,
            variable_name,
            latitude,
            longitude,
            value
        FROM {truth_table}
        WHERE DATE(timestamp AT TIME ZONE 'UTC') = %s
          AND EXTRACT(HOUR FROM timestamp AT TIME ZONE 'UTC') IN (0, 6, 12, 18)
        ORDER BY variable_name, latitude, longitude
    """
    df = pd.read_sql(query, conn, params=(evaluation_date,))
    return df


# ───────────────────────────────────────────────────────────────────────────
# CALCUL DES MÉTRIQUES
# ───────────────────────────────────────────────────────────────────────────

def compute_metrics_for_group(
    predict_values: np.ndarray,
    truth_values: np.ndarray,
    cyclic_period: Optional[float] = None,
) -> dict:
    """
    Calcule MAE, RMSE, Bias sur un ensemble de paires (prédit, vrai).

    Args:
        predict_values: array des valeurs prédites
        truth_values:   array des valeurs vraies (même taille)
        cyclic_period:  si fourni (ex: 360 pour la direction du vent), applique
                        la formule cyclique pour MAE/RMSE et force bias=None
                        (le biais n'a pas de sens physique simple sur un angle).

    Returns:
        dict avec mae, rmse, bias, sample_count
    """
    if len(predict_values) != len(truth_values):
        raise ValueError(f"Taille différente : predict={len(predict_values)}, truth={len(truth_values)}")

    if len(predict_values) == 0:
        return {"mae": None, "rmse": None, "bias": None, "sample_count": 0}

    if cyclic_period is not None:
        # Différence angulaire minimale : ex. entre 5° et 355°, l'écart vrai est 10° (pas 350°).
        # Formule : min(|a-b| mod P, P - |a-b| mod P)
        raw_diff = np.abs(predict_values - truth_values) % cyclic_period
        abs_errors = np.minimum(raw_diff, cyclic_period - raw_diff)

        mae = float(np.mean(abs_errors))
        rmse = float(np.sqrt(np.mean(abs_errors ** 2)))
        bias = None  # Pas de bias signé interprétable pour une variable cyclique
        sample_count = len(abs_errors)
    else:
        # Cas standard (variables linéaires : t2m, vent, pression, etc.)
        errors = predict_values - truth_values  # erreur signée

        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        bias = float(np.mean(errors))
        sample_count = len(errors)

    return {
        "mae": mae,
        "rmse": rmse,
        "bias": bias,
        "sample_count": sample_count,
    }


def compute_metrics_for_comparison(
    predictions_df: pd.DataFrame,
    truth_df: pd.DataFrame,
    comparison_name: str,
    evaluation_date: date,
) -> list:
    """
    Calcule les métriques pour 1 comparaison sur 1 date.
    Boucle sur chaque (variable × horizon).

    Returns:
        Liste de dicts (1 par variable × horizon).
    """
    rows = []

    # Pour chaque combinaison variable × horizon
    for variable in VARIABLES:
        for horizon in HORIZONS:
            # Filtrer prédictions
            pred_subset = predictions_df[
                (predictions_df["variable_name"] == variable) &
                (predictions_df["forecast_horizon_h"] == horizon)
            ]

            if pred_subset.empty:
                logger.debug(f"   ⚠️  Pas de prédictions pour {variable} +{horizon}h")
                continue

            # Filtrer vérité (sur le même timestamp)
            # On déduit le timestamp depuis les prédictions
            pred_timestamps = pred_subset["timestamp"].unique()
            if len(pred_timestamps) != 1:
                logger.warning(f"   ⚠️  {variable} +{horizon}h : {len(pred_timestamps)} timestamps distincts (attendu 1)")
                continue

            target_timestamp = pred_timestamps[0]
            truth_subset = truth_df[
                (truth_df["variable_name"] == variable) &
                (truth_df["timestamp"] == target_timestamp)
            ]

            if truth_subset.empty:
                logger.debug(f"   ⚠️  Pas de vérité pour {variable} à {target_timestamp}")
                continue

            # Joindre prédict ↔ vérité sur (lat, lon)
            merged = pd.merge(
                pred_subset[["latitude", "longitude", "value"]].rename(columns={"value": "predict_value"}),
                truth_subset[["latitude", "longitude", "value"]].rename(columns={"value": "truth_value"}),
                on=["latitude", "longitude"],
                how="inner",
            )

            if merged.empty:
                logger.warning(f"   ⚠️  {variable} +{horizon}h : aucun point commun après jointure")
                continue

            # Calcul métriques (avec gestion cyclique pour wind_direction_10m_deg)
            predict_values = merged["predict_value"].astype(np.float64).values
            truth_values = merged["truth_value"].astype(np.float64).values
            cyclic_period = CYCLIC_VARIABLES.get(variable)
            metrics = compute_metrics_for_group(
                predict_values, truth_values, cyclic_period=cyclic_period,
            )

            rows.append({
                "comparison": comparison_name,
                "evaluation_date": evaluation_date,
                "variable_name": variable,
                "forecast_horizon_h": horizon,
                "mae": metrics["mae"],
                "rmse": metrics["rmse"],
                "bias": metrics["bias"],
                "sample_count": metrics["sample_count"],
            })

    return rows


# ───────────────────────────────────────────────────────────────────────────
# INSERTION EN DB (UPSERT)
# ───────────────────────────────────────────────────────────────────────────

def upsert_metrics(conn, rows: list, dry_run: bool = False) -> int:
    """
    Insère ou met à jour les lignes dans mae_metrics via UPSERT.

    Returns:
        Nombre de lignes insérées/mises à jour.
    """
    if not rows:
        return 0

    if dry_run:
        logger.info(f"   🧪 DRY-RUN : pas d'écriture en DB ({len(rows)} lignes)")
        return 0

    cursor = conn.cursor()
    try:
        upsert_sql = """
            INSERT INTO mae_metrics
                (comparison, evaluation_date, variable_name, forecast_horizon_h,
                 mae, rmse, bias, sample_count)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (comparison, evaluation_date, variable_name, forecast_horizon_h)
            DO UPDATE SET
                mae = EXCLUDED.mae,
                rmse = EXCLUDED.rmse,
                bias = EXCLUDED.bias,
                sample_count = EXCLUDED.sample_count
        """
        params = [
            (
                row["comparison"],
                row["evaluation_date"],
                row["variable_name"],
                row["forecast_horizon_h"],
                row["mae"],
                row["rmse"],
                row["bias"],
                row["sample_count"],
            )
            for row in rows
        ]
        cursor.executemany(upsert_sql, params)
        n_inserted = cursor.rowcount
        conn.commit()
        return n_inserted

    except Exception as e:
        conn.rollback()
        logger.error(f"   ❌ Erreur UPSERT : {e}")
        raise
    finally:
        cursor.close()


# ───────────────────────────────────────────────────────────────────────────
# COMPUTE MAE POUR 1 DATE / 1 COMPARAISON
# ───────────────────────────────────────────────────────────────────────────

def compute_one_comparison(
    conn,
    comparison_name: str,
    evaluation_date: date,
    dry_run: bool = False,
) -> dict:
    """Calcule les métriques pour 1 comparaison sur 1 date."""
    config = COMPARISONS[comparison_name]
    label = config["label"]

    logger.info(f"\n   🎯 {label}")
    t0 = time.time()

    # Charger les données
    predictions_df = load_predictions_for_date(conn, config["predict_view"], evaluation_date)
    truth_df = load_truth_for_date(conn, config["truth_table"], evaluation_date)

    logger.info(f"      📊 Prédictions : {len(predictions_df):,} lignes")
    logger.info(f"      📊 Vérité      : {len(truth_df):,} lignes")

    if predictions_df.empty:
        logger.warning(f"      ⚠️  Pas de prédictions pour le {evaluation_date}, skip")
        return {"rows_computed": 0, "rows_upserted": 0}

    if truth_df.empty:
        logger.warning(f"      ⚠️  Pas de vérité pour le {evaluation_date}, skip")
        return {"rows_computed": 0, "rows_upserted": 0}

    # Calculer
    metrics_rows = compute_metrics_for_comparison(
        predictions_df, truth_df, comparison_name, evaluation_date,
    )
    logger.info(f"      🧮 Calculé : {len(metrics_rows)} lignes (variables × horizons)")

    # Insérer
    n_upserted = upsert_metrics(conn, metrics_rows, dry_run=dry_run)
    logger.info(f"      💾 Upserted : {n_upserted} lignes en DB")

    elapsed = time.time() - t0
    logger.info(f"      ⏱️  {elapsed:.1f}s")

    # Petit récap des métriques (top variables par MAE)
    if metrics_rows:
        df_metrics = pd.DataFrame(metrics_rows)
        df_summary = df_metrics.groupby("variable_name").agg({
            "mae": "mean",
            "sample_count": "sum",
        }).round(3).sort_values("mae", ascending=False)
        logger.info(f"      📋 MAE moyen par variable :")
        for var, row in df_summary.iterrows():
            logger.info(f"         • {var:30s} MAE={row['mae']:>8.3f}, n={int(row['sample_count']):,}")

    return {"rows_computed": len(metrics_rows), "rows_upserted": n_upserted}


# ───────────────────────────────────────────────────────────────────────────
# COMPUTE MAE POUR 1 DATE (toutes comparaisons)
# ───────────────────────────────────────────────────────────────────────────

def compute_for_date(
    conn,
    evaluation_date: date,
    skip_graphcast: bool = False,
    skip_arome: bool = False,
    dry_run: bool = False,
) -> dict:
    """Calcule toutes les comparaisons pour 1 date."""
    logger.info(f"\n📅 Date évaluée : {evaluation_date}")

    results = {}

    if not skip_graphcast:
        results["graphcast_vs_era5"] = compute_one_comparison(
            conn, "graphcast_vs_era5", evaluation_date, dry_run=dry_run,
        )

    if not skip_arome:
        results["arome_vs_era5"] = compute_one_comparison(
            conn, "arome_vs_era5", evaluation_date, dry_run=dry_run,
        )

    return results


# ───────────────────────────────────────────────────────────────────────────
# VALIDATION POST-INSERTION
# ───────────────────────────────────────────────────────────────────────────

def show_table_state(conn):
    """Affiche l'état de la table mae_metrics."""
    logger.info("\n" + "=" * 70)
    logger.info("📊 ÉTAT DE LA TABLE mae_metrics")
    logger.info("=" * 70)

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM mae_metrics")
        total = cursor.fetchone()[0]
        logger.info(f"\n   📊 Total lignes : {total:,}")

        cursor.execute("""
            SELECT comparison, COUNT(*) as n
            FROM mae_metrics
            GROUP BY comparison
            ORDER BY comparison
        """)
        logger.info(f"\n   📋 Par comparaison :")
        for comp, n in cursor.fetchall():
            logger.info(f"      • {comp:30s} {n:>5} lignes")

        cursor.execute("""
            SELECT MIN(evaluation_date), MAX(evaluation_date),
                   COUNT(DISTINCT evaluation_date) as n_dates
            FROM mae_metrics
        """)
        row = cursor.fetchone()
        if row[0]:
            logger.info(f"\n   📅 Plage de dates : {row[0]} → {row[1]} ({row[2]} dates)")

    finally:
        cursor.close()


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def parse_arguments():
    parser = argparse.ArgumentParser(description="Calcul MAE/RMSE/Bias")
    parser.add_argument("--date", type=str, default=None,
                        help="Date d'évaluation unique (YYYY-MM-DD)")
    parser.add_argument("--start-date", type=str, default=None,
                        help="Date de début (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None,
                        help="Date de fin (YYYY-MM-DD)")
    parser.add_argument("--skip-graphcast", action="store_true",
                        help="Skip la comparaison graphcast_vs_era5")
    parser.add_argument("--skip-arome", action="store_true",
                        help="Skip la comparaison arome_vs_era5")
    parser.add_argument("--dry-run", action="store_true",
                        help="Calcule mais n'insère pas en DB")
    parser.add_argument("--no-validation", action="store_true",
                        help="Skip la validation finale")
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

    # Liste des dates
    if args.date:
        try:
            dates = [datetime.strptime(args.date, "%Y-%m-%d").date()]
        except ValueError:
            logger.error(f"❌ Format date invalide : {args.date}")
            sys.exit(1)
    else:
        try:
            start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
            end = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError as e:
            logger.error(f"❌ Format date invalide : {e}")
            sys.exit(1)

        dates = []
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)

    # Banner
    logger.info("╔" + "═" * 68 + "╗")
    msg = "📊 CALCUL MAE/RMSE/Bias"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╠" + "═" * 68 + "╣")
    msg = f"Dates    : {len(dates)} ({dates[0]} → {dates[-1]})"
    logger.info(f"║  {msg:<66s}║")
    msg = f"Compar.  : {'graphcast_vs_era5' if not args.skip_graphcast else '(SKIP)'} | {'arome_vs_era5' if not args.skip_arome else '(SKIP)'}"
    logger.info(f"║  {msg:<66s}║")
    msg = f"Mode     : {'DRY-RUN' if args.dry_run else 'PRODUCTION'}"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")

    # Connexion DB
    logger.info("\n🔌 Connexion à la DB...")
    try:
        conn = get_db_connection()
    except Exception as e:
        logger.error(f"❌ Impossible de se connecter : {e}")
        sys.exit(1)

    t_global_start = time.time()
    total_upserted = 0

    try:
        for d in dates:
            results = compute_for_date(
                conn, d,
                skip_graphcast=args.skip_graphcast,
                skip_arome=args.skip_arome,
                dry_run=args.dry_run,
            )
            for comp_name, stats in results.items():
                total_upserted += stats["rows_upserted"]

        # Validation
        if not args.no_validation and not args.dry_run:
            show_table_state(conn)

    finally:
        conn.close()

    # Récap
    elapsed_min = (time.time() - t_global_start) / 60
    logger.info("\n" + "╔" + "═" * 68 + "╗")
    msg = f"✅ CALCUL MAE TERMINÉ en {elapsed_min:.1f} min"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")
    logger.info(f"\n📊 Total lignes upserted : {total_upserted}")

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompu")
        sys.exit(1)
