import json
import signal
import socket
import threading

from srcs.path_utils import STATE_FILE
from srcs.ui_utils import ts


PORT = 6000
BUFFER_SIZE = 4096
INTERVAL = 60

ip2user = {}
user2ip = {}
chunks = {}
lock = threading.Lock()
shutdown_event = threading.Event()


def save_state():
    state = {
        "ip2user": ip2user,
        "user2ip": user2ip,
        "chunks": chunks
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)


def cleanup():
    while not shutdown_event.wait(INTERVAL):
        with lock:
            chunks.clear()
            ip2user.clear()
            user2ip.clear()
            save_state()


def request_shutdown(_signum=None, _frame=None):
    shutdown_event.set()


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

    print(f"[{ts()}] {user} : {', '.join(chunk_list)}")


def create_discovery_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", PORT))
        return sock
    except OSError:
        sock.close()
        raise


def content_discovery(sock=None):
    shutdown_event.clear()
    if sock is None:
        sock = create_discovery_socket()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    with sock:
        sock.settimeout(1)
        threading.Thread(target=cleanup, daemon=True).start()

        while not shutdown_event.is_set():
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                handle_announcement(data, addr)
            except socket.timeout:
                continue
            except OSError as e:
                if shutdown_event.is_set():
                    break
                print(f"[{ts()}] Error: {e}")


if __name__ == "__main__":
    content_discovery()
