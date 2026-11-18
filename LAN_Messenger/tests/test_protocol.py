import asyncio
import unittest
from protocol import encode_message, read_message, ProtocolError

class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_utf8_roundtrip(self):
        expected = {"type": "broadcast", "message": "O‘zbekcha: salom, ғ, қ, ў, ҳ"}
        reader = asyncio.StreamReader()
        reader.feed_data(encode_message(expected))
        reader.feed_eof()
        self.assertEqual(await read_message(reader), expected)

    async def test_invalid_length(self):
        reader = asyncio.StreamReader()
        reader.feed_data(b"\\x00\\x00\\x00\\x00")
        reader.feed_eof()
        with self.assertRaises(ProtocolError):
            await read_message(reader)

if __name__ == "__main__":
    unittest.main()
