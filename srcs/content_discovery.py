import json
import signal
import socket as socket_module
import threading

from srcs.config import BUFFER_SIZE, DISCOVERY_CLEANUP_INTERVAL, DISCOVERY_PORT
from srcs.state_store import save_state
from srcs.ui_utils import timestamp


ip2user = {}
user2ip = {}
chunks = {}
last_printed_announcements = {}
lock = threading.Lock()
shutdown_event = threading.Event()


def persist_state():
    save_state({
        "ip2user": ip2user,
        "user2ip": user2ip,
        "chunks": chunks
    })


def cleanup():
    while not shutdown_event.wait(DISCOVERY_CLEANUP_INTERVAL):
        with lock:
            chunks.clear()
            ip2user.clear()
            user2ip.clear()
            persist_state()


def request_shutdown(_signum=None, _frame=None):
    shutdown_event.set()


def handle_announcement(data, addr):
    ip = addr[0]
    try:
        message = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError:
        print(f"[{timestamp()}] Error: Invalid JSON from {ip}")
        return

    user = message.get("username")
    chunk_list = message.get("chunks", [])
    if not user:
        print(f"[{timestamp()}] Warning: Announcement from {ip} has no username.")
        return

    normalized_chunks = tuple(sorted(chunk_list))
    should_print = False

    with lock:
        ip2user[ip] = user
        user2ip[user] = ip

        for chunk in chunk_list:
            users = chunks.setdefault(chunk, [])
            if user not in users:
                users.append(user)

        previous_announcement = last_printed_announcements.get(ip)
        current_announcement = (user, normalized_chunks)
        should_print = previous_announcement != current_announcement
        if should_print:
            last_printed_announcements[ip] = current_announcement

        persist_state()

    if should_print:
        print(f"[{timestamp()}] {user} : {', '.join(chunk_list)}")


def create_discovery_socket():
    socket = socket_module.socket(socket_module.AF_INET, socket_module.SOCK_DGRAM)
    try:
        socket.setsockopt(socket_module.SOL_SOCKET, socket_module.SO_REUSEADDR, 1)
        socket.bind(("", DISCOVERY_PORT))
        return socket
    except OSError:
        socket.close()
        raise


def content_discovery(socket=None):
    shutdown_event.clear()
    if socket is None:
        socket = create_discovery_socket()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    with socket:
        socket.settimeout(1)
        threading.Thread(target=cleanup, daemon=True).start()

        while not shutdown_event.is_set():
            try:
                data, addr = socket.recvfrom(BUFFER_SIZE)
                handle_announcement(data, addr)
            except socket_module.timeout:
                continue
            except OSError as e:
                if shutdown_event.is_set():
                    break
                print(f"[{timestamp()}] Error: {e}")


if __name__ == "__main__":
    content_discovery()
