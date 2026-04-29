"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Ingestion des prédictions GraphCast en DB PostgreSQL
FICHIER  : scripts/graphcast_gfs/ingest_graphcast_to_db.py
RÔLE     : Importe les CSV de prédictions GraphCast dans la table
           graphcast_predictions de PostgreSQL.
═══════════════════════════════════════════════════════════════════════════

STRATÉGIE D'INGESTION
---------------------
1. Crée une TABLE TEMPORAIRE identique à graphcast_predictions
2. Utilise COPY (psycopg2.copy_expert) pour charger TRÈS RAPIDEMENT le CSV
3. Fait un INSERT ... ON CONFLICT DO UPDATE depuis la temp vers la vraie table
4. Supprime la table temporaire

Avantages de cette approche :
- COPY est la méthode la plus rapide pour insérer de gros volumes
  (~200 000 lignes/seconde sur PostgreSQL local)
- ON CONFLICT DO UPDATE (upsert) = idempotence : re-run sans erreur
- Table temporaire = pas de verrouillage de la vraie table

MAPPING CSV → DB
----------------
  CSV                       → DB
  ─────────────────────────────────────────
  run_datetime_utc          → run_timestamp
  forecast_timestamp_utc    → timestamp
  lead_hours                → forecast_horizon_h
  lat                       → latitude
  lon                       → longitude
  variable_name             → variable_name
  value                     → value
  unit                      → unit

USAGE
-----
    conda activate meteo_ia
    cd /Users/kouande/Desktop/PROJETS/Dev_meteo/meteo_ia_france/scripts

    # Ingérer TOUS les CSV du dossier (par défaut)
    python -m graphcast_gfs.ingest_graphcast_to_db

    # Ingérer UN fichier spécifique
    python -m graphcast_gfs.ingest_graphcast_to_db --csv graphcast_20260416_18h.csv

    # Mode test (dry-run, pas d'écriture en DB)
    python -m graphcast_gfs.ingest_graphcast_to_db --dry-run

TEMPS ESTIMÉ
------------
- Par CSV (93 600 lignes) : ~2-5 secondes
- Total 8 CSV (~750 000 lignes) : ~30 secondes
═══════════════════════════════════════════════════════════════════════════
"""

import argparse
import csv
import io
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

# Import du helper de connexion DB
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db_connection import get_db_connection


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ───────────────────────────────────────────────────────────────────────────

BASE_DIR = Path.home() / "Desktop" / "PROJETS" / "Dev_meteo" / "meteo_ia_france"
CSV_DIR = BASE_DIR / "data" / "graphcast_predictions_csv"

TABLE_NAME = "graphcast_predictions"
TEMP_TABLE_NAME = "graphcast_predictions_staging"

# Colonnes de la table cible (ordre important pour COPY)
DB_COLUMNS = [
    "run_timestamp",
    "timestamp",
    "forecast_horizon_h",
    "variable_name",
    "unit",
    "latitude",
    "longitude",
    "value",
]

# Clé UNIQUE pour l'upsert (d'après init_db_schema.sql)
UNIQUE_KEY = [
    "run_timestamp",
    "timestamp",
    "variable_name",
    "latitude",
    "longitude",
]

# Colonnes mises à jour en cas de conflit (tout sauf la clé unique)
UPDATE_COLUMNS = ["forecast_horizon_h", "unit", "value"]


# ───────────────────────────────────────────────────────────────────────────
# TRANSFORMATION CSV → FORMAT COPY
# ───────────────────────────────────────────────────────────────────────────

def transform_csv_row(row: dict) -> tuple:
    """
    Transforme une ligne CSV en tuple ordonné selon DB_COLUMNS.

    CSV source :
        run_datetime_utc, forecast_timestamp_utc, lead_hours,
        lat, lon, variable_name, value, unit

    DB cible :
        run_timestamp, timestamp, forecast_horizon_h, variable_name,
        unit, latitude, longitude, value
    """
    return (
        row["run_datetime_utc"],          # run_timestamp
        row["forecast_timestamp_utc"],    # timestamp
        int(row["lead_hours"]),           # forecast_horizon_h
        row["variable_name"],             # variable_name
        row["unit"],                      # unit
        float(row["lat"]),                # latitude
        float(row["lon"]),                # longitude
        float(row["value"]),              # value
    )


def csv_to_buffer(csv_path: Path) -> io.StringIO:
    """
    Lit un CSV et transforme chaque ligne au format DB dans un buffer
    StringIO compatible avec psycopg2 COPY.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            db_row = transform_csv_row(row)
            writer.writerow(db_row)

    buffer.seek(0)
    return buffer


# ───────────────────────────────────────────────────────────────────────────
# INGESTION D'UN CSV
# ───────────────────────────────────────────────────────────────────────────

