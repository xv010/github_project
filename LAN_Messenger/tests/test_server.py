import asyncio
import tempfile
import unittest
from pathlib import Path
from server import MessengerServer
from protocol import encode_message, read_message

async def recv(reader):
    return await asyncio.wait_for(read_message(reader), 2)

class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = MessengerServer("127.0.0.1", 0, str(Path(self.tmp.name) / "test.db"))
        self.server = await self.app.start()
        self.port = self.server.sockets[0].getsockname()[1]
        self.clients = []

    async def asyncTearDown(self):
        for r, w in self.clients:
            w.close()
            try: await w.wait_closed()
            except Exception: pass
        await self.app.close()
        self.tmp.cleanup()

    async def connect(self, username):
        r, w = await asyncio.open_connection("127.0.0.1", self.port)
        self.clients.append((r, w))
        w.write(encode_message({"type": "login", "username": username}))
        await w.drain()
        first = await recv(r)
        if first.get("type") == "login" and first.get("status") == "ok":
            history = await recv(r)
            self.assertEqual(history["type"], "history")
        return r, w, first

    async def send(self, writer, obj):
        writer.write(encode_message(obj))
        await writer.drain()

    async def test_broadcast_private_duplicate_and_db(self):
        a, aw, ok = await self.connect("Ali")
        b, bw, _ = await self.connect("Vali")
        c, cw, _ = await self.connect("Salima")
        self.assertEqual(ok.get("status"), "ok")
        # Drain join/user-list notifications before testing payload routing.
        await asyncio.sleep(0.05)
        for reader in (a, b, c):
            while not reader._buffer == b"":
                try: await asyncio.wait_for(read_message(reader), 0.03)
                except Exception: break
        await self.send(aw, {"type": "broadcast", "sender": "FAKE", "message": "Assalomu alaykum"})
        received = [await recv(r) for r in (a, b, c)]
        self.assertTrue(all(x["type"] == "broadcast" and x["sender"] == "Ali" for x in received))
        await self.send(aw, {"type": "private_message", "receiver": "Vali", "message": "Faqat senga"})
        # Ali gets echo; Vali gets message; Salima must not receive it.
        ra, rb = await recv(a), await recv(b)
        self.assertEqual(ra["type"], "private_message")
        self.assertEqual(rb["message"], "Faqat senga")
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(read_message(c), 0.15)
        rows = self.app.db.history("Ali")
        self.assertTrue(any(x["message"] == "Assalomu alaykum" for x in rows))
        self.assertTrue(any(x["message"] == "Faqat senga" for x in rows))
        _, _, duplicate = await self.connect("ali")
        self.assertEqual(duplicate["type"], "error")

if __name__ == "__main__":
    unittest.main()
