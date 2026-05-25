import json
import os
import re
import socket
import time

from srcs.file_utils import split_file
from srcs.path_utils import CHUNK_DIR
from srcs.ui_utils import ts


IP = os.environ.get("BT_BROADCAST_IP", "192.168.1.255")
PORT = 6000
INTERVAL = 8
CHUNK_PATTERN = re.compile(r"^.+(?:_| )\d+$")


def collect_chunks(directory=CHUNK_DIR):
    found = []
    if not directory.exists():
        return found
    for item in os.listdir(directory):
        if not os.path.isfile(directory / item):
            continue
        if "." in item:
            continue
        if CHUNK_PATTERN.match(item):
            found.append(item)
    return sorted(found)


def prepare_file(file_to_host):
    chunk_names = split_file(file_to_host)
    if chunk_names:
        print(f"[{ts()}] Split '{file_to_host}' into {len(chunk_names)} chunk(s): {', '.join(chunk_names)}")
    else:
        print(f"[{ts()}] Warning: Could not split '{file_to_host}'. Looking for existing chunk files...")
    return chunk_names


def start_announcer(username=None, file_to_host=None):
    if username is None:
        username = input("Enter your username: ")
    if file_to_host is None:
        file_to_host = input("Enter the file name to host: ")

    prepare_file(file_to_host)

    existing_chunks = collect_chunks()
    if not existing_chunks:
        print(f"[{ts()}] Error: No chunks found to announce. Hosting aborted.")
        return

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        if IP not in ("127.0.0.1", "localhost"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while True:
            chunks = collect_chunks()

            if not chunks:
                print(f"[{ts()}] No chunks found to announce, waiting...")
                time.sleep(INTERVAL)
                continue

            message = json.dumps({
                "username": username,
                "chunks": chunks
            }).encode("utf-8")

            try:
                sock.sendto(message, (IP, PORT))
                print(f"[{ts()}] Announcement sent: {chunks}")
            except Exception as e:
                print(f"[{ts()}] Error sending announcement: {e}")

            time.sleep(INTERVAL)


if __name__ == "__main__":
    start_announcer()
