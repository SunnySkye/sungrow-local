"""Connection health without retaining an online state after communication fails."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .sensor import inverter_device


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SungrowConnection(entry.runtime_data)])


class SungrowConnection(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.data['serial']}_connection"
        self._attr_device_info = inverter_device(coordinator.entry)

    @property
    def available(self):
        return True

    @property
    def is_on(self):
        return self.coordinator.last_update_success
