"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Ingestion des données en PostgreSQL
FICHIER  : utils/db_connection.py
RÔLE     : Centraliser la connexion PostgreSQL pour tous les scripts
═══════════════════════════════════════════════════════════════════════════

POURQUOI CE FICHIER ?
---------------------
Tous nos scripts d'ingestion (ingest_graphcast, ingest_era5, ingest_arome,
daily_*) ont besoin de se connecter à la même base de données PostgreSQL.

Au lieu de répéter la logique de connexion dans CHAQUE script (DRY violé),
on centralise tout ici. Les autres scripts feront juste :

    from utils.db_connection import get_db_connection
    conn = get_db_connection()

Cela apporte 4 avantages :
1. Moins de code dupliqué (DRY = Don't Repeat Yourself)
2. Si on change le mot de passe, on modifie UN seul endroit
3. Logging cohérent et standardisé
4. Gestion centralisée des erreurs

INSPIRATION
-----------
Pattern identique à ton script `fetch_rte_data.py` du projet
electricity_consumption_dashboard, mais factorisé dans un module dédié.
═══════════════════════════════════════════════════════════════════════════
"""

import os
import logging
import psycopg2
from psycopg2.extensions import connection as PGConnection
from dotenv import load_dotenv


# ───────────────────────────────────────────────────────────────────────────
# Chargement des variables d'environnement depuis le fichier .env
# ───────────────────────────────────────────────────────────────────────────
# Le fichier .env (à la racine du projet) doit contenir :
#   DB_HOST=localhost
#   DB_PORT=5433
#   DB_NAME=meteo_ia_db
#   DB_USER=meteo_user
#   DB_PASSWORD=meteo_pwd_2026
#
# IMPORTANT : .env DOIT être dans .gitignore (ne JAMAIS commit les passwords)
load_dotenv()


# ───────────────────────────────────────────────────────────────────────────
# Configuration du logger pour ce module
# ───────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


def get_db_connection() -> PGConnection:
    """
    Établit une connexion à la base de données PostgreSQL.

    Returns:
        psycopg2.extensions.connection : objet connexion PostgreSQL ouvert.
            À fermer impérativement avec conn.close() après usage.

    Raises:
        psycopg2.OperationalError : si la DB n'est pas joignable
            (Docker arrêté, mauvais credentials, port fermé...)
        ValueError : si une variable d'environnement DB_* est manquante.

    Exemple :
        >>> conn = get_db_connection()
        >>> cursor = conn.cursor()
        >>> cursor.execute("SELECT COUNT(*) FROM era5_truth")
        >>> print(cursor.fetchone()[0])
        >>> cursor.close()
        >>> conn.close()
    """
    # Récupération des paramètres depuis l'environnement
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    # Validation : toutes les variables doivent être présentes
    missing = [
        var for var, val in [
            ("DB_HOST", db_host),
            ("DB_PORT", db_port),
            ("DB_NAME", db_name),
            ("DB_USER", db_user),
            ("DB_PASSWORD", db_password),
        ] if not val
    ]
    if missing:
        raise ValueError(
            f"Variables d'environnement manquantes : {', '.join(missing)}. "
            f"Vérifie ton fichier .env"
        )

    # Tentative de connexion
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password,
        )

        # Forcer UTC pour cette session (cohérence cruciale)
        # Bien que la database soit déjà configurée en UTC via ALTER DATABASE,
        # on force ici par sécurité au cas où un .env aurait une timezone
        # locale qui surcharge.
        with conn.cursor() as cur:
            cur.execute("SET timezone = 'UTC'")
        conn.commit()

        logger.info(
            f"✓ Connexion DB OK : {db_user}@{db_host}:{db_port}/{db_name} (UTC)"
        )
        return conn

    except psycopg2.OperationalError as e:
        logger.error(
            f"✗ Échec connexion DB : {e}. "
            f"Vérifie que Docker tourne et que .env est correct."
        )
        raise


def test_connection() -> bool:
    """
    Teste la connexion à la base de données et affiche les infos clés.

    Utile pour vérifier que tout est bien configuré AVANT de lancer
    un script d'ingestion. Tu peux l'appeler en standalone :

        $ python -m utils.db_connection

    Returns:
        bool : True si tout est OK, False sinon.
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Vérifier la version PostgreSQL
            cur.execute("SELECT version()")
            pg_version = cur.fetchone()[0]

            # Vérifier la timezone de la session
            cur.execute("SHOW timezone")
            tz = cur.fetchone()[0]

            # Vérifier que les 4 tables existent
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                  AND table_name IN ('era5_truth', 'arome_forecasts',
                                     'graphcast_predictions', 'mae_metrics')
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]

            # Vérifier que les 2 vues existent
            cur.execute("""
                SELECT table_name FROM information_schema.views
                WHERE table_schema = 'public'
                  AND table_name IN ('arome_forecasts_fresh',
                                     'graphcast_predictions_fresh')
                ORDER BY table_name
            """)
            views = [row[0] for row in cur.fetchall()]

        conn.close()

        # Affichage du résumé
        print("\n" + "═" * 70)
        print("  TEST DE CONNEXION DB — RÉSULTATS")
        print("═" * 70)
        print(f"  PostgreSQL  : {pg_version[:50]}...")
        print(f"  Timezone    : {tz}")
        print(f"  Tables ({len(tables)}/4) : {', '.join(tables)}")
        print(f"  Vues   ({len(views)}/2) : {', '.join(views)}")

        if len(tables) == 4 and len(views) == 2:
            print("\n  ✓ TOUT EST OK ! Tu peux lancer les scripts d'ingestion.")
            print("═" * 70 + "\n")
            return True
        else:
            print("\n  ⚠ PROBLÈME : tables ou vues manquantes.")
            print("    → Re-exécute init_db_schema.sql dans DBeaver")
            print("═" * 70 + "\n")
            return False

    except Exception as e:
        print(f"\n✗ Échec du test : {e}\n")
        return False


# ───────────────────────────────────────────────────────────────────────────
# Point d'entrée pour exécution directe (test)
# ───────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Configuration logging basique pour les tests standalone
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
    )
    test_connection()
