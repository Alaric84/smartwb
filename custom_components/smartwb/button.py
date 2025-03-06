from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import asyncio
import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up SmartWB button based on config entry."""
    ip = config_entry.data['ip_address']
    port = config_entry.data['port']
    device_name = config_entry.data['name']
    unique_id = config_entry.unique_id

    button = SmartWBInterruptButton(hass, f"{device_name}_interrupt", ip, port, config_entry.entry_id, unique_id, device_name)
    async_add_entities([button], True)

class SmartWBInterruptButton(ButtonEntity):
    """Button to interrupt the contact."""

    def __init__(self, hass, name, ip, port, entry_id, unique_id, device_name):
        """Initialize the button."""
        self.hass = hass
        self._name = name
        self._ip = ip
        self._port = port
        self._available = True
        self._attr_unique_id = f"{unique_id}_interrupt"
        self._entry_id = entry_id
        self._device_name = device_name
        self._unique_id = unique_id
        self._attr_icon = "mdi:stop-circle-outline"

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._unique_id)},
            "name": self._device_name,
            "manufacturer": "SmartWB",
            "model": "SimpleEVSE-WiFi",
        }

    @property
    def name(self):
        """Return the name of the button."""
        return self._name

    async def async_press(self) -> None:
        """Handle the button press."""
        url = f"http://{self._ip}:{self._port}/interruptCp"
        try:
            session = async_get_clientsession(self.hass)
            async with asyncio.timeout(10):
                async with session.get(url) as response:
                    response_text = await response.text()
                    if response_text.startswith("S0_"):
                        if "interrupted" in response_text.lower():
                            _LOGGER.info(f"SmartWB successfully interrupted: {response_text}")
                        else:
                            _LOGGER.info(f"SmartWB command successful, but state unclear: {response_text}")
                        self._available = True
                    elif response_text.startswith("E0_"):
                        _LOGGER.error(f"Internal error: {response_text}")
                        self._available = False
                    elif response_text.startswith("E1_"):
                        _LOGGER.error(f"Invalid value error: {response_text}")
                    elif response_text.startswith("E2_"):
                        _LOGGER.error(f"Wrong parameter error: {response_text}")
                    elif response_text.startswith("E3_"):
                        _LOGGER.warning(f"SmartWB interrupt state unchanged: {response_text}")
                    else:
                        _LOGGER.error(f"Unexpected response: {response_text}")
                        self._available = False
        except asyncio.TimeoutError:
            self._available = False
            _LOGGER.error("Timeout error sending interrupt command to %s", url)
        except Exception as e:
            self._available = False
            _LOGGER.error("Error sending interrupt command to %s: %s", url, str(e))
