"""Read-only Sungrow encrypted Modbus TCP client for SG5K-D.

Protocol: https://github.com/rpvelloso/Sungrow-Modbus
Registers: https://github.com/bohdan-s/SunGather/blob/main/SunGather/registers-sungrow.yaml
Only input-register reads (function 04) are implemented.
"""
import asyncio
import struct
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class SungrowError(Exception):
    """Communication or unsupported device error."""


async def exchange(host, request, encrypted=False):
    """Exchange exactly one request with bounded connection and read times."""
    writer = None
    try:
        async with asyncio.timeout(5):
            reader, writer = await asyncio.open_connection(host, 502)
            writer.write(request)
            await writer.drain()
            header = await reader.readexactly(4 if encrypted else 6)
            remaining = header[2] + header[3] if encrypted else struct.unpack(">H", header[4:6])[0]
            if remaining < 3 or remaining > 512 or (encrypted and remaining % 16):
                raise SungrowError("Invalid packet length")
            return header + await reader.readexactly(remaining)
    except (OSError, TimeoutError, asyncio.IncompleteReadError) as err:
        raise SungrowError(f"Cannot read {host}: {type(err).__name__}") from err
    finally:
        if writer is not None:
            writer.close()


async def session_key(host):
    reply = await exchange(host, bytes.fromhex("686800000006f7040ae70008"))
    if len(reply) != 25 or reply[6:9] != bytes([247, 4, 16]):
        raise SungrowError("Invalid Sungrow session response")
    public = reply[9:]
    if public in (bytes(16), bytes([255]) * 16):
        return None
    return bytes(a ^ b for a, b in zip(public, b"Grow#0*2Sun68CbE", strict=True))


async def read_registers(host, key, address, count):
    request = struct.pack(">HHHBBHH", 1, 0, 6, 1, 4, address - 1, count)
    if key:
        padding = 16 - len(request) % 16
        encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
        payload = b"\x68\x68" + request[2:] + bytes([255]) * padding
        packet = bytes([1, 0, len(request), padding]) + encryptor.update(payload) + encryptor.finalize()
        wire = await exchange(host, packet, True)
        decryptor = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
        reply = (decryptor.update(wire[4:]) + decryptor.finalize())[:wire[2]]
        expected_transaction = b"\x68\x68"
    else:
        reply = await exchange(host, request)
        expected_transaction = b"\x00\x01"
    if len(reply) < 9 or reply[:2] != expected_transaction or reply[2:4] != b"\x00\x00" or reply[6] != 1:
        raise SungrowError("Invalid Modbus response header")
    if reply[7] == 0x84:
        raise SungrowError(f"Modbus exception {reply[8]} at register {address}")
    if reply[7] != 4 or reply[8] != count * 2 or len(reply) != 9 + count * 2:
        raise SungrowError("Modbus response does not match requested registers")
    return reply[9:]


def value16(data, offset, signed=False, scale=1):
    raw = struct.unpack_from(">H", data, offset)[0]
    if raw == 0xFFFF or (signed and raw in (0x7FFF, 0x8000)):
        return None
    if signed and raw >= 0x8000:
        raw -= 0x10000
    return round(raw * scale, 3)


def value32(data, offset, signed=False, scale=1):
    low, high = struct.unpack_from(">HH", data, offset)
    raw = low + high * 65536
    if raw == 0xFFFFFFFF or (signed and raw in (0x7FFFFFFF, 0x80000000)):
        return None
    if signed and raw >= 0x80000000:
        raw -= 0x100000000
    return round(raw * scale, 3)


async def read_snapshot(host, expected_serial=None, smart_meter=False):
    key = await session_key(host)
    # Identity and all electrical measurements are read in one contiguous block.
    basic = await read_registers(host, key, 4990, 49)
    serial = basic[:20].decode("ascii").strip("\x00 ")
    if expected_serial and serial != expected_serial:
        raise SungrowError(f"Inverter identity changed at {host}")
    if value16(basic, 20) != 0x0126:
        raise SungrowError("This integration supports SG5K-D inverters")
    offset = lambda address: (address - 4990) * 2
    total = await read_registers(host, key, 5144, 2)
    values = {
        "serial": serial,
        "generation_w": value32(basic, offset(5031)),
        "daily_generation_kwh": value16(basic, offset(5003), scale=0.1),
        "total_generation_kwh": value32(total, 0, scale=0.1),
        "temperature_c": value16(basic, offset(5008), signed=True, scale=0.1),
        "grid_voltage_v": value16(basic, offset(5019), scale=0.1),
        "dc_power_w": value32(basic, offset(5017)),
        "mppt_1_voltage_v": value16(basic, offset(5011), scale=0.1),
        "mppt_1_current_a": value16(basic, offset(5012), scale=0.1),
        "mppt_2_voltage_v": value16(basic, offset(5013), scale=0.1),
        "mppt_2_current_a": value16(basic, offset(5014), scale=0.1),
        "grid_frequency_hz": value16(basic, offset(5036), scale=0.1),
        "power_factor": value16(basic, offset(5035), signed=True, scale=0.001),
        "last_updated": datetime.now(timezone.utc),
    }
    if smart_meter:
        try:
            meter = await read_registers(host, key, 5083, 18)
            for name, address, signed, scale in (
                ("grid_power_w", 5083, True, 1),
                ("daily_export_kwh", 5093, False, 0.1),
                ("total_export_kwh", 5095, False, 0.1),
                ("daily_import_kwh", 5097, False, 0.1),
                ("total_import_kwh", 5099, False, 0.1),
            ):
                values[name] = value32(meter, (address - 5083) * 2, signed, scale)
            power = values["grid_power_w"]
            values["grid_import_w"] = None if power is None else max(power, 0)
            values["grid_export_w"] = None if power is None else max(-power, 0)
        except SungrowError:
            # Meter failure must not hide healthy inverter measurements or retain stale meter data.
            values["meter_available"] = False
        else:
            values["meter_available"] = all(values.get(k) is not None for k in (
                "grid_power_w", "total_import_kwh", "total_export_kwh",
            ))
    return values
