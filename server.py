# Server (ko'p foydalanuvchili chat)
import os
import socket
import threading

DEFAULT_HOST = os.environ.get("CHAT_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("CHAT_PORT", "5555"))

clients = {}
lock = threading.Lock()


def broadcast(message, sender_socket=None):
    with lock:
        for client_socket in list(clients.keys()):
            if client_socket != sender_socket:
                try:
                    client_socket.sendall(message.encode('utf-8'))
                except Exception:
                    pass


def normalize_client_identity(raw_data, addr):
    raw_data = (raw_data or "").strip()
    if not raw_data:
        raw_data = f"Foydalanuvchi_{addr[1]}"

    user_id = raw_data
    name = raw_data
    if "|" in raw_data:
        user_id, _, name = raw_data.partition('|')
        name = name.strip()
    user_id = user_id.strip()
    if not name:
        name = f"Foydalanuvchi_{addr[1]}"
    if not user_id:
        user_id = name
    return user_id, name


def handle_client(client_socket, addr):
    try:
        raw_data = client_socket.recv(4096).decode('utf-8').strip()
        user_id, name = normalize_client_identity(raw_data, addr)

        with lock:
            clients[client_socket] = {"id": user_id, "name": name}

        print(f"[YANGI] {name} [{user_id}] ({addr}) ulandi")
        broadcast(f"\n>>> {name} [{user_id}] chatga qo'shildi <<<\n", client_socket)

        while True:
            msg = client_socket.recv(4096).decode('utf-8')
            if not msg:
                break
            if msg.lower() == 'exit':
                break

            print(f"{name} [{user_id}]: {msg}")
            broadcast(f"{name}: {msg}", client_socket)

    except (ConnectionResetError, OSError, UnicodeDecodeError):
        pass
    finally:
        with lock:
            if client_socket in clients:
                left_user = clients.pop(client_socket)
                left_name = left_user.get("name", "Foydalanuvchi")
                print(f"[CHIQDI] {left_name} ({addr})")
                broadcast(f"\n>>> {left_name} chatni tark etdi <<<\n")
        try:
            client_socket.close()
        except Exception:
            pass


def start_server(host=DEFAULT_HOST, port=DEFAULT_PORT):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(10)
    print(f"[SERVER] {host}:{port} da tinglanmoqda...")
    print("Kutilmoqda...\n")

    while True:
        client_socket, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True)
        thread.start()


if __name__ == "__main__":
    import sys

    host = DEFAULT_HOST
    port = DEFAULT_PORT

    if len(sys.argv) >= 2:
        host = sys.argv[1]
    if len(sys.argv) >= 3:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print("Port raqami noto'g'ri. Masalan: python server.py 0.0.0.0 5555")
            sys.exit(1)

    print(f"Server ishga tushdi. Ulanish uchun IP: {host}, Port: {port}")
    start_server(host=host, port=port)