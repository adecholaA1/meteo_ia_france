"""
═══════════════════════════════════════════════════════════════════════
 Configuration centralisée du logging pour les pipelines.

 Configure :
   - Console (stdout)        : pour suivre en direct dans le terminal
   - Fichier logs/<source>.log : append à chaque run
                                 (historique cumulatif sur la durée)

 Usage dans un pipeline :
   from utils.logging_setup import setup_pipeline_logging
   setup_pipeline_logging("arome")  # crée logs/arome.log

 Le dossier `logs/` est créé automatiquement à la racine du projet
 (au même niveau que `scripts/`).
═══════════════════════════════════════════════════════════════════════
"""
import logging
import sys
from pathlib import Path

# Racine du projet (2 niveaux au-dessus de ce fichier)
# Ce fichier : meteo_ia_france/scripts/utils/logging_setup.py
# .parents[0] = utils/
# .parents[1] = scripts/
# .parents[2] = meteo_ia_france/  ← racine
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = PROJECT_ROOT / "logs"


def setup_pipeline_logging(source_name: str) -> logging.Logger:
    """
    Configure le logging pour un pipeline (console + fichier).

    Args:
        source_name: nom de la source ('arome', 'era5', 'graphcast', 'mae').
                     Détermine le nom du fichier log : logs/<source_name>.log

    Returns:
        Le root logger configuré (pour info, généralement pas nécessaire
        car logging.getLogger(__name__) suffit dans les modules).

    Comportement :
        - Le dossier `logs/` est créé s'il n'existe pas.
        - Le fichier `logs/<source_name>.log` est ouvert en mode APPEND :
          les nouveaux runs s'ajoutent à la suite, sans écraser l'historique.
        - Format identique pour console et fichier.
    """
    # 1. Créer le dossier logs/ s'il n'existe pas
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Chemin du fichier log
    log_file = LOGS_DIR / f"{source_name}.log"

    # 3. Format identique pour console et fichier
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # 4. Récupérer le root logger et le configurer
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 5. ⚠️ Important : retirer les handlers existants pour éviter les doublons
    #    (cas où le pipeline est ré-importé dans un même processus, tests, etc.)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 6. Handler console (stdout) — pour voir en direct dans le terminal
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 7. Handler fichier (mode 'a' = append) — pour persister l'historique
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 8. Petit log d'amorçage pour signaler le début d'un nouveau run
    #    Ça permet de visualiser facilement les "frontières" entre runs dans le fichier
    root_logger.info("=" * 76)
    root_logger.info(f"🚀 Nouveau run de pipeline : {source_name.upper()}")
    root_logger.info(f"   Fichier log : {log_file}")
    root_logger.info("=" * 76)

    return root_logger


if __name__ == "__main__":
    # Test direct : `python scripts/utils/logging_setup.py`
    logger = setup_pipeline_logging("test")
    logger.info("Test info")
    logger.warning("Test warning")
    logger.error("Test error")
    print(f"\n✅ Test OK. Vérifie : {LOGS_DIR}/test.log")
