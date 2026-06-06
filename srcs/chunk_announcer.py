import json
import signal
import socket as socket_module
import threading
import os

from srcs.config import ANNOUNCE_INTERVAL, BROADCAST_IP, DISCOVERY_PORT
from srcs.file_utils import split_file
from srcs.path_utils import CHUNK_DIR
from srcs.ui_utils import timestamp


shutdown_event = threading.Event()


def collect_chunks(directory=CHUNK_DIR):
    if not directory.exists():
        return []
    return sorted(
        item
        for item in os.listdir(directory)
        if os.path.isfile(directory / item)
    )


def prepare_file(file_to_host):
    chunk_names = split_file(file_to_host)
    if chunk_names:
        print(f"[{timestamp()}] Split '{file_to_host}' into {len(chunk_names)} chunk(s): {', '.join(chunk_names)}")
        print(f"[{timestamp()}] Starting to announce these chunks.")
    else:
        print(f"[{timestamp()}] Warning: Could not split '{file_to_host}'. Looking for existing chunk files...")
    return chunk_names


def request_shutdown(_signum=None, _frame=None):
    shutdown_event.set()


def start_announcer(username=None, file_to_host=None):
    shutdown_event.clear()
    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    if username is None:
        username = input("Enter your username: ")
    if file_to_host is None:
        file_to_host = input("Enter the file name to host: ")

    prepare_file(file_to_host)

    existing_chunks = collect_chunks()
    if not existing_chunks:
        print(f"[{timestamp()}] Error: No chunks found to announce. Hosting aborted.")
        return

    with socket_module.socket(socket_module.AF_INET, socket_module.SOCK_DGRAM) as socket:
        if BROADCAST_IP not in ("127.0.0.1", "localhost"):
            socket.setsockopt(socket_module.SOL_SOCKET, socket_module.SO_BROADCAST, 1)

        print(f"[{timestamp()}] Started announcing chunks every {ANNOUNCE_INTERVAL} seconds.")
        missing_chunks_reported = False

        while not shutdown_event.is_set():
            chunks = collect_chunks()

            if not chunks:
                if not missing_chunks_reported:
                    print(f"[{timestamp()}] No chunks found to announce, waiting...")
                    missing_chunks_reported = True
                shutdown_event.wait(ANNOUNCE_INTERVAL)
                continue

            missing_chunks_reported = False
            message = json.dumps({
                "username": username,
                "chunks": chunks
            }).encode("utf-8")

            try:
                socket.sendto(message, (BROADCAST_IP, DISCOVERY_PORT))
            except OSError as e:
                print(f"[{timestamp()}] Error sending announcement: {e}")

            shutdown_event.wait(ANNOUNCE_INTERVAL)


if __name__ == "__main__":
    start_announcer()
