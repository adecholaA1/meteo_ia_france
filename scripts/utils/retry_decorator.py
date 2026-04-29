"""
═══════════════════════════════════════════════════════════════════════════
PROJET   : Plateforme de Prévision Météo IA pour l'Énergie — France
ÉTAPE    : 7 — Ingestion des données en PostgreSQL
FICHIER  : utils/retry_decorator.py
RÔLE     : Retry automatique des fonctions qui échouent (APIs externes)
═══════════════════════════════════════════════════════════════════════════

POURQUOI CE FICHIER ?
---------------------
Les APIs externes (Copernicus, Météo-France) peuvent échouer ponctuellement :
  • Surcharge serveur (HTTP 503)
  • Timeout réseau
  • Maintenance programmée

Au lieu de planter le script au premier échec, on RÉESSAIE 3 fois avec
30 minutes d'intervalle. Si tout échoue, on logue l'erreur et on lève une
exception.

RÈGLE D'OR
----------
On ne réessaie QUE SI l'appel ÉCHOUE.
Si l'appel réussit du premier coup → on continue immédiatement (pas d'attente).

INSPIRATION
-----------
Ton script fetch_rte_data.py utilise cette même logique avec un boucle
for + try/except dans le main(). Ici on factorise dans un DÉCORATEUR
réutilisable, plus élégant et maintenable.

UTILISATION
-----------
    from utils.retry_decorator import retry_on_failure

    @retry_on_failure()  # Valeurs par défaut : 3 essais × 30 min
    def download_era5(date):
        # ... code qui peut échouer ...
        return data

    # Personnalisation possible :
    @retry_on_failure(max_attempts=5, delay_seconds=60)
    def quick_retry_function():
        ...

    # Usage normal :
    data = download_era5(some_date)
    # → Si succès au 1er essai : retourne immédiatement
    # → Si échec : attend 30 min, réessaie. Jusqu'à 3 fois max.
    # → Si tout échoue : lève l'exception originale
═══════════════════════════════════════════════════════════════════════════
"""

import time
import logging
import functools
from typing import Callable, Type, Tuple, Any


# ───────────────────────────────────────────────────────────────────────────
# Configuration du logger pour ce module
# ───────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# CONSTANTES PAR DÉFAUT
# ───────────────────────────────────────────────────────────────────────────

# Nombre maximum de tentatives (essai initial + retries)
DEFAULT_MAX_ATTEMPTS = 3

# Délai entre 2 tentatives (en secondes)
# 30 minutes = 1800 secondes
DEFAULT_DELAY_SECONDS = 30 * 60


# ───────────────────────────────────────────────────────────────────────────
# DÉCORATEUR PRINCIPAL
# ───────────────────────────────────────────────────────────────────────────

