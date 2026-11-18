import argparse
import asyncio
import logging
import re
from datetime import datetime, timezone

from config import HOST, PORT, MAX_MESSAGE_LENGTH, BACKLOG
from database import Database
from protocol import encode_message, read_message, ProtocolError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lan-messenger")

def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

class MessengerServer:
    def __init__(self, host=HOST, port=PORT, db_path="messenger.db"):
        self.host, self.port = host, port
        self.db = Database(db_path)
        self.clients = {}  # username -> StreamWriter
        self.lock = asyncio.Lock()
        self.server = None
        self.stopping = False

    async def send(self, writer, payload):
        writer.write(encode_message(payload))
        await writer.drain()

    async def safe_send(self, writer, payload):
        try:
            await self.send(writer, payload)
            return True
        except (ConnectionError, OSError, ProtocolError):
            return False

    async def broadcast_system(self, message):
        payload = {"type": "system_message", "message": message, "timestamp": now()}
        async with self.lock:
            writers = list(self.clients.values())
        for writer in writers:
            await self.safe_send(writer, payload)

    async def publish_user_list(self):
        async with self.lock:
            names = sorted(self.clients)
            writers = list(self.clients.values())
        payload = {"type": "user_list", "users": names}
        for writer in writers:
            await self.safe_send(writer, payload)

    async def handle_client(self, reader, writer):
        peer = writer.get_extra_info("peername")
        username = None
        try:
            # First frame must be a login request.
            request = await asyncio.wait_for(read_message(reader), timeout=20)
            if request.get("type") != "login":
                await self.safe_send(writer, {"type": "error", "message": "Avval login yuboring."})
                return
            requested = request.get("username", "")
            if not isinstance(requested, str) or not re.fullmatch(r"[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ0-9_.-]{2,24}", requested):
                await self.safe_send(writer, {"type": "error", "message": "Login 2–24 belgi bo‘lsin; harf, raqam, _, -, . ishlating."})
                return
            async with self.lock:
                if requested.casefold() in {name.casefold() for name in self.clients}:
                    await self.safe_send(writer, {"type": "error", "message": "Bu foydalanuvchi nomi band."})
                    return
                username = requested
                self.clients[username] = writer
            async with self.lock:
                self.db.user_connected(username, now())
                history = self.db.history(username)
            await self.send(writer, {"type": "login", "status": "ok", "username": username})
            await self.send(writer, {"type": "history", "messages": history})
            await self.publish_user_list()
            await self.broadcast_system(f"{username} chatga qo‘shildi.")
            log.info("Connected: %s (%s)", username, peer)

            while not self.stopping:
                data = await read_message(reader)
                kind = data.get("type")
                if kind in ("broadcast", "private_message"):
                    message = data.get("message")
                    if not isinstance(message, str) or not message.strip() or len(message) > MAX_MESSAGE_LENGTH:
                        await self.safe_send(writer, {"type": "error", "message": f"Xabar 1–{MAX_MESSAGE_LENGTH} belgi bo‘lishi kerak."})
                        continue
                    timestamp = now()
                    if kind == "broadcast":
                        payload = {"type": "broadcast", "sender": username, "message": message, "timestamp": timestamp}
                        async with self.lock:
                            self.db.save_message(username, None, message, kind, timestamp)
                            recipients = list(self.clients.items())
                        for _, recipient in recipients:
                            await self.safe_send(recipient, payload)
                    else:
                        target = data.get("receiver")
                        if not isinstance(target, str) or target == username:
                            await self.safe_send(writer, {"type": "error", "message": "Shaxsiy xabar uchun boshqa foydalanuvchini tanlang."})
                            continue
                        async with self.lock:
                            recipient = next((w for n, w in self.clients.items() if n.casefold() == target.casefold()), None)
                            actual_target = next((n for n in self.clients if n.casefold() == target.casefold()), None)
                            if recipient:
                                self.db.save_message(username, actual_target, message, kind, timestamp)
                        if recipient:
                            payload = {"type": "private_message", "sender": username, "receiver": actual_target, "message": message, "timestamp": timestamp}
                            await self.safe_send(recipient, payload)
                            await self.safe_send(writer, payload)
                        else:
                            await self.safe_send(writer, {"type": "error", "message": "Foydalanuvchi hozir onlayn emas."})
                elif kind == "user_list_request":
                    await self.publish_user_list()
                elif kind == "history_request":
                    async with self.lock:
                        rows = self.db.history(username)
                    await self.safe_send(writer, {"type": "history", "messages": rows})
                elif kind == "logout":
                    break
                else:
                    await self.safe_send(writer, {"type": "error", "message": "Noma’lum xabar turi."})
        except asyncio.IncompleteReadError:
            pass
        except (ConnectionError, OSError) as exc:
            log.info("Connection ended %s: %s", peer, exc)
        except (ProtocolError, asyncio.TimeoutError) as exc:
            log.warning("Protocol/timeout error from %s: %s", peer, exc)
            if not writer.is_closing():
                await self.safe_send(writer, {"type": "error", "message": "Protokol xatosi yoki ulanish vaqti tugadi."})
        except Exception:
            log.exception("Unexpected client error: %s", peer)
        finally:
            if username:
                async with self.lock:
                    current = self.clients.get(username)
                    if current is writer:
                        self.clients.pop(username, None)
                        self.db.user_disconnected(username, now())
                await self.publish_user_list()
                await self.broadcast_system(f"{username} chatdan chiqdi.")
                log.info("Disconnected: %s", username)
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

    async def start(self):
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port, backlog=BACKLOG)
        sockets = self.server.sockets or []
        for sock in sockets:
            log.info("Server listening on %s:%s", *sock.getsockname()[:2])
        return self.server

    async def serve_forever(self):
        await self.start()
        async with self.server:
            await self.server.serve_forever()

    async def close(self):
        self.stopping = True
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        async with self.lock:
            writers = list(self.clients.values())
            self.clients.clear()
        for writer in writers:
            await self.safe_send(writer, {"type": "system_message", "message": "Server to‘xtatilmoqda.", "timestamp": now()})
            writer.close()
        await asyncio.gather(*(w.wait_closed() for w in writers), return_exceptions=True)

async def main(host, port, db):
    app = MessengerServer(host, port, db)
    try:
        await app.serve_forever()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await app.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LAN Messenger server")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--db", default="messenger.db")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.host, args.port, args.db))
    except KeyboardInterrupt:
        print("\\nServer stopped.")
