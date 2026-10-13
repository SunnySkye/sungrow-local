# Sungrow Local

Local, read-only monitoring for Sungrow **SG5K-D** solar inverters using **WiFi V31** communication modules. Supports Sungrow's encrypted Modbus TCP transport and a connected SG Smart Meter.

Configure each inverter through Home Assistant's UI. Readings update every 30 seconds inside Home Assistant; no cloud account, MQTT broker, external service or always-on desktop is required.

## Compatibility

| Hardware/software | Status |
| --- | --- |
| SG5K-D with WiFi V31 | Verified on two inverters |
| Inverter firmware CR0-1.0.5.0-AR0-1.0.17.0 | Verified |
| SG Smart Meter connected through one inverter | Verified |
| Home Assistant Core 2026.10.1 | Verified; minimum supported version |
| Other inverter models, WiNet-S and other firmware | Not validated; not advertised as supported |

The integration implements input-register reads only. It cannot change inverter, export-limit or grid settings.

This is a community integration and is not affiliated with or endorsed by Sungrow. Initial hardware testing covers one installation; please report compatibility results with the model and firmware version.

## Installation with HACS

[Open this repository in HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=SunnySkye&repository=sungrow-local&category=integration)

1. Open **HACS → Custom repositories**.
2. Add `https://github.com/SunnySkye/sungrow-local` with type **Integration**.
3. Download **Sungrow Local** and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Sungrow Local**.
5. Enter the WiFi module's local IP address and a device name.
6. Enable **Smart meter connected** only for the inverter that returns your meter readings.
7. Repeat setup for each additional inverter.

A custom repository can be installed before acceptance into HACS's default catalogue. Catalogue inclusion is subject to HACS review.

### Manual installation

Copy `custom_components/sungrow_local` into your Home Assistant `/config/custom_components/` directory, restart, and follow steps 4–7 above.

Existing manually configured entries are preserved when HACS replaces the files: the integration domain, inverter serial identifiers and entity unique IDs remain unchanged. Do not add duplicate entries.

## Devices and entities

Each inverter has **13 sensors and one connection binary sensor**:

- AC generation power, today's generation and lifetime generation.
- Internal temperature and grid voltage.
- DC power and the voltage/current of both MPPT inputs.
- Grid frequency and power factor.
- Last successful update and connection status.

The inverter connected to a meter also creates a separate **Sungrow Smart Meter** device with **seven sensors**:

- Signed grid power, plus separate import and export power.
- Today's imported and exported energy.
- Lifetime imported and exported energy.

Signed grid power is **positive for import** and **negative for export**. Unavailable register markers are handled as missing readings rather than very large energy or power values. A failed meter read does not hide healthy inverter readings. A failed inverter poll makes its measurements unavailable and its connection entity off.

If a single meter covers multiple inverters, configure it once. Do not sum duplicate meter readings.

### Energy dashboard

Under **Settings → Dashboards → Energy**, use each inverter's **Lifetime generation** sensor for solar production. Use the meter's **Lifetime grid import** and **Lifetime grid export** sensors for grid consumption and return to grid. Their `energy` device class and `total_increasing` state class support long-term statistics.

History begins when Home Assistant records these entities. The integration does not import past iSolarCloud history.

## Address changes and troubleshooting

- Reserve each module's IP address in your router's DHCP settings.
- If an address changes, use the integration entry's **Reconfigure** action. Reconfiguration checks the inverter serial before changing the address, keeping existing entity IDs and history.
- Home Assistant must be able to reach the module on TCP port **502**. Successful cloud reporting alone does not prove LAN access works.
- Ordinary Modbus clients may fail because these modules use Sungrow's encrypted transport.
- If setup reports missing meter readings, leave the meter option disabled for that inverter and check which inverter actually connects to the meter.
- If the module is unavailable overnight or disconnected, readings remain unavailable until communication returns; unavailable generation is not replaced with an invented zero.
- Brand icons are bundled in `brand/`. Refresh the frontend after installation if an old placeholder remains cached.

## Development

Use Python 3.14.2 or newer:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests -v
```

GitHub Actions runs protocol tests, Home Assistant integration tests, Hassfest and HACS validation. Tests use simulated responses and never access an owner's hardware.

## Credits and license

The encrypted transport was implemented using the protocol described by [Roberto Panerai Velloso's Sungrow-Modbus](https://github.com/rpvelloso/Sungrow-Modbus). Register definitions were checked against [SunGather](https://github.com/bohdan-s/SunGather).

Code is distributed under **GPL-3.0-or-later**; see [LICENSE](LICENSE). See [NOTICE](NOTICE) for protocol attribution and brand-image provenance. Sungrow marks remain the property of their respective owners and are included to identify compatible hardware.
