"""Inverter and separate smart meter entities."""
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


def description(key, name, unit=None, device_class=None, state_class=SensorStateClass.MEASUREMENT):
    return SensorEntityDescription(key=key, name=name, native_unit_of_measurement=unit,
                                   device_class=device_class, state_class=state_class)


INVERTER_SENSORS = (
    description("generation_w", "Generation power", "W", SensorDeviceClass.POWER),
    description("daily_generation_kwh", "Generation today", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    description("total_generation_kwh", "Lifetime generation", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    description("temperature_c", "Internal temperature", "°C", SensorDeviceClass.TEMPERATURE),
    description("grid_voltage_v", "Grid voltage", "V", SensorDeviceClass.VOLTAGE),
    description("dc_power_w", "DC power", "W", SensorDeviceClass.POWER),
    description("mppt_1_voltage_v", "MPPT 1 voltage", "V", SensorDeviceClass.VOLTAGE),
    description("mppt_1_current_a", "MPPT 1 current", "A", SensorDeviceClass.CURRENT),
    description("mppt_2_voltage_v", "MPPT 2 voltage", "V", SensorDeviceClass.VOLTAGE),
    description("mppt_2_current_a", "MPPT 2 current", "A", SensorDeviceClass.CURRENT),
    description("grid_frequency_hz", "Grid frequency", "Hz", SensorDeviceClass.FREQUENCY),
    # Register 5035 is a signed ratio, not a percentage.
    description("power_factor", "Power factor", state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="last_updated", name="Last updated", device_class=SensorDeviceClass.TIMESTAMP,
                            entity_category=EntityCategory.DIAGNOSTIC),
)
METER_SENSORS = (
    description("grid_power_w", "Grid power", "W", SensorDeviceClass.POWER),
    description("grid_import_w", "Grid import power", "W", SensorDeviceClass.POWER),
    description("grid_export_w", "Grid export power", "W", SensorDeviceClass.POWER),
    description("daily_import_kwh", "Grid import today", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    description("daily_export_kwh", "Grid export today", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    description("total_import_kwh", "Lifetime grid import", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    description("total_export_kwh", "Lifetime grid export", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
)


def inverter_device(entry):
    return DeviceInfo(identifiers={(DOMAIN, entry.data["serial"])}, name=entry.title,
                      manufacturer="SUNGROW", model="SG5K-D", serial_number=entry.data["serial"])


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    entities = [SungrowSensor(coordinator, item) for item in INVERTER_SENSORS]
    if entry.data.get("smart_meter"):
        entities.extend(SungrowSensor(coordinator, item, meter=True) for item in METER_SENSORS)
    async_add_entities(entities)


class SungrowSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, item, meter=False):
        super().__init__(coordinator)
        self.entity_description = item
        self._meter = meter
        entry = coordinator.entry
        serial = entry.data["serial"]
        self._attr_unique_id = f"{serial}_{item.key}"
        self._attr_device_info = inverter_device(entry) if not meter else DeviceInfo(
            identifiers={(DOMAIN, f"{serial}_meter")}, name="Sungrow Smart Meter",
            manufacturer="SUNGROW", model="SG Smart Meter", via_device_id=coordinator.device.id,
        )

    @property
    def available(self):
        return super().available and (not self._meter or self.coordinator.data.get("meter_available", False))

    @property
    def native_value(self):
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "grid_power_w":
            return {"positive_direction": "grid import", "negative_direction": "grid export"}
        return None
