import base64
import binascii
import json
import os
import socket as socket_module
import time
from typing import Any

import pyDes

from srcs import diffie_hellman
from srcs.file_utils import chunk_name, merge_chunks
from srcs.path_utils import DOWNLOAD_LOG, STATE_FILE, chunk_path
from srcs.ui_utils import print_box_up, timestamp


PORT = 6001


def log_download(chunk: str, user: str, ip: str) -> None:
    entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] RECEIVED - Chunk: {chunk} - From: {user} - IP: {ip}"
    with open(DOWNLOAD_LOG, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def load_state() -> dict[str, Any] | None:
    if not STATE_FILE.exists():
        print(f"[{timestamp()}] Error: {STATE_FILE} not found.")
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[{timestamp()}] Error: {STATE_FILE} could not be read (Invalid JSON).")
        return None


def receive_all(socket: socket_module.socket) -> str:
    data = b""
    while True:
        packet = socket.recv(4096)
        if not packet:
            break
        data += packet
    return data.decode("utf-8")


def download_secure(socket: socket_module.socket, requested_chunk: str) -> bool:
    my_private_key = diffie_hellman.generate_private_key()
    my_public_key = diffie_hellman.generate_public_key(my_private_key)
    socket.sendall(json.dumps({"key": str(my_public_key)}).encode("utf-8"))

    response_data = socket.recv(4096).decode("utf-8")
    server_pub_key = int(json.loads(response_data)["key"])

    shared_secret = diffie_hellman.compute_shared_key(server_pub_key, my_private_key)

    socket.sendall(json.dumps({"requested secured content": requested_chunk}).encode("utf-8"))

    response_data = receive_all(socket)
    response = json.loads(response_data)

    if "error" in response:
        raise RuntimeError(f"Server returned error: {response['error']}")

    encrypted_bytes = base64.b64decode(response.get("encrypted chunk", ""))
    des_key = str(shared_secret).zfill(8)[:8].encode("utf-8")
    decrypted = pyDes.des(des_key, pyDes.ECB, pad=None, padmode=pyDes.PAD_PKCS5).decrypt(encrypted_bytes)

    with open(chunk_path(requested_chunk), "wb") as f:
        f.write(decrypted)

    return True


def download_plain(socket: socket_module.socket, requested_chunk: str) -> bool:
    socket.sendall(json.dumps({"requested content": requested_chunk}).encode("utf-8"))

    response_data = receive_all(socket)
    if not response_data:
        raise socket_module.error("Empty response received.")

    response = json.loads(response_data)

    if "error" in response:
        raise RuntimeError(f"Server returned error: {response['error']}")

    decoded_data = base64.b64decode(response.get("data", ""))

    with open(chunk_path(requested_chunk), "wb") as f:
        f.write(decoded_data)

    return True


def download_chunk(chunk_label: str, state: dict[str, Any], is_secure: bool = False) -> bool:
    chunks_map = state.get("chunks", {})
    user2ip_map = state.get("user2ip", {})

    users_with_chunk = chunks_map.get(chunk_label, [])

    if not users_with_chunk:
        print(f"[{timestamp()}] Error: '{chunk_label}' not found on the network.")
        return False

    for user in users_with_chunk:
        ip = user2ip_map.get(user)
        if not ip:
            continue

        print(f"[{timestamp()}] Requesting chunk '{chunk_label}' from {user}.")

        try:
            with socket_module.socket(socket_module.AF_INET, socket_module.SOCK_STREAM) as socket:
                socket.settimeout(5.0)
                socket.connect((ip, PORT))

                if is_secure:
                    download_secure(socket, chunk_label)
                else:
                    download_plain(socket, chunk_label)

                log_download(chunk_label, user, ip)
                return True

        except (socket_module.error, ValueError, KeyError, RuntimeError, binascii.Error):
            print(f"[{timestamp()}] Chunk {chunk_label} cannot be downloaded from {user}.")

    print(f"[{timestamp()}] CHUNK {chunk_label} CANNOT BE DOWNLOADED FROM ONLINE PEERS.")
    return False


def download_file(file_name: str, is_secure: bool = False, num_chunks: int = 3) -> None:
    requested_file: str = file_name.strip()
    content_name: str = os.path.splitext(requested_file)[0]
    state = load_state()
    if not state:
        return

    mode = "Secure" if is_secure else "Plain"
    print_box_up(f"Starting {mode} Download: {content_name}")
    all_success = True

    for i in range(1, num_chunks + 1):
        current_chunk = chunk_name(content_name, i)
        success = download_chunk(current_chunk, state, is_secure)
        if not success:
            all_success = False
            break

    if all_success:
        merged_path = merge_chunks(content_name, num_chunks, output_name=requested_file or None)
        if merged_path:
            print(f"\n[{timestamp()}] File successfully downloaded and merged to '{merged_path}'")
        else:
            print(f"\n[{timestamp()}] Download complete but merge failed.")
    else:
        print(f"\n[{timestamp()}] Download incomplete. Missing chunks.")


if __name__ == "__main__":
    target = input("Enter the name of the file you want to download: ")
    download_file(target)
