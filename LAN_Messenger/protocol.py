"""Length-prefixed JSON protocol: 4-byte unsigned big-endian length + UTF-8 JSON."""
import asyncio
import json
import struct
from config import MAX_FRAME_SIZE

class ProtocolError(Exception):
    pass

def encode_message(message: dict) -> bytes:
    if not isinstance(message, dict):
        raise ProtocolError("Message must be a JSON object")
    try:
        payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProtocolError(f"Cannot encode message: {exc}") from exc
    if not payload or len(payload) > MAX_FRAME_SIZE:
        raise ProtocolError("Frame size is invalid or exceeds the limit")
    return struct.pack("!I", len(payload)) + payload

async def read_message(reader: asyncio.StreamReader) -> dict:
    try:
        header = await reader.readexactly(4)
        (length,) = struct.unpack("!I", header)
        if length < 1 or length > MAX_FRAME_SIZE:
            raise ProtocolError("Invalid frame length")
        payload = await reader.readexactly(length)
        value = json.loads(payload.decode("utf-8"))
    except asyncio.IncompleteReadError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, struct.error) as exc:
        raise ProtocolError(f"Invalid frame: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("type"), str):
        raise ProtocolError("JSON message must be an object with a string 'type'")
    return value
