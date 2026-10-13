"""Enable custom integrations for Home Assistant's test harness."""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def snapshot():
    return {
        "serial": "TESTINV0001",
        "generation_w": 1500,
        "daily_generation_kwh": 12.3,
        "total_generation_kwh": 10000.5,
        "temperature_c": 38.1,
        "grid_voltage_v": 235.5,
        "dc_power_w": 1540,
        "mppt_1_voltage_v": 390.0,
        "mppt_1_current_a": 2.0,
        "mppt_2_voltage_v": 250.0,
        "mppt_2_current_a": 3.0,
        "grid_frequency_hz": 50.0,
        "power_factor": 1.0,
        "last_updated": datetime.now(timezone.utc),
        "meter_available": True,
        "grid_power_w": -700,
        "grid_import_w": 0,
        "grid_export_w": 700,
        "daily_import_kwh": 7.6,
        "daily_export_kwh": 10.0,
        "total_import_kwh": 12345.6,
        "total_export_kwh": 7890.1,
    }


@pytest.fixture
def mock_read(snapshot):
    with (
        patch("custom_components.sungrow_local.read_snapshot", return_value=snapshot) as poll,
        patch("custom_components.sungrow_local.config_flow.read_snapshot", return_value=snapshot) as flow,
    ):
        yield poll, flow
