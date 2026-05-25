import json
import socket
import threading
import time

from srcs.path_utils import STATE_FILE
from srcs.ui_utils import ts


PORT = 6000
BUFSIZE = 4096
INTERVAL = 60

ip2user = {}
user2ip = {}
chunks = {}
lock = threading.Lock()


def save_state():
    state = {
        "ip2user": ip2user,
        "user2ip": user2ip,
        "chunks": chunks
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)


def cleanup():
    while True:
        time.sleep(INTERVAL)
        with lock:
            chunks.clear()
            ip2user.clear()
            user2ip.clear()
            save_state()
        print(f"[{ts()}] Recency check: Discovery state cleared.")


def handle_announcement(data, addr):
    ip = addr[0]
    try:
        message = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError:
        print(f"[{ts()}] Error: Invalid JSON from {ip}")
        return

    user = message.get("username")
    chunk_list = message.get("chunks", [])
    if not user:
        print(f"[{ts()}] Warning: Announcement from {ip} has no username.")
        return

    with lock:
        ip2user[ip] = user
        user2ip[user] = ip

        for chunk in chunk_list:
            users = chunks.setdefault(chunk, [])
            if user not in users:
                users.append(user)
        save_state()

    print(f"[{ts()}] Peer Found: {user} ({ip}) hosts {', '.join(chunk_list)}")


def create_discovery_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", PORT))
        return sock
    except Exception:
        sock.close()
        raise


def content_discovery(sock=None):
    if sock is None:
        sock = create_discovery_socket()

    with sock:
        threading.Thread(target=cleanup, daemon=True).start()
        print(f"Content Discovery started. Listening on UDP port {PORT}...")

        while True:
            try:
                data, addr = sock.recvfrom(BUFSIZE)
                handle_announcement(data, addr)
            except KeyboardInterrupt:
                print("\nShutting down Content Discovery...")
                break
            except Exception as e:
                print(f"[{ts()}] Error: {e}")


if __name__ == "__main__":
    content_discovery()
