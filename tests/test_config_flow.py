"""User setup, duplicate protection and identity-safe reconfiguration."""
from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_local.client import SungrowError

DOMAIN = "sungrow_local"
INPUT = {"host": "192.0.2.10", "name": "Sungrow Inverter", "smart_meter": True}


async def test_user_setup(hass, mock_read):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {**INPUT, "serial": "TESTINV0001"}
    await hass.async_block_till_done()


async def test_connection_error(hass, mock_read):
    mock_read[1].side_effect = SungrowError("Cannot connect")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data=INPUT)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_meter_is_not_created_when_unavailable(hass, mock_read, snapshot):
    mock_read[1].return_value = {**snapshot, "meter_available": False}
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data=INPUT)
    assert result["errors"] == {"base": "meter_unavailable"}


async def test_duplicate_serial(hass, mock_read):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="TESTINV0001", data={**INPUT, "serial": "TESTINV0001"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data=INPUT)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_rejects_different_inverter(hass, mock_read, snapshot):
    entry = MockConfigEntry(domain=DOMAIN, title=INPUT["name"], unique_id="TESTINV0001",
                            data={**INPUT, "serial": "TESTINV0001"})
    entry.add_to_hass(hass)
    mock_read[1].return_value = {**snapshot, "serial": "OTHERINV0001"}
    result = await hass.config_entries.flow.async_init(DOMAIN, context={
        "source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id,
    }, data={**INPUT, "host": "192.0.2.11"})
    assert result["errors"] == {"base": "wrong_inverter"}
    assert entry.data["host"] == INPUT["host"]


async def test_reconfigure_preserves_identity(hass, mock_read):
    entry = MockConfigEntry(domain=DOMAIN, title=INPUT["name"], unique_id="TESTINV0001",
                            data={**INPUT, "serial": "TESTINV0001"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={
        "source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id,
    }, data={**INPUT, "host": "192.0.2.11"})
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["host"] == "192.0.2.11"
    assert entry.unique_id == "TESTINV0001"
    await hass.async_block_till_done()
