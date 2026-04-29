"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Ingestion des données en PostgreSQL
FICHIER  : utils/date_utils.py
RÔLE     : Centraliser la gestion des dates en UTC strict
═══════════════════════════════════════════════════════════════════════════

POURQUOI CE FICHIER ?
---------------------
La gestion des dates est LE piège classique en météo :
  • Sources externes (ERA5, AROME, GraphCast) sont en UTC
  • Le système Mac est en heure de Paris (UTC+1 / UTC+2)
  • Si on mélange = bugs subtils, données incohérentes, debug pénible

Ce module garantit que TOUTES les dates dans nos scripts sont :
  ✓ tz-aware (avec timezone explicite)
  ✓ en UTC strict
  ✓ calculées dynamiquement (jamais en dur)

INSPIRATION
-----------
Pattern proche de la gestion datetime dans ton fetch_rte_data.py
(fonction get_timezone_offset), mais simplifié : on ne fait PAS de conversion
locale, on reste en UTC partout (la conversion se fait côté frontend).

UTILISATION
-----------
    from utils.date_utils import (
        now_utc,
        today_utc_midnight,
        get_historical_dates,
        get_era5_available_dates,
    )

    # Aujourd'hui à 00h UTC
    today = today_utc_midnight()

    # Les 8 derniers jours pour AROME/GraphCast
    dates = get_historical_dates(num_days=8)

    # Les dates ERA5 disponibles (latence 5 jours)
    era5_dates = get_era5_available_dates(num_days=8)
═══════════════════════════════════════════════════════════════════════════
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Tuple


# ───────────────────────────────────────────────────────────────────────────
# Configuration du logger pour ce module
# ───────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# CONSTANTES MÉTIER (modifiables depuis ici sans toucher aux scripts)
# ───────────────────────────────────────────────────────────────────────────

# Pas de temps en heures (contrainte architecturale GraphCast)
PAS_DE_TEMPS_H = 6

# Heures UTC des runs/snapshots dans une journée
# Aligné sur GraphCast (00h, 06h, 12h, 18h UTC)
RUN_HOURS_UTC = [0, 6, 12, 18]

# Latence ERA5 (réanalyse Copernicus publiée avec 5 jours de retard)
ERA5_LATENCY_DAYS = 5

# Nombre de jours d'historique par défaut pour les batchs initiaux
DEFAULT_HISTORICAL_DAYS = 8

# Horizon de prévision en heures (J+1 = 24h pour MVP v1.0)
FORECAST_HORIZON_H = 24

# Liste des horizons par run (déduit du pas et de l'horizon max)
# Pour MVP v1.0 : [6, 12, 18, 24]
FORECAST_HORIZONS_H = list(range(PAS_DE_TEMPS_H, FORECAST_HORIZON_H + 1, PAS_DE_TEMPS_H))


# ───────────────────────────────────────────────────────────────────────────
# FONCTIONS DE BASE — Récupération de l'heure actuelle en UTC
# ───────────────────────────────────────────────────────────────────────────

def now_utc() -> datetime:
    """
    Retourne l'instant présent en UTC (datetime tz-aware).

    Pourquoi cette fonction au lieu de datetime.now() ?
        datetime.now() retourne l'heure locale (= Paris sur ton Mac)
        et est "tz-naive" (pas de timezone), ce qui pose problèmes
        quand PostgreSQL essaie de l'interpréter.

    Returns:
        datetime tz-aware en UTC.

    Exemple :
        >>> now_utc()
        datetime.datetime(2026, 4, 23, 10, 35, 12, tzinfo=datetime.timezone.utc)
    """
    return datetime.now(timezone.utc)


def today_utc_midnight() -> datetime:
    """
    Retourne aujourd'hui à 00:00 UTC (datetime tz-aware).

    Utile comme point de référence pour calculer "il y a N jours".

    Returns:
        datetime tz-aware UTC à minuit.

    Exemple :
        Si on est le 23 avril 2026 à 10h35 UTC, retourne :
        datetime(2026, 4, 23, 0, 0, 0, tzinfo=timezone.utc)
    """
    now = now_utc()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


# ───────────────────────────────────────────────────────────────────────────
# FONCTIONS HISTORIQUES — Liste des dates pour batch one-shot
# ───────────────────────────────────────────────────────────────────────────

def get_historical_dates(num_days: int = DEFAULT_HISTORICAL_DAYS) -> List[datetime]:
    """
    Retourne les N derniers jours à 00h UTC, du plus ANCIEN au plus RÉCENT.

    Utilisé pour le BATCH initial (collecte historique 8 jours) des sources
    GraphCast et AROME (pas ERA5 qui a une latence — voir fonction dédiée).

    Args:
        num_days: Nombre de jours d'historique (défaut 8).

    Returns:
        Liste de datetime tz-aware UTC, triée du plus ancien au plus récent.

    Exemple :
        Si aujourd'hui = 23 avril 2026 et num_days=8, retourne :
        [16/04 00h UTC, 17/04 00h UTC, ..., 22/04 00h UTC, 23/04 00h UTC]
    """
    today = today_utc_midnight()
    dates = [
        today - timedelta(days=i)
        for i in range(num_days - 1, -1, -1)
    ]
    logger.info(
        f"📅 Fenêtre historique calculée : "
        f"{dates[0].date()} → {dates[-1].date()} ({num_days} jours)"
    )
    return dates