def ingest_csv_to_db(
    csv_path: Path,
    conn,
    dry_run: bool = False,
) -> dict:
    """
    Ingère un CSV complet dans la DB via la stratégie :
      1. Crée table temporaire
      2. COPY CSV → table temporaire
      3. INSERT ... ON CONFLICT DO UPDATE depuis temp vers graphcast_predictions
      4. DROP table temporaire

    Retourne un dict avec les stats : {rows_inserted, rows_updated, duration}
    """
    logger.info(f"\n📂 Traitement {csv_path.name}")
    t_start = time.time()

    # Compter les lignes CSV
    with open(csv_path, "r", encoding="utf-8") as f:
        n_csv_rows = sum(1 for _ in f) - 1  # -1 pour le header
    logger.info(f"   📊 {n_csv_rows:,} lignes dans le CSV")

    if dry_run:
        logger.info(f"   🧪 DRY-RUN : pas d'écriture en DB")
        return {"rows_csv": n_csv_rows, "rows_affected": 0, "duration": 0}

    cursor = conn.cursor()

    try:
        # ═══ 1. Créer la table temporaire ═══
        logger.info(f"   🔧 Création table temporaire {TEMP_TABLE_NAME}")
        cursor.execute(f"""
            CREATE TEMP TABLE {TEMP_TABLE_NAME} (
                run_timestamp       TIMESTAMP WITH TIME ZONE NOT NULL,
                timestamp           TIMESTAMP WITH TIME ZONE NOT NULL,
                forecast_horizon_h  INT NOT NULL,
                variable_name       VARCHAR(50) NOT NULL,
                unit                VARCHAR(10),
                latitude            NUMERIC(9, 6) NOT NULL,
                longitude           NUMERIC(9, 6) NOT NULL,
                value               NUMERIC(10, 4) NOT NULL
            ) ON COMMIT DROP
        """)

        # ═══ 2. COPY CSV → table temporaire ═══
        logger.info(f"   📤 COPY → {TEMP_TABLE_NAME}")
        t_copy = time.time()
        buffer = csv_to_buffer(csv_path)

        cursor.copy_expert(
            sql=f"""
                COPY {TEMP_TABLE_NAME}
                ({', '.join(DB_COLUMNS)})
                FROM STDIN WITH (FORMAT csv, DELIMITER E'\t', HEADER false)
            """,
            file=buffer,
        )
        logger.info(f"      ✅ COPY terminé en {time.time() - t_copy:.1f}s")

        # ═══ 3. UPSERT depuis temp vers vraie table ═══
        logger.info(f"   📥 UPSERT → {TABLE_NAME}")
        t_upsert = time.time()

        # Construction dynamique de la clause ON CONFLICT
        update_clause = ", ".join([
            f"{col} = EXCLUDED.{col}" for col in UPDATE_COLUMNS
        ])
        unique_key_str = ", ".join(UNIQUE_KEY)

        upsert_sql = f"""
            INSERT INTO {TABLE_NAME}
                ({', '.join(DB_COLUMNS)})
            SELECT {', '.join(DB_COLUMNS)} FROM {TEMP_TABLE_NAME}
            ON CONFLICT ({unique_key_str}) DO UPDATE SET
                {update_clause}
        """
        cursor.execute(upsert_sql)
        rows_affected = cursor.rowcount
        logger.info(f"      ✅ UPSERT terminé en {time.time() - t_upsert:.1f}s ({rows_affected:,} lignes)")

        # Commit de la transaction
        conn.commit()

        duration = time.time() - t_start
        logger.info(f"   ✅ Ingestion OK en {duration:.1f}s")

        return {
            "rows_csv": n_csv_rows,
            "rows_affected": rows_affected,
            "duration": duration,
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"   ❌ Erreur : {e}")
        raise

    finally:
        cursor.close()


# ───────────────────────────────────────────────────────────────────────────
# VALIDATION POST-INGESTION
# ───────────────────────────────────────────────────────────────────────────

