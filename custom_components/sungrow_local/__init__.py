"""Sungrow local polling integration."""
import logging
from datetime import timedelta

from homeassistant.const import Platform
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import SungrowError, read_snapshot
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


class SungrowCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=entry.title, config_entry=entry,
                         update_interval=timedelta(seconds=SCAN_INTERVAL))
        self.entry = entry

    async def _async_update_data(self):
        try:
            return await read_snapshot(self.entry.data["host"], self.entry.data["serial"],
                                       self.entry.data.get("smart_meter", False))
        except SungrowError as err:
            raise UpdateFailed(str(err)) from err


async def async_setup_entry(hass, entry):
    coordinator = SungrowCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    coordinator.device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.data["serial"])},
        name=entry.title, manufacturer="SUNGROW", model="SG5K-D", serial_number=entry.data["serial"],
    )
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