def get_era5_available_dates(num_days: int = DEFAULT_HISTORICAL_DAYS) -> List[datetime]:
    """
    Retourne les dates ERA5 réellement disponibles (compte tenu de la latence).

    ERA5 a une latence de 5 jours : la donnée la plus récente disponible
    aujourd'hui est celle de J-5. Donc on cherche l'intersection entre :
      - La fenêtre des N derniers jours
      - Les dates où ERA5 est publié

    Args:
        num_days: Nombre de jours d'historique souhaité (défaut 8).

    Returns:
        Liste de datetime tz-aware UTC, triée du plus ancien au plus récent.
        Peut être PLUS COURTE que num_days si ERA5 n'a pas encore tout publié.

    Exemple :
        Si aujourd'hui = 23 avril 2026, ERA5 dispo jusqu'à 18/04 (J-5).
        Pour num_days=8, on chercherait 16-23 avril, mais seuls
        16, 17, 18 avril sont disponibles → retourne 3 dates.
    """
    today = today_utc_midnight()

    # Fenêtre cible
    window_start = today - timedelta(days=num_days - 1)
    window_end = today

    # Dernière date ERA5 disponible
    last_era5 = today - timedelta(days=ERA5_LATENCY_DAYS)

    # Intersection : on prend de window_start jusqu'à min(window_end, last_era5)
    available_end = min(window_end, last_era5)

    if available_end < window_start:
        # Cas extrême : aucune date ERA5 dans la fenêtre
        logger.warning(
            f"⚠️ Aucune date ERA5 disponible dans la fenêtre "
            f"{window_start.date()} → {window_end.date()}"
        )
        return []

    # Construire la liste
    nb_dates = (available_end - window_start).days + 1
    dates = [
        window_start + timedelta(days=i)
        for i in range(nb_dates)
    ]
    logger.info(
        f"📅 Fenêtre ERA5 disponible : "
        f"{dates[0].date()} → {dates[-1].date()} "
        f"({len(dates)}/{num_days} jours, latence {ERA5_LATENCY_DAYS}j)"
    )
    return dates


# ───────────────────────────────────────────────────────────────────────────
# FONCTIONS DE RUNS — Calcul des moments de prévision
# ───────────────────────────────────────────────────────────────────────────

def get_runs_for_day(date: datetime) -> List[datetime]:
    """
    Retourne les datetime des runs pour un jour donné.

    En MVP v1.0 : 1 seul run/jour à 00h UTC.
    En v1.1 (futur) : 4 runs/jour (00h, 06h, 12h, 18h UTC).

    On code dès maintenant pour les 4 runs pour faciliter la transition,
    mais le script daily_*.py n'utilisera que le run 00h en v1.0.

    Args:
        date: Date pour laquelle on veut les runs (heure ignorée).

    Returns:
        Liste de datetime tz-aware UTC pour les heures de run de ce jour.

    Exemple :
        >>> get_runs_for_day(datetime(2026, 4, 23, tzinfo=timezone.utc))
        [datetime(2026, 4, 23, 0, ...), datetime(2026, 4, 23, 6, ...),
         datetime(2026, 4, 23, 12, ...), datetime(2026, 4, 23, 18, ...)]
    """
    # Normaliser à minuit UTC
    day_midnight = date.replace(hour=0, minute=0, second=0, microsecond=0)
    if day_midnight.tzinfo is None:
        day_midnight = day_midnight.replace(tzinfo=timezone.utc)

    return [
        day_midnight + timedelta(hours=h)
        for h in RUN_HOURS_UTC
    ]


def get_forecast_timestamps(run_datetime: datetime) -> List[Tuple[int, datetime]]:
    """
    Retourne les timestamps de validité pour un run donné.

    Pour 1 run, on a plusieurs prévisions à différents horizons (+6h, +12h,
    +18h, +24h en MVP v1.0). Cette fonction retourne ces couples
    (horizon_h, timestamp_validité).

    Args:
        run_datetime: Heure d'init du run (tz-aware UTC).

    Returns:
        Liste de tuples (horizon_h, timestamp) pour chaque prévision.

    Exemple :
        >>> run = datetime(2026, 4, 23, 0, tzinfo=timezone.utc)
        >>> get_forecast_timestamps(run)
        [(6,  datetime(2026, 4, 23, 6, ...)),
         (12, datetime(2026, 4, 23, 12, ...)),
         (18, datetime(2026, 4, 23, 18, ...)),
         (24, datetime(2026, 4, 24, 0, ...))]
    """
    if run_datetime.tzinfo is None:
        raise ValueError(
            "run_datetime doit être tz-aware. Utilise tzinfo=timezone.utc"
        )

    return [
        (h, run_datetime + timedelta(hours=h))
        for h in FORECAST_HORIZONS_H
    ]