def validate_ingestion(conn):
    """Exécute des requêtes de validation sur la table après ingestion."""
    logger.info("\n" + "=" * 70)
    logger.info("📊 VALIDATION DE L'INGESTION")
    logger.info("=" * 70)

    cursor = conn.cursor()

    try:
        # 1. Nombre total de lignes
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        total_rows = cursor.fetchone()[0]
        logger.info(f"\n   📊 Total lignes dans {TABLE_NAME} : {total_rows:,}")

        # 2. Nombre de runs distincts
        cursor.execute(f"SELECT COUNT(DISTINCT run_timestamp) FROM {TABLE_NAME}")
        n_runs = cursor.fetchone()[0]
        logger.info(f"   📊 Runs distincts : {n_runs}")

        # 3. Variables distinctes
        cursor.execute(f"""
            SELECT variable_name, COUNT(*) as n
            FROM {TABLE_NAME}
            GROUP BY variable_name
            ORDER BY variable_name
        """)
        logger.info(f"\n   📋 Variables ingérées :")
        for var, n in cursor.fetchall():
            logger.info(f"      • {var:30s} {n:>10,} lignes")

        # 4. Horizons distincts
        cursor.execute(f"""
            SELECT forecast_horizon_h, COUNT(*) as n
            FROM {TABLE_NAME}
            GROUP BY forecast_horizon_h
            ORDER BY forecast_horizon_h
        """)
        logger.info(f"\n   ⏱️  Horizons :")
        for h, n in cursor.fetchall():
            logger.info(f"      • +{h}h : {n:,} lignes")

        # 5. Plage temporelle
        cursor.execute(f"""
            SELECT MIN(run_timestamp), MAX(run_timestamp),
                   MIN(timestamp), MAX(timestamp)
            FROM {TABLE_NAME}
        """)
        min_run, max_run, min_ts, max_ts = cursor.fetchone()
        logger.info(f"\n   📅 Plage temporelle :")
        logger.info(f"      • Runs de {min_run} à {max_run}")
        logger.info(f"      • Prédictions de {min_ts} à {max_ts}")

        # 6. Statistiques par variable (t2m en exemple)
        cursor.execute(f"""
            SELECT MIN(value), MAX(value), AVG(value)
            FROM {TABLE_NAME}
            WHERE variable_name = 't2m_celsius'
        """)
        row = cursor.fetchone()
        if row[0] is not None:
            logger.info(f"\n   🌡️  t2m_celsius : min={row[0]:.2f}°C, max={row[1]:.2f}°C, moy={row[2]:.2f}°C")

    finally:
        cursor.close()


# ───────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ───────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Ingestion CSV GraphCast → PostgreSQL",
    )
    parser.add_argument(
        "--csv", type=str, default=None,
        help="Nom d'un CSV spécifique (dans graphcast_predictions_csv/). Sinon tous.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulation : pas d'écriture en DB",
    )
    parser.add_argument(
        "--skip-validation", action="store_true",
        help="Skip la validation post-ingestion",
    )
    args = parser.parse_args()

    # Banner
    logger.info("╔" + "═" * 68 + "╗")
    msg = "📥 INGESTION GRAPHCAST → PostgreSQL"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")
    logger.info(f"   Source  : {CSV_DIR}")
    logger.info(f"   Cible   : {TABLE_NAME}")
    logger.info(f"   Dry-run : {args.dry_run}")

    # Lister les CSV à ingérer
    if args.csv:
        csv_paths = [CSV_DIR / args.csv]
        if not csv_paths[0].exists():
            logger.error(f"❌ CSV introuvable : {csv_paths[0]}")
            sys.exit(1)
    else:
        csv_paths = sorted(CSV_DIR.glob("graphcast_*.csv"))

    if not csv_paths:
        logger.error("❌ Aucun CSV à ingérer")
        sys.exit(1)

    logger.info(f"\n📅 Fichiers à ingérer : {len(csv_paths)}")
    for p in csv_paths:
        logger.info(f"   • {p.name}")

    # Connexion DB
    if not args.dry_run:
        logger.info("\n🔌 Connexion à la DB...")
        try:
            conn = get_db_connection()
            logger.info("   ✅ Connecté")
        except Exception as e:
            logger.error(f"❌ Impossible de se connecter à la DB : {e}")
            sys.exit(1)
    else:
        conn = None

    # Ingestion
    t_global_start = time.time()
    results = {"success": [], "failed": []}

    for csv_path in csv_paths:
        try:
            stats = ingest_csv_to_db(csv_path, conn, dry_run=args.dry_run)
            results["success"].append((csv_path, stats))
        except Exception as e:
            logger.error(f"\n❌ Échec pour {csv_path.name} : {e}")
            import traceback
            logger.error(traceback.format_exc())
            results["failed"].append((csv_path, str(e)))

    # Validation post-ingestion
    if not args.dry_run and not args.skip_validation and results["success"]:
        try:
            validate_ingestion(conn)
        except Exception as e:
            logger.warning(f"\n⚠️ Validation échouée : {e}")

    # Fermer connexion
    if conn:
        conn.close()

    # Récap
    elapsed_min = (time.time() - t_global_start) / 60
    logger.info("\n" + "╔" + "═" * 68 + "╗")
    msg = f"✅ INGESTION TERMINÉE en {elapsed_min:.1f} min"
    logger.info(f"║  {msg:<66s}║")
    logger.info("╚" + "═" * 68 + "╝")
    logger.info(f"\n📊 Résultats :")
    logger.info(f"   Succès : {len(results['success'])}/{len(csv_paths)}")
    logger.info(f"   Échecs : {len(results['failed'])}/{len(csv_paths)}")

    if results["success"]:
        total_rows = sum(s[1].get("rows_affected", 0) for s in results["success"])
        logger.info(f"   Lignes ingérées : {total_rows:,}")

    if results["failed"]:
        logger.warning("\n⚠️ Fichiers en échec :")
        for csv_path, err in results["failed"]:
            logger.warning(f"   • {csv_path.name} : {err}")

    sys.exit(0 if not results["failed"] else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompu par l'utilisateur")
        sys.exit(1)
