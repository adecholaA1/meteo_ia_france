"""
═══════════════════════════════════════════════════════════════════════
 Régénération automatique du JSON statique frontend
   À appeler à la fin de chaque run_daily_pipeline (arome/era5/graphcast/mae).

 🆕 PHASE B.6 :
   En plus de régénérer le JSON statique, ce hook :
   1. Invalide le cache RAM du backend Express (POST /cache/clear)
   2. Pré-réchauffe le cache (3 GET sur /available-times)
   → Garantit que les utilisateurs ne paient JAMAIS la latence de 6-9s
      qui arrive quand le cache est vide.

 Le helper est tolérant aux pannes : si le backend Express ou Node n'est
 pas disponible, il log l'erreur mais ne fait PAS échouer le pipeline.
═══════════════════════════════════════════════════════════════════════
"""
import logging
import os
import subprocess
from pathlib import Path

# ⚠️ urllib est dans la stdlib Python, pas besoin d'installer requests
from urllib import request as urllib_request
from urllib.error import URLError

logger = logging.getLogger(__name__)

# Racine du projet (3 niveaux au-dessus de ce fichier)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
SCRIPT_PATH = FRONTEND_DIR / "scripts" / "generate_static_data.mjs"

# 🆕 PHASE B.6 — URL du backend Express
# Configurable via variable d'env BACKEND_URL (défaut : localhost:3001)
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:3001")
HTTP_TIMEOUT_SECONDS = 30  # 30s max pour le pre-warming (qui peut prendre ~9s)


def regenerate_frontend_json() -> bool:
    """
    Régénère public/data/sample_forecast.json en appelant le script Node,
    puis invalide + pré-réchauffe le cache backend.

    Returns:
        True si la régénération a réussi, False sinon.
        L'invalidation/pre-warming sont tolérants aux pannes (warning seulement).
    """
    if not SCRIPT_PATH.exists():
        logger.warning(f"Script de régénération introuvable : {SCRIPT_PATH}")
        return False

    logger.info("🔄 Régénération du JSON statique frontend...")

    try:
        result = subprocess.run(
            ["node", str(SCRIPT_PATH)],
            cwd=str(FRONTEND_DIR),
            capture_output=True,
            text=True,
            timeout=60,  # 60s max
        )

        if result.returncode == 0:
            logger.info("✅ JSON statique régénéré avec succès")
            # 🆕 PHASE B.6 : invalidation + pre-warming du cache backend
            invalidate_and_prewarm_backend_cache()
            return True
        else:
            logger.error(
                f"❌ Échec régénération JSON (code {result.returncode})\n"
                f"   stderr: {result.stderr[:500]}"
            )
            return False

    except subprocess.TimeoutExpired:
        logger.error("⏱️  Timeout pendant la régénération JSON (>60s)")
        return False
    except FileNotFoundError:
        logger.warning(
            "⚠️  Node.js introuvable. La régénération JSON est ignorée. "
            "Installer Node ou ignorer si le frontend n'est pas utilisé."
        )
        return False
    except Exception as e:
        logger.error(f"❌ Erreur inattendue régénération JSON : {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# 🆕 PHASE B.6 — Invalidation et pre-warming du cache backend
# ═══════════════════════════════════════════════════════════════════════════

def invalidate_and_prewarm_backend_cache() -> None:
    """
    Invalide le cache backend Express puis le pré-réchauffe avec les 3 sources.

    Étapes :
        1. POST /api/forecast/cache/clear   → vide le cache RAM
        2. GET  /api/forecast/available-times?source=arome     → remplit
        3. GET  /api/forecast/available-times?source=graphcast → remplit
        4. GET  /api/forecast/available-times?source=era5      → remplit

    → Après ce hook, les 3 sources sont en cache pour 1h, garantissant
       une latence < 50ms pour TOUS les utilisateurs.

    Tolérant aux pannes : si le backend n'est pas démarré ou inaccessible,
    on log un warning sans faire échouer le pipeline.
    """
    logger.info("🔄 Invalidation + pre-warming du cache backend...")

    # ── 1. Invalidation du cache ──────────────────────────────────────────
    try:
        clear_url = f"{BACKEND_URL}/api/forecast/cache/clear"
        req = urllib_request.Request(clear_url, method="POST")
        with urllib_request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as response:
            if response.status == 200:
                logger.info("   ✅ Cache backend invalidé")
            else:
                logger.warning(f"   ⚠️  Réponse inattendue (HTTP {response.status})")
                return  # On ne pre-warm pas si l'invalidation a échoué
    except URLError as e:
        logger.warning(
            f"   ⚠️  Backend inaccessible ({BACKEND_URL}) : {e}\n"
            f"      Cache non invalidé. Le backend doit être démarré pour que "
            f"l'invalidation soit effective."
        )
        return  # On ne pre-warm pas si l'invalidation a échoué
    except Exception as e:
        logger.warning(f"   ⚠️  Erreur invalidation cache : {e}")
        return

    # ── 2. Pre-warming (3 sources) ────────────────────────────────────────
    sources = ["arome", "graphcast", "era5"]
    success_count = 0
    for source in sources:
        try:
            warm_url = f"{BACKEND_URL}/api/forecast/available-times?source={source}"
            with urllib_request.urlopen(warm_url, timeout=HTTP_TIMEOUT_SECONDS) as response:
                if response.status == 200:
                    success_count += 1
                else:
                    logger.warning(
                        f"   ⚠️  Pre-warming {source} : HTTP {response.status}"
                    )
        except Exception as e:
            logger.warning(f"   ⚠️  Pre-warming {source} : {e}")

    if success_count == len(sources):
        logger.info(
            f"   ✅ Cache pré-réchauffé pour les {success_count} sources "
            f"(arome, graphcast, era5)"
        )
    else:
        logger.warning(
            f"   ⚠️  Pre-warming partiel : {success_count}/{len(sources)} sources OK"
        )


if __name__ == "__main__":
    # Test direct : `python scripts/utils/regenerate_frontend_json.py`
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    success = regenerate_frontend_json()
    exit(0 if success else 1)
