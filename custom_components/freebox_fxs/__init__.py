import logging
import hmac
import hashlib
import aiohttp
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

DOMAIN = "freebox_fxs_ring"

BASE_URL = "http://mafreebox.freebox.fr/api/latest"
URL_LOGIN = f"{BASE_URL}/login/"
URL_RING_START = f"{BASE_URL}/phone/fxs_ring_start/"
URL_RING_STOP = f"{BASE_URL}/phone/fxs_ring_stop/"

# Identifiants de l'application déclarée auprès de la Freebox
APP_ID = "ha.freebox.fxs.ring"
APP_NAME = "Freebox FXS Ring Controller"
APP_VERSION = "1.0.0"
DEVICE_NAME = "Home Assistant"

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Initialisation du composant avec authentification Freebox OS."""
    session = async_get_clientsession(hass)

    async def get_session_token() -> str:
        """Gère le challenge de connexion et retourne le token de session valide."""
        try:
            # 1. Obtenir le challenge de connexion
            async with session.get(URL_LOGIN, timeout=5) as resp:
                if resp.status != 200:
                    return ""
                data = await resp.json()
                
            if not data.get("success"):
                return ""

            result = data.get("result", {})
            challenge = result.get("challenge")
            logged_in = result.get("logged_in", False)

            # Si déjà connecté, on peut récupérer le token d'app stocké ou en demander un nouveau
            # Pour un usage simplifié, on passe par l'authentification par token d'application stocké localement ou en clair
            app_token = config.get("app_token", "")
            if not app_token:
                _LOGGER.warning("Aucun token d'application Freebox configuré. Veuillez autoriser l'app sur la Freebox.")
                return ""

            # 2. Calculer la signature HMAC-SHA1
            password = hmac.new(
                app_token.encode("utf-8"),
                challenge.encode("utf-8"),
                hashlib.sha1
            ).hexdigest()

            # 3. Demander l'ouverture de session
            payload = {
                "app_id": APP_ID,
                "password": password
            }

            async with session.post(f"{URL_LOGIN}session/", json=payload, timeout=5) as login_resp:
                login_data = await login_resp.json()
                if login_data.get("success"):
                    return login_data["result"].get("session_token")
                else:
                    _LOGGER.error("Échec de l'authentification Freebox : %s", login_data)

        except Exception as err:
            _LOGGER.error("Erreur lors de la session d'authentification Freebox : %s", err)
        
        return ""

    async def send_freebox_command(url: str, service_name: str):
        """Envoie la requête POST signée avec le token de session."""
        session_token = await get_session_token()
        if not session_token:
            _LOGGER.error("Impossible d'exécuter %s : Session Freebox non authentifiée.", service_name)
            return

        headers = {
            "X-Fbx-App-Auth": session_token
        }

        try:
            async with session.post(url, headers=headers, timeout=5) as resp:
                result_data = await resp.json()
                if resp.status == 200 and result_data.get("success", False):
                    _LOGGER.info("Commande Freebox FXS (%s) exécutée avec succès.", service_name)
                else:
                    _LOGGER.error(
                        "Erreur Freebox (%s) - Statut: %s, Réponse: %s",
                        service_name,
                        resp.status,
                        result_data,
                    )
        except Exception as err:
            _LOGGER.error("Erreur réseau lors de l'appel (%s) : %s", service_name, err)

    async def handle_ring_start(call: ServiceCall):
        await send_freebox_command(URL_RING_START, "ring_start")

    async def handle_ring_stop(call: ServiceCall):
        await send_freebox_command(URL_RING_STOP, "ring_stop")

    hass.services.async_register(DOMAIN, "ring_start", handle_ring_start)
    hass.services.async_register(DOMAIN, "ring_stop", handle_ring_stop)

    return True