def retry_on_failure(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    delay_seconds: int = DEFAULT_DELAY_SECONDS,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable:
    """
    Décorateur qui réessaie une fonction en cas d'échec.

    Args:
        max_attempts:  Nombre TOTAL de tentatives (par défaut 3).
                       Inclut l'essai initial + les retries.
        delay_seconds: Délai entre 2 tentatives en secondes (défaut 1800 = 30min).
        exceptions:    Tuple des types d'exceptions à intercepter (défaut Exception).
                       Permet de ne pas retry sur certaines erreurs spécifiques.

    Returns:
        Callable : la fonction décorée avec logique de retry.

    Comportement :
        • Essai 1 → succès      : retourne le résultat
        • Essai 1 → échec       : attend delay_seconds, essai 2
        • Essai 2 → succès      : retourne le résultat
        • Essai 2 → échec       : attend delay_seconds, essai 3
        • Essai 3 → succès      : retourne le résultat
        • Essai 3 → échec       : lève l'exception originale

    Exemple basique :
        >>> @retry_on_failure()
        ... def fetch_data():
        ...     response = requests.get('https://api.example.com')
        ...     response.raise_for_status()
        ...     return response.json()

    Exemple avec personnalisation :
        >>> @retry_on_failure(
        ...     max_attempts=5,
        ...     delay_seconds=60,  # 1 minute entre essais
        ...     exceptions=(ConnectionError, TimeoutError),  # Pas tous les erreurs
        ... )
        ... def fetch_arome(date):
        ...     ...
    """

    def decorator(func: Callable) -> Callable:

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:

            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    # ───── TENTATIVE D'EXÉCUTION ─────
                    if attempt > 1:
                        logger.info(
                            f"🔁 [{func.__name__}] Tentative {attempt}/{max_attempts}..."
                        )

                    result = func(*args, **kwargs)

                    # ───── SUCCÈS : on retourne ─────
                    if attempt > 1:
                        logger.info(
                            f"✓ [{func.__name__}] Succès à la tentative {attempt}"
                        )
                    return result

                except exceptions as e:
                    last_exception = e

                    # ───── ÉCHEC : on logue ─────
                    logger.error(
                        f"✗ [{func.__name__}] Échec tentative {attempt}/{max_attempts} : {e}"
                    )

                    # ───── DERNIÈRE TENTATIVE : on lève l'exception ─────
                    if attempt == max_attempts:
                        logger.error(
                            f"✗ [{func.__name__}] TOUTES les tentatives ont échoué "
                            f"({max_attempts}). Abandon."
                        )
                        raise

                    # ───── AUTRE TENTATIVE À VENIR : on attend ─────
                    delay_min = delay_seconds // 60
                    logger.info(
                        f"⏳ [{func.__name__}] Nouvelle tentative dans "
                        f"{delay_min} min ({delay_seconds} sec)..."
                    )
                    time.sleep(delay_seconds)

            # Ne devrait jamais arriver (la boucle ci-dessus retourne ou raise)
            # mais par sécurité :
            raise last_exception

        return wrapper

    return decorator


# ───────────────────────────────────────────────────────────────────────────
# DÉCORATEUR DE TEST RAPIDE (pour valider en dev sans attendre 30 min)
# ───────────────────────────────────────────────────────────────────────────

def retry_quick(max_attempts: int = 3, delay_seconds: int = 2) -> Callable:
    """
    Variante du décorateur retry pour les TESTS UNIQUEMENT.

    Délai par défaut très court (2 secondes) pour vérifier la mécanique
    sans attendre 30 minutes.

    À NE PAS utiliser en production !

    Exemple :
        >>> @retry_quick(max_attempts=3, delay_seconds=1)
        ... def test_function():
        ...     raise Exception("Test")
        >>>
        >>> test_function()  # Va essayer 3 fois avec 1 sec entre chaque
    """
    return retry_on_failure(
        max_attempts=max_attempts,
        delay_seconds=delay_seconds,
    )


# ───────────────────────────────────────────────────────────────────────────
# FONCTION DE TEST STANDALONE
# ───────────────────────────────────────────────────────────────────────────

def test_retry_decorator() -> None:
    """
    Démontre le fonctionnement du décorateur avec 3 cas concrets.

    Lance avec :
        $ python -m utils.retry_decorator
    """
    print("\n" + "═" * 70)
    print("  TEST DU DÉCORATEUR retry_on_failure")
    print("═" * 70)

    # ───── CAS 1 : succès au premier essai (pas de retry) ─────
    print("\n📍 CAS 1 : succès immédiat (pas de retry attendu)")
    print("─" * 70)

    @retry_quick(max_attempts=3, delay_seconds=1)
    def succeed_immediately() -> str:
        return "✓ Réussi du premier coup !"

    result = succeed_immediately()
    print(f"  Résultat : {result}")

    # ───── CAS 2 : échec puis succès au 2e essai ─────
    print("\n📍 CAS 2 : échec puis succès au 2e essai")
    print("─" * 70)

    attempt_counter = {"n": 0}

    @retry_quick(max_attempts=3, delay_seconds=1)
    def fail_then_succeed() -> str:
        attempt_counter["n"] += 1
        if attempt_counter["n"] < 2:
            raise ConnectionError("Simulation : API indisponible")
        return f"✓ Réussi à la tentative {attempt_counter['n']}"

    result = fail_then_succeed()
    print(f"  Résultat : {result}")

    # ───── CAS 3 : échec à toutes les tentatives ─────
    print("\n📍 CAS 3 : échec à toutes les tentatives (3/3 échecs)")
    print("─" * 70)

    @retry_quick(max_attempts=3, delay_seconds=1)
    def always_fail() -> None:
        raise TimeoutError("Simulation : timeout")

    try:
        always_fail()
    except TimeoutError as e:
        print(f"  Exception finale levée : {type(e).__name__} : {e}")

    print("\n" + "═" * 70)
    print("  ✓ TOUS LES TESTS SONT PASSÉS")
    print("═" * 70 + "\n")


# ───────────────────────────────────────────────────────────────────────────
# Point d'entrée pour exécution directe (test)
# ───────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
    )
    test_retry_decorator()