# ───────────────────────────────────────────────────────────────────────────
# FONCTIONS DE FORMAT — Conversion pour APIs externes
# ───────────────────────────────────────────────────────────────────────────

def format_for_copernicus(dt: datetime) -> dict:
    """
    Formate une datetime UTC pour l'API Copernicus (cdsapi).

    Copernicus attend les dates dans un format dict spécifique pour
    les requêtes ERA5.

    Args:
        dt: datetime tz-aware UTC.

    Returns:
        Dict avec 'year', 'month', 'day', 'time' au format Copernicus.

    Exemple :
        >>> dt = datetime(2026, 4, 23, 6, 0, tzinfo=timezone.utc)
        >>> format_for_copernicus(dt)
        {'year': '2026', 'month': '04', 'day': '23', 'time': '06:00'}
    """
    if dt.tzinfo is None:
        raise ValueError("datetime doit être tz-aware UTC")

    # Convertir en UTC si autre timezone
    dt_utc = dt.astimezone(timezone.utc)

    return {
        'year':  str(dt_utc.year),
        'month': f'{dt_utc.month:02d}',
        'day':   f'{dt_utc.day:02d}',
        'time':  f'{dt_utc.hour:02d}:00',
    }


def format_iso_utc(dt: datetime) -> str:
    """
    Formate une datetime en chaîne ISO 8601 UTC stricte.

    Utile pour insérer en PostgreSQL ou loguer.

    Args:
        dt: datetime tz-aware (n'importe quelle timezone).

    Returns:
        Chaîne ISO 8601 en UTC, format '2026-04-23T18:00:00+00:00'

    Exemple :
        >>> format_iso_utc(datetime(2026, 4, 23, 18, tzinfo=timezone.utc))
        '2026-04-23T18:00:00+00:00'
    """
    if dt.tzinfo is None:
        raise ValueError("datetime doit être tz-aware")

    return dt.astimezone(timezone.utc).isoformat()


# ───────────────────────────────────────────────────────────────────────────
# FONCTION DE TEST STANDALONE
# ───────────────────────────────────────────────────────────────────────────

def test_date_utils() -> None:
    """
    Affiche un récap de tous les calculs de dates pour vérification visuelle.

    Lance avec :
        $ python -m utils.date_utils
    """
    print("\n" + "═" * 70)
    print("  TEST DE date_utils.py — RÉCAPITULATIF DES DATES")
    print("═" * 70)

    # Test 1 : maintenant
    print(f"\n📍 Instant présent (UTC) : {now_utc()}")
    print(f"📍 Aujourd'hui 00h UTC   : {today_utc_midnight()}")

    # Test 2 : fenêtre historique 8 jours
    print(f"\n📅 Fenêtre historique 8 jours (AROME, GraphCast) :")
    for d in get_historical_dates(num_days=8):
        print(f"   • {d.strftime('%A %d %B %Y')} ({d.isoformat()})")

    # Test 3 : fenêtre ERA5 disponible
    print(f"\n📅 Fenêtre ERA5 disponible (latence 5j) :")
    era5_dates = get_era5_available_dates(num_days=8)
    if era5_dates:
        for d in era5_dates:
            print(f"   • {d.strftime('%A %d %B %Y')} ({d.isoformat()})")
    else:
        print("   ⚠️ Aucune date ERA5 disponible")

    # Test 4 : runs pour aujourd'hui
    today = today_utc_midnight()
    print(f"\n⏰ Runs pour aujourd'hui ({today.date()}) :")
    for r in get_runs_for_day(today):
        print(f"   • {r.strftime('%H:%M UTC')}")

    # Test 5 : timestamps de prévision pour le run 00h
    run_00 = today.replace(hour=0)
    print(f"\n🔮 Prévisions pour le run 00h UTC ({today.date()}) :")
    for horizon, ts in get_forecast_timestamps(run_00):
        print(f"   • +{horizon:>2d}h → {ts.isoformat()}")

    # Test 6 : format Copernicus
    print(f"\n📡 Format Copernicus pour le run 00h UTC :")
    cop = format_for_copernicus(run_00)
    print(f"   {cop}")

    # Test 7 : format ISO UTC
    print(f"\n🔤 Format ISO UTC :")
    print(f"   {format_iso_utc(run_00)}")

    print("\n" + "═" * 70 + "\n")


# ───────────────────────────────────────────────────────────────────────────
# Point d'entrée pour exécution directe (test)
# ───────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
    )
    test_date_utils()
