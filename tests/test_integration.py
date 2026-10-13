"""Entity/device setup and polling failure isolation."""
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_local.client import SungrowError


async def setup(hass, smart_meter=True):
    entry = MockConfigEntry(domain="sungrow_local", title="Sungrow Inverter", unique_id="TESTINV0001",
                            data={"host": "192.0.2.10", "name": "Sungrow Inverter",
                                  "serial": "TESTINV0001", "smart_meter": smart_meter})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_devices_entities_and_energy_metadata(hass, mock_read):
    entry = await setup(hass)
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert len(entities) == 21
    devices = {e.device_id for e in entities}
    assert len(devices) == 2
    meter_id = next(e.device_id for e in entities if e.unique_id == "TESTINV0001_daily_import_kwh")
    inverter_id = next(e.device_id for e in entities if e.unique_id == "TESTINV0001_generation_w")
    assert dr.async_get(hass).async_get(meter_id).via_device_id == inverter_id
    energy = hass.states.get("sensor.sungrow_smart_meter_lifetime_grid_import")
    assert energy.attributes["device_class"] == "energy"
    assert energy.attributes["state_class"] == "total_increasing"
    assert energy.attributes["unit_of_measurement"] == "kWh"
    assert hass.states.get("sensor.sungrow_smart_meter_grid_power").state == "-700"


async def test_inverter_without_meter(hass, mock_read):
    entry = await setup(hass, smart_meter=False)
    assert len(er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)) == 14
    assert hass.states.get("sensor.sungrow_smart_meter_grid_power") is None


async def test_poll_failure_and_recovery(hass, mock_read):
    entry = await setup(hass)
    mock_read[0].side_effect = SungrowError("Disconnected")
    await entry.runtime_data.async_refresh()
    assert hass.states.get("sensor.sungrow_inverter_generation_power").state == "unavailable"
    assert hass.states.get("binary_sensor.sungrow_inverter_connection").state == "off"
    mock_read[0].side_effect = None
    await entry.runtime_data.async_refresh()
    assert hass.states.get("sensor.sungrow_inverter_generation_power").state == "1500"
    assert hass.states.get("binary_sensor.sungrow_inverter_connection").state == "on"


async def test_meter_failure_does_not_hide_inverter(hass, mock_read, snapshot):
    entry = await setup(hass)
    mock_read[0].return_value = {**snapshot, "meter_available": False}
    await entry.runtime_data.async_refresh()
    assert hass.states.get("sensor.sungrow_smart_meter_grid_power").state == "unavailable"
    assert hass.states.get("sensor.sungrow_inverter_generation_power").state == "1500"


async def test_unload_removes_entities(hass, mock_read):
    entry = await setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.sungrow_inverter_generation_power") is None
    assert hass.states.get("sensor.sungrow_smart_meter_grid_power") is None
