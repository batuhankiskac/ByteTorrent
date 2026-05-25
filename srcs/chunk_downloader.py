import base64
import json
import os
import socket
import time
import pyDes

try:
    from . import diffie_hellman
    from .file_utils import chunk_name, merge_chunks
    from .path_utils import DOWNLOAD_LOG, STATE_FILE, chunk_path
    from .ui_utils import print_box_title, ts
except ImportError:
    from pathlib import Path
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from srcs import diffie_hellman
    from srcs.file_utils import chunk_name, merge_chunks
    from srcs.path_utils import DOWNLOAD_LOG, STATE_FILE, chunk_path
    from srcs.ui_utils import print_box_title, ts

PORT = 6001


def log_download(chunk, user, ip):
    entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] RECEIVED - Chunk: {chunk} - From: {user} ({ip})"
    with open(DOWNLOAD_LOG, "a", encoding="utf-8") as f:
        f.write(entry + "\n")
    print(f"[{ts()}] {entry}")


def load_state():
    if not STATE_FILE.exists():
        print(f"[{ts()}] Error: {STATE_FILE} not found.")
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[{ts()}] Error: {STATE_FILE} could not be read (Invalid JSON).")
        return None


def receive_all(sock):
    data = b""
    while True:
        packet = sock.recv(4096)
        if not packet:
            break
        data += packet
    return data.decode("utf-8")


def download_secure(sock, chunk_name):
    my_priv_key = diffie_hellman.generate_private_key()
    my_pub_key = diffie_hellman.generate_public_key(my_priv_key)
    sock.sendall(json.dumps({"key": str(my_pub_key)}).encode("utf-8"))

    resp_data = sock.recv(4096).decode("utf-8")
    server_pub_key = int(json.loads(resp_data)["key"])

    shared_secret = diffie_hellman.compute_shared_key(server_pub_key, my_priv_key)

    sock.sendall(json.dumps({"requested secured content": chunk_name}).encode("utf-8"))

    response_data = receive_all(sock)
    response = json.loads(response_data)

    if "error" in response:
        raise RuntimeError(f"Server returned error: {response['error']}")

    encrypted_bytes = base64.b64decode(response.get("encrypted chunk", ""))
    des_key = str(shared_secret).zfill(8)[:8].encode("utf-8")
    decrypted = pyDes.des(des_key, pyDes.ECB, pad=None, padmode=pyDes.PAD_PKCS5).decrypt(encrypted_bytes)

    with open(chunk_path(chunk_name), "wb") as f:
        f.write(decrypted)

    return True


def download_plain(sock, chunk_name):
    sock.sendall(json.dumps({"requested content": chunk_name}).encode("utf-8"))

    response_data = receive_all(sock)
    if not response_data:
        raise socket.error("Empty response received.")

    response = json.loads(response_data)

    if "error" in response:
        raise RuntimeError(f"Server returned error: {response['error']}")

    decoded_data = base64.b64decode(response.get("data", ""))

    with open(chunk_path(chunk_name), "wb") as f:
        f.write(decoded_data)

    return True


def download_chunk(chunk_name, state, is_secure=False):
    chunks_map = state.get("chunks", {})
    user2ip_map = state.get("user2ip", {})

    users_with_chunk = chunks_map.get(chunk_name, [])
    if not users_with_chunk and " " in chunk_name:
        legacy_name = chunk_name.replace(" ", "_")
        users_with_chunk = chunks_map.get(legacy_name, [])
    else:
        legacy_name = chunk_name

    if not users_with_chunk:
        print(f"[{ts()}] Error: '{chunk_name}' not found on the network.")
        return False

    for user in users_with_chunk:
        ip = user2ip_map.get(user)
        if not ip:
            continue

        mode = "Secure" if is_secure else "Plain"
        print(f"[{ts()}] Connecting [{mode}] to {user} ({ip}) for '{chunk_name}'...")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5.0)
                sock.connect((ip, PORT))

                if is_secure:
                    download_secure(sock, legacy_name)
                else:
                    download_plain(sock, legacy_name)

                print(f"[{ts()}] Success ({mode}): '{chunk_name}' downloaded from {user}.")
                log_download(chunk_name, user, ip)
                return True

        except (socket.error, socket.timeout) as e:
            print(f"[{ts()}] Chunk {chunk_name} cannot be downloaded from {user}. Error: {e}")
        except json.JSONDecodeError:
            print(f"[{ts()}] Chunk {chunk_name} cannot be downloaded from {user}. Data could not be parsed.")
        except RuntimeError as e:
            print(f"[{ts()}] Chunk {chunk_name} cannot be downloaded from {user}. {e}")
        except Exception as e:
            print(f"[{ts()}] Chunk {chunk_name} cannot be downloaded from {user}. Error: {e}")

    print(f"[{ts()}] CHUNK {chunk_name} CANNOT BE DOWNLOADED FROM ONLINE PEERS.")
    return False


def download_file(file_name, is_secure=False, num_chunks=3):
    requested_file = file_name.strip()
    file_name = os.path.splitext(requested_file)[0]
    state = load_state()
    if not state:
        return

    mode = "Secure" if is_secure else "Plain"
    print_box_title(f"Starting {mode} Download: {file_name}")
    all_success = True

    for i in range(1, num_chunks + 1):
        current_chunk = chunk_name(file_name, i)
        success = download_chunk(current_chunk, state, is_secure)
        if not success:
            all_success = False
            break

    if all_success:
        merged_path = merge_chunks(file_name, num_chunks, output_name=requested_file or None)
        if merged_path:
            print(f"\n[{ts()}] File successfully downloaded and merged to '{merged_path}'")
        else:
            print(f"\n[{ts()}] Download complete but merge failed.")
    else:
        print(f"\n[{ts()}] Download incomplete. Missing chunks.")


if __name__ == "__main__":
    target = input("Enter the name of the file you want to download: ")
    download_file(target)
