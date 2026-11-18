# Client (forma orqali ma'lumot kiritish)
import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext


class ChatClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Client")
        self.root.geometry("520x650")
        self.root.resizable(False, False)

        self.client_socket = None
        self.client_id = ""
        self.connected = False

        tk.Label(root, text="ID:", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(18, 4))
        self.id_entry = tk.Entry(root, width=30, font=("Arial", 11))
        self.id_entry.pack(anchor="w", padx=20, fill="x", ipady=6)

        tk.Label(root, text="Ism / Familiya:", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(12, 4))
        self.name_entry = tk.Entry(root, width=30, font=("Arial", 11))
        self.name_entry.pack(anchor="w", padx=20, fill="x", ipady=6)

        tk.Label(root, text="Server IP:", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(12, 4))
        self.ip_entry = tk.Entry(root, width=30, font=("Arial", 11))
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.pack(anchor="w", padx=20, fill="x", ipady=6)

        tk.Label(root, text="Port:", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(12, 4))
        self.port_entry = tk.Entry(root, width=30, font=("Arial", 11))
        self.port_entry.insert(0, "5555")
        self.port_entry.pack(anchor="w", padx=20, fill="x", ipady=6)

        self.connect_btn = tk.Button(root, text="Ulanish", command=self.connect_to_server, bg="#2E7D32", fg="white", font=("Arial", 10, "bold"))
        self.connect_btn.pack(anchor="w", padx=20, pady=(18, 10), ipadx=18, ipady=8)

        self.chat_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, state="disabled", height=18, font=("Arial", 10))
        self.chat_box.pack(padx=20, pady=(8, 8), fill="both", expand=True)

        msg_frame = tk.Frame(root)
        msg_frame.pack(fill="x", padx=20, pady=(0, 16))
        self.msg_entry = tk.Entry(msg_frame, font=("Arial", 11))
        self.msg_entry.bind("<Return>", lambda event: self.send_message())
        self.msg_entry.pack(side=tk.LEFT, fill="x", expand=True, ipady=8)
        self.send_btn = tk.Button(msg_frame, text="Yuborish", command=self.send_message, bg="#1565C0", fg="white", font=("Arial", 10, "bold"))
        self.send_btn.pack(side=tk.RIGHT, padx=(10, 0), ipadx=16, ipady=8)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def append_message(self, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert(tk.END, text + "\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.see(tk.END)

    def connect_to_server(self):
        user_id = self.id_entry.get().strip()
        name = self.name_entry.get().strip()
        server_ip = self.ip_entry.get().strip() or "127.0.0.1"
        port_text = self.port_entry.get().strip() or "5555"

        if not user_id or not name:
            messagebox.showerror("Xato", "ID va ism/familiya kiritilishi shart.")
            return

        try:
            port = int(port_text)
        except ValueError:
            messagebox.showerror("Xato", "Port raqami noto'g'ri.")
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5)
            self.client_socket.connect((server_ip, port))
            self.client_socket.sendall(f"{user_id}|{name}".encode("utf-8"))
            self.client_id = user_id
            self.connected = True
            self.append_message(f"=== {name} [{user_id}] sifatida ulandingiz ===")
            self.connect_btn.config(state="disabled")

            receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            receive_thread.start()
        except Exception as exc:
            messagebox.showerror("Ulanish xatosi", str(exc))

    def receive_messages(self):
        while self.connected and self.client_socket:
            try:
                msg = self.client_socket.recv(1024).decode("utf-8")
                if not msg:
                    break
                self.append_message(msg.rstrip())
            except socket.timeout:
                continue
            except Exception:
                break

        self.connected = False
        self.connect_btn.config(state="normal")
        self.append_message("[Ulanish uzildi]")

    def send_message(self):
        if not self.connected or self.client_socket is None:
            messagebox.showwarning("Ogohlantirish", "Avval serverga ulanib oling.")
            return

        msg = self.msg_entry.get().strip()
        if not msg:
            return

        if msg.lower() == "exit":
            self.client_socket.sendall(b"exit")
            self.on_close()
            return

        try:
            self.client_socket.sendall(msg.encode("utf-8"))
            self.msg_entry.delete(0, tk.END)
        except Exception:
            messagebox.showerror("Xato", "Xabar jo'natilmadi.")

    def on_close(self):
        if self.client_socket is not None:
            try:
                self.client_socket.sendall(b"exit")
            except Exception:
                pass
            self.client_socket.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClientApp(root)
    root.mainloop()