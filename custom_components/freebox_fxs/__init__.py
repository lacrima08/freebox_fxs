import logging
import aiohttp
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

DOMAIN = "freebox_fxs_ring"

# URL de base de la Freebox (modifiable si besoin)
BASE_URL = "http://mafreebox.freebox.fr/api/latest"
URL_RING_START = f"{BASE_URL}/phone/fxs_ring_start/"
URL_RING_STOP = f"{BASE_URL}/phone/fxs_ring_stop/"
URL_LOGIN = f"{BASE_URL}/login/"

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Initialisation du composant minimaliste de sonnerie FXS."""
    session = async_get_clientsession(hass)

    async def get_auth_token() -> str:
        """Récupère un token de session valide auprès de l'API Freebox."""
        try:
            async with session.get(URL_LOGIN, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Si un token de session est requis par la Freebox
                    if "result" in data and "logged_in" in data["result"] and data["result"]["logged_in"]:
                        return resp.headers.get("X-Fbx-App-Auth", "")
        except Exception as err:
            _LOGGER.debug("Impossible de récupérer le token de session Freebox (mode libre ou direct) : %s", err)
        return ""

    async def send_freebox_command(url: str, service_name: str):
        """Envoie la requête POST authentifiée vers l'API Freebox."""
        headers = {}
        token = await get_auth_token()
        if token:
            headers["X-Fbx-App-Auth"] = token

        try:
            async with session.post(url, headers=headers, timeout=5) as resp:
                result_data = await resp.json()
                if resp.status == 200 and result_data.get("success", False):
                    _LOGGER.info("Commande Freebox FXS (%s) exécutée avec succès.", service_name)
                else:
                    _LOGGER.error(
                        "Erreur lors de l'appel Freebox (%s) - Statut HTTP: %s, Réponse: %s",
                        service_name,
                        resp.status,
                        result_data,
                    )
        except Exception as err:
            _LOGGER.error("Erreur de communication réseau avec la Freebox (%s) : %s", service_name, err)

    async def handle_ring_start(call: ServiceCall):
        """Service Home Assistant: démarrer la sonnerie."""
        await send_freebox_command(URL_RING_START, "ring_start")

    async def handle_ring_stop(call: ServiceCall):
        """Service Home Assistant: arrêter la sonnerie."""
        await send_freebox_command(URL_RING_STOP, "ring_stop")

    # Enregistrement des services
    hass.services.async_register(DOMAIN, "ring_start", handle_ring_start)
    hass.services.async_register(DOMAIN, "ring_stop", handle_ring_stop)

    _LOGGER.info("Intégration Freebox FXS Ring initialisée avec succès.")
    return True