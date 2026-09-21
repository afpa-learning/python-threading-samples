from mcp.server import MCPServer
import httpx, json, os, logging
from datetime import datetime
from geopy.geocoders import Nominatim
from logging.handlers import RotatingFileHandler

# ─── Configuration du logging ────────────────────────────────────────
LOG_DIR = os.getenv("APP_LOG_DIR", "project_root_path\\log")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("serveur-meteo")
logger.setLevel(logging.INFO)

_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, '{:%Y-%m-%d}-serveur-meteo.log'.format(datetime.now())),
    maxBytes=5_000_000,
    backupCount=5,
    encoding="utf-8",
)
_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
))
logger.addHandler(_handler)

# Important : ne PAS logger sur stdout quand le transport est stdio.
# FastMCP utilise stdout pour le protocole JSON-RPC ; tout print()
# ou handler console y écrirait et casserait la communication avec
# le client (Claude Desktop, etc.). Le fichier seul est sûr.


# Création du serveur
mcp = MCPServer("serveur-meteo", version="1.0.0")

# ─── Géocodage : ville -> coordonnées ────────────────────────────────
async def _geocode(city: str) -> dict:
    # Create a geolocator instance
    geolocator = Nominatim(user_agent="geoapi")
    
    # Get location details from an address
    location = geolocator.geocode(city)

    return {
        "latitude": location.latitude,
        "longitude": location.longitude,
    }


# ─── TOOL : action exécutable ────────────────────────────────────────
@mcp.tool()
async def get_weather(city: str, unit: str = "celsius") -> dict:
    """Récupère la météo actuelle pour une ville donnée.

    Args:
        city: Nom de la ville (ex: "Paris", "Tokyo")
        unit: Unité de température - "celsius" ou "fahrenheit"
    """
    logger.info("get_weather appelé | city=%r unit=%r", city, unit)

    async with httpx.AsyncClient() as client:
        location = await _geocode(city)
        resp = await client.get(
            f"https://api.open-meteo.com/v1/forecast",
            params={"latitude": location["latitude"], "longitude": location["longitude"],
                    "current_weather": True}
        )
        data = resp.json()
    temp = data["current_weather"]["temperature"]
    if unit == "fahrenheit":
        temp = temp * 9/5 + 32
    return {"city": city, "temperature": temp,
            "unit": unit, "timestamp": datetime.now().isoformat()}

# ─── RESOURCE : données en lecture ───────────────────────────────────
@mcp.resource("config://app-settings")
def get_app_settings() -> str:
    """Retourne la configuration courante de l'application."""
    return json.dumps({
        "version": "2.1.0",
        "env": os.getenv("APP_ENV", "production"),
        "features": ["mcp", "agents", "rag"]
    }, indent=2)

# ─── RESOURCE dynamique (pattern URI) ────────────────────────────────
@mcp.resource("logs://{date}/errors")
def get_error_logs(date: str) -> str:
    """Retourne les logs d'erreurs pour une date donnée (YYYY-MM-DD)."""
    log_path = os.path.join(LOG_DIR, "{date}-serveur-meteo.log")
    if not os.path.exists(log_path):
        return f"Aucun log pour le {date}"
    with open(log_path) as f:
        return f.read()

# ─── PROMPT : template réutilisable ──────────────────────────────────
@mcp.prompt()
def analyse_logs(date: str, niveau: str = "ERROR") -> str:
    """Template pour analyser les logs d'une journée."""
    return (f"Analyse les logs du {date} de niveau {niveau}. "
            "Identifie les patterns récurrents, les pics d'erreurs, "
            "et propose des corrections prioritaires.")

# ─── Lancement ────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()  # stdio par défaut — compatible Claude Desktop