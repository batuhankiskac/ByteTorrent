import base64
import binascii
import json
import signal
import socket
import threading
import time

import pyDes

from srcs import diffie_hellman
from srcs.config import BUFFER_SIZE, UPLOAD_PORT
from srcs.path_utils import UPLOAD_LOG, chunk_path
from srcs.state_store import get_user_by_ip
from srcs.ui_utils import timestamp


shutdown_event = threading.Event()


def log_upload(chunk, user):
    entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SENT - Chunk: {chunk} - To: {user}"
    with open(UPLOAD_LOG, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def send_chunk(conn, chunk, user, shared_secret=None):
    file_path = chunk_path(chunk)
    if not file_path.exists():
        conn.sendall(json.dumps({"error": "File not found"}).encode("utf-8"))
        return

    with open(file_path, "rb") as f:
        raw = f.read()

    response = {"chunk name": chunk}
    if shared_secret is None:
        response["data"] = base64.b64encode(raw).decode("utf-8")
    else:
        des_key = str(shared_secret).zfill(8)[:8].encode("utf-8")
        encrypted = pyDes.des(des_key, pyDes.ECB, pad=None, padmode=pyDes.PAD_PKCS5).encrypt(raw)
        response["encrypted chunk"] = base64.b64encode(encrypted).decode("utf-8")

    conn.sendall(json.dumps(response).encode("utf-8"))
    log_upload(chunk, user)


def handle_client(conn, addr):
    ip = addr[0]
    user = get_user_by_ip(ip)
    shared_secret = None

    with conn:
        try:
            while True:
                request = conn.recv(BUFFER_SIZE).decode("utf-8")
                if not request:
                    break

                message = json.loads(request)

                if "requested content" in message:
                    chunk = message.get("requested content")
                    print(f"[{timestamp()}] {user} requested chunk: {chunk}")
                    send_chunk(conn, chunk, user)
                    break

                elif "key" in message:
                    client_pub_key = int(message["key"])

                    my_private_key = diffie_hellman.generate_private_key()
                    my_public_key = diffie_hellman.generate_public_key(my_private_key)
                    shared_secret = diffie_hellman.compute_shared_key(client_pub_key, my_private_key)

                    conn.sendall(json.dumps({"key": str(my_public_key)}).encode("utf-8"))

                elif "requested secured content" in message:
                    chunk = message.get("requested secured content")
                    print(f"[{timestamp()}] {user} requested chunk: {chunk}")

                    if not shared_secret:
                        conn.sendall(json.dumps({"error": "No shared key established"}).encode("utf-8"))
                        break

                    send_chunk(conn, chunk, user, shared_secret)
                    break

        except (json.JSONDecodeError, ValueError, binascii.Error):
            print(f"[{timestamp()}] Error: Invalid JSON from {ip}")
        except socket.error as e:
            print(f"[{timestamp()}] Socket error with {ip}: {e}")


def create_uploader_socket():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("", UPLOAD_PORT))
        server.listen(5)
        return server
    except OSError:
        server.close()
        raise


def request_shutdown(_signum=None, _frame=None):
    shutdown_event.set()


def uploader(server=None):
    shutdown_event.clear()
    if server is None:
        server = create_uploader_socket()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    with server:
        server.settimeout(1)
        while not shutdown_event.is_set():
            try:
                conn, addr = server.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except OSError as e:
                if shutdown_event.is_set():
                    break
                print(f"[{timestamp()}] Server error: {e}")


if __name__ == "__main__":
    uploader()
