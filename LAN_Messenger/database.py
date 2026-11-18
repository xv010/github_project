"""Small SQLite repository. All calls are serialized by an asyncio lock in the server."""
import sqlite3
from pathlib import Path

class Database:
    def __init__(self, path="messenger.db"):
        self.path = str(path)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=15000")
        return conn

    def _init_db(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                connected_at TEXT,
                last_seen TEXT
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                receiver TEXT,
                message TEXT NOT NULL,
                message_type TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_time ON messages(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_pair ON messages(sender, receiver)")

    def user_connected(self, username, timestamp):
        with self._connect() as conn:
            conn.execute("""INSERT INTO users(username, connected_at, last_seen)
                VALUES(?,?,?) ON CONFLICT(username) DO UPDATE SET
                connected_at=excluded.connected_at, last_seen=excluded.last_seen""",
                (username, timestamp, timestamp))

    def user_disconnected(self, username, timestamp):
        with self._connect() as conn:
            conn.execute("UPDATE users SET last_seen=? WHERE username=?", (timestamp, username))

    def save_message(self, sender, receiver, message, message_type, timestamp):
        with self._connect() as conn:
            cur = conn.execute("""INSERT INTO messages
                (sender, receiver, message, message_type, timestamp)
                VALUES(?,?,?,?,?)""", (sender, receiver, message, message_type, timestamp))
            return cur.lastrowid

    def history(self, username, limit=100):
        with self._connect() as conn:
            rows = conn.execute("""SELECT sender, receiver, message, message_type, timestamp
                FROM messages
                WHERE (message_type='broadcast')
                   OR (message_type='private_message' AND (sender=? OR receiver=?))
                ORDER BY id DESC LIMIT ?""", (username, username, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]
