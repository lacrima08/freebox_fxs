import logging
import aiohttp
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

DOMAIN = "freebox_fxs"

URL_RING_START = "http://mafreebox.freebox.fr/api/latest/phone/fxs_ring_start/"
URL_RING_STOP = "http://mafreebox.freebox.fr/api/latest/phone/fxs_ring_stop/"

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Initialisation du composant Freebox FXS Ring."""
    session = async_get_clientsession(hass)

    async def handle_ring_start(call: ServiceCall):
        """Service pour démarrer la sonnerie FXS."""
        try:
            async with session.post(URL_RING_START, timeout=5) as resp:
                if resp.status == 200:
                    _LOGGER.info("Sonnerie FXS démarrée avec succès.")
                else:
                    _LOGGER.error("Échec du démarrage de la sonnerie FXS : %s", resp.status)
        except Exception as err:
            _LOGGER.error("Erreur de connexion à la Freebox (ring_start) : %s", err)

    async def handle_ring_stop(call: ServiceCall):
        """Service pour arrêter la sonnerie FXS."""
        try:
            async with session.post(URL_RING_STOP, timeout=5) as resp:
                if resp.status == 200:
                    _LOGGER.info("Sonnerie FXS arrêtée avec succès.")
                else:
                    _LOGGER.error("Échec de l'arrêt de la sonnerie FXS : %s", resp.status)
        except Exception as err:
            _LOGGER.error("Erreur de connexion à la Freebox (ring_stop) : %s", err)

    hass.services.async_register(DOMAIN, "ring_start", handle_ring_start)
    hass.services.async_register(DOMAIN, "ring_stop", handle_ring_stop)

    return True
