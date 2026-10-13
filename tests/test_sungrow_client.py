"""Protocol regression checks without Home Assistant or live-device side effects."""
import asyncio
import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import AsyncMock, Mock, patch

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

spec = importlib.util.spec_from_file_location(
    "sungrow_client", Path(__file__).parents[1] / "custom_components/sungrow_local/client.py"
)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class DecodingTests(unittest.TestCase):
    def test_word_order_and_scaling(self):
        self.assertEqual(client.value32(struct.pack(">HH", 0x5678, 0x1234), 0), 0x12345678)
        self.assertEqual(client.value32(struct.pack(">HH", 76, 0), 0, scale=0.1), 7.6)
        self.assertEqual(client.value16(struct.pack(">H", 381), 0, scale=0.1), 38.1)

    def test_signed_grid_export(self):
        self.assertEqual(client.value32(struct.pack(">HH", 0xF320, 0xFFFF), 0, signed=True), -3296)

    def test_unavailable_values_are_not_energy_or_power(self):
        for low, high in [(0xFFFF, 0xFFFF), (0xFFFF, 0x7FFF), (0, 0x8000)]:
            self.assertIsNone(client.value32(struct.pack(">HH", low, high), 0, signed=True))
        self.assertIsNone(client.value16(bytes.fromhex("ffff"), 0))


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_encrypted_read_uses_function_04_and_zero_based_address(self):
        key = bytes(range(16))

        async def fake_exchange(host, request, encrypted):
            self.assertTrue(encrypted)
            decryptor = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
            plain = (decryptor.update(request[4:]) + decryptor.finalize())[:request[2]]
            self.assertEqual(plain, bytes.fromhex("6868000000060104138a0001"))
            reply = bytes.fromhex("686800000005010402004c")
            padding = 16 - len(reply) % 16
            encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
            return bytes([1, 0, len(reply), padding]) + encryptor.update(reply + bytes([255]) * padding) + encryptor.finalize()

        with patch.object(client, "exchange", side_effect=fake_exchange):
            result = await client.read_registers("inverter", key, 5003, 1)
        self.assertEqual(result, bytes.fromhex("004c"))

    async def test_modbus_exception_is_not_decoded_as_a_reading(self):
        with patch.object(client, "exchange", AsyncMock(return_value=bytes.fromhex("000100000003018402"))):
            with self.assertRaises(client.SungrowError):
                await client.read_registers("inverter", None, 5003, 1)

    async def test_fragmented_tcp_response(self):
        reader = asyncio.StreamReader()
        writer = Mock()
        writer.drain = AsyncMock()
        async def fragments():
            for fragment in [bytes.fromhex("000100"), bytes.fromhex("0000050104"), bytes.fromhex("02004c")]:
                reader.feed_data(fragment)
                await asyncio.sleep(0)
        task = asyncio.create_task(fragments())
        try:
            with patch.object(client.asyncio, "open_connection", AsyncMock(return_value=(reader, writer))):
                data = await client.read_registers("inverter", None, 5003, 1)
            self.assertEqual(data, bytes.fromhex("004c"))
            writer.close.assert_called_once()
        finally:
            await task


if __name__ == "__main__":
    unittest.main()
