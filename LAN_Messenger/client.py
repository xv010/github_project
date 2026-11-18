import asyncio
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from protocol import encode_message, read_message

class NetworkClient:
    def __init__(self, events):
        self.events = events
        self.loop = None
        self.reader = None
        self.writer = None
        self.thread = threading.Thread(target=self._thread_main, daemon=True)
        self.thread.start()
        self.ready = threading.Event()

    def _thread_main(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.ready.set()
        self.loop.run_forever()

    def submit(self, coro):
        self.ready.wait()
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    async def connect(self, host, port, username):
        try:
            self.reader, self.writer = await asyncio.open_connection(host, port)
            self.writer.write(encode_message({"type": "login", "username": username}))
            await self.writer.drain()
            self.events.put({"type": "status", "text": "Serverga ulanmoqda..."})
            asyncio.create_task(self._reader_task())
        except Exception as exc:
            self.events.put({"type": "disconnected", "message": str(exc)})

    async def _reader_task(self):
        try:
            while True:
                msg = await read_message(self.reader)
                self.events.put(msg)
        except Exception as exc:
            self.events.put({"type": "disconnected", "message": str(exc)})
        finally:
            if self.writer:
                self.writer.close()
                try:
                    await self.writer.wait_closed()
                except Exception:
                    pass
            self.reader = self.writer = None

    async def send(self, payload):
        if not self.writer or self.writer.is_closing():
            self.events.put({"type": "error", "message": "Serverga ulanmagan."})
            return
        try:
            self.writer.write(encode_message(payload))
            await self.writer.drain()
        except Exception as exc:
            self.events.put({"type": "disconnected", "message": str(exc)})

    async def disconnect(self):
        if self.writer:
            try:
                self.writer.write(encode_message({"type": "logout"}))
                await self.writer.drain()
            except Exception:
                pass
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = self.reader = None

class MessengerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LAN Messenger")
        self.root.geometry("900x600")
        self.root.minsize(700, 480)
        self.events = queue.Queue()
        self.net = NetworkClient(self.events)
        self.username = ""
        self.connected = False
        self.selected_user = None
        self._style()
        self._build()
        self.root.after(100, self._poll)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=7)

    def _build(self):
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="LAN MESSENGER", style="Title.TLabel").pack(side="left")
        self.status = ttk.Label(top, text="● Offline", foreground="#b33")
        self.status.pack(side="right")

        login = ttk.LabelFrame(self.root, text="Ulanish", padding=10)
        login.pack(fill="x", padx=12, pady=(0, 10))
        self.host = tk.StringVar(value="192.168.1.100")
        self.port = tk.StringVar(value="5000")
        self.name = tk.StringVar()
        ttk.Label(login, text="Server IP").grid(row=0, column=0, padx=4)
        ttk.Entry(login, textvariable=self.host, width=18).grid(row=0, column=1, padx=4)
        ttk.Label(login, text="Port").grid(row=0, column=2, padx=4)
        ttk.Entry(login, textvariable=self.port, width=7).grid(row=0, column=3, padx=4)
        ttk.Label(login, text="Username").grid(row=0, column=4, padx=4)
        ttk.Entry(login, textvariable=self.name, width=16).grid(row=0, column=5, padx=4)
        self.connect_btn = ttk.Button(login, text="Ulanish", command=self._connect)
        self.connect_btn.grid(row=0, column=6, padx=4)
        self.disconnect_btn = ttk.Button(login, text="Uzish", command=self._disconnect, state="disabled")
        self.disconnect_btn.grid(row=0, column=7, padx=4)

        body = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        body.pack(fill="both", expand=True)
        chat_frame = ttk.LabelFrame(body, text="Chat", padding=8)
        chat_frame.pack(side="left", fill="both", expand=True)
        self.chat = tk.Text(chat_frame, wrap="word", state="disabled", font=("Segoe UI", 10), padx=8, pady=8)
        scroll = ttk.Scrollbar(chat_frame, command=self.chat.yview)
        self.chat.configure(yscrollcommand=scroll.set)
        self.chat.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.chat.tag_configure("mine", justify="right", foreground="#1459a6", spacing1=5, spacing3=5)
        self.chat.tag_configure("other", justify="left", foreground="#222", spacing1=5, spacing3=5)
        self.chat.tag_configure("system", justify="center", foreground="#777", spacing1=5, spacing3=5)

        side = ttk.LabelFrame(body, text="Onlayn foydalanuvchilar", padding=8)
        side.pack(side="right", fill="y", padx=(10, 0))
        self.users = tk.Listbox(side, width=22, font=("Segoe UI", 10), exportselection=False)
        self.users.pack(fill="both", expand=True)
        self.users.bind("<<ListboxSelect>>", self._select_user)
        ttk.Button(side, text="Umumiy chat", command=self._public).pack(fill="x", pady=(8, 0))

        bottom = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        bottom.pack(fill="x")
        self.target_label = ttk.Label(bottom, text="Qabul qiluvchi: Umumiy chat")
        self.target_label.pack(anchor="w", pady=(0, 5))
        self.message = tk.StringVar()
        entry = ttk.Entry(bottom, textvariable=self.message)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", self._send)
        ttk.Button(bottom, text="Yuborish", command=self._send).pack(side="left", padx=(8, 0))

    def _append(self, text, tag="other"):
        self.chat.configure(state="normal")
        self.chat.insert("end", text + "\\n", tag)
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _connect(self):
        if self.connected:
            return
        username = self.name.get().strip()
        if not username:
            messagebox.showwarning("Login", "Foydalanuvchi nomini kiriting.")
            return
        try:
            port = int(self.port.get())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror("Port", "Port 1–65535 oralig‘ida bo‘lishi kerak.")
            return
        self.username = username
        self.net.submit(self.net.connect(self.host.get().strip(), port, username))
        self.status.config(text="● Connecting...", foreground="#b8860b")
        self.connect_btn.config(state="disabled")

    def _disconnect(self):
        self.net.submit(self.net.disconnect())
        self.connected = False
        self._set_offline("Ulanish uzildi.")

    def _set_offline(self, message):
        self.connected = False
        self.status.config(text="● Offline", foreground="#b33")
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self._append(message, "system")

    def _send(self, event=None):
        message = self.message.get().strip()
        if not message or not self.connected:
            return
        if self.selected_user:
            payload = {"type": "private_message", "receiver": self.selected_user, "message": message}
        else:
            payload = {"type": "broadcast", "message": message}
        self.net.submit(self.net.send(payload))
        self.message.set("")

    def _select_user(self, event=None):
        selection = self.users.curselection()
        if selection:
            value = self.users.get(selection[0])
            if value != self.username:
                self.selected_user = value
                self.target_label.config(text=f"Qabul qiluvchi: {value} (shaxsiy)")
            else:
                self._public()

    def _public(self):
        self.selected_user = None
        self.target_label.config(text="Qabul qiluvchi: Umumiy chat")

    def _poll(self):
        try:
            while True:
                msg = self.events.get_nowait()
                kind = msg.get("type")
                if kind == "login":
                    if msg.get("status") == "ok":
                        self.connected = True
                        self.status.config(text="● Online", foreground="#198754")
                        self.connect_btn.config(state="disabled")
                        self.disconnect_btn.config(state="normal")
                        self._append(f"Ulandi: {msg.get('username')}", "system")
                    else:
                        self._set_offline(msg.get("message", "Login xatosi"))
                elif kind == "user_list":
                    self.users.delete(0, "end")
                    for user in msg.get("users", []):
                        self.users.insert("end", user)
                elif kind == "history":
                    self._append("--- Saqlangan chat tarixi ---", "system")
                    for item in msg.get("messages", []):
                        self._display_message(item)
                elif kind in ("broadcast", "private_message"):
                    self._display_message(msg)
                elif kind == "system_message":
                    self._append(msg.get("message", ""), "system")
                elif kind == "error":
                    self._append("XATOLIK: " + msg.get("message", ""), "system")
                    if not self.connected:
                        self.connect_btn.config(state="normal")
                elif kind == "disconnected":
                    self._set_offline("Server bilan aloqa uzildi: " + msg.get("message", ""))
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _display_message(self, msg):
        sender = msg.get("sender", "")
        stamp = msg.get("timestamp", "")
        try:
            stamp = datetime.fromisoformat(stamp).strftime("%H:%M:%S")
        except Exception:
            pass
        private = msg.get("message_type") == "private_message" or msg.get("type") == "private_message"
        label = f"[Shaxsiy: {sender} → {msg.get('receiver','')}] " if private else f"{sender}: "
        tag = "mine" if sender == self.username else "other"
        self._append(f"{stamp}  {label}{msg.get('message','')}", tag)

    def _close(self):
        try:
            self.net.submit(self.net.disconnect()).result(timeout=2)
        except Exception:
            pass
        if self.net.loop:
            self.net.loop.call_soon_threadsafe(self.net.loop.stop)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    MessengerGUI(root)
    root.mainloop()
