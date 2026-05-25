import base64
import json
import socket
import threading
import time
import pyDes

from srcs import diffie_hellman
from srcs.path_utils import STATE_FILE, UPLOAD_LOG, chunk_path
from srcs.ui_utils import ts


PORT = 6001
BUFSIZE = 4096


def log_upload(chunk, user):
    entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SENT - Chunk: {chunk} - To: {user}"
    with open(UPLOAD_LOG, "a", encoding="utf-8") as f:
        f.write(entry + "\n")
    print(f"[{ts()}] {entry}")


def get_user(ip):
    if not STATE_FILE.exists():
        return ip
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("ip2user", {}).get(ip, ip)
    except Exception:
        return ip


def handle_client(conn, addr):
    ip = addr[0]
    shared_secret = None

    with conn:
        try:
            while True:
                request = conn.recv(BUFSIZE).decode("utf-8")
                if not request:
                    break

                message = json.loads(request)

                if "requested content" in message:
                    chunk = message.get("requested content")
                    print(f"[{ts()}] Request received for chunk: {chunk} from {ip}")

                    file_path = chunk_path(chunk)
                    if file_path.exists():
                        with open(file_path, "rb") as f:
                            data = base64.b64encode(f.read()).decode("utf-8")

                        response = json.dumps({
                            "chunk name": chunk,
                            "data": data
                        })
                        conn.sendall(response.encode("utf-8"))
                        print(f"[{ts()}] Successfully sent {chunk}")
                        log_upload(chunk, get_user(ip))
                    else:
                        conn.sendall(json.dumps({"error": "File not found"}).encode("utf-8"))
                    break

                elif "key" in message:
                    client_pub_key = int(message["key"])
                    print(f"[{ts()}] Secure handshake initiated ({ip})")

                    my_private_key = diffie_hellman.generate_private_key()
                    my_pub_key = diffie_hellman.generate_public_key(my_private_key)
                    shared_secret = diffie_hellman.compute_shared_key(client_pub_key, my_private_key)

                    conn.sendall(json.dumps({"key": str(my_pub_key)}).encode("utf-8"))

                elif "requested secured content" in message:
                    chunk = message.get("requested secured content")
                    print(f"[{ts()}] Secure request received for chunk: {chunk} from {ip}")

                    if not shared_secret:
                        conn.sendall(json.dumps({"error": "No shared key established"}).encode("utf-8"))
                        break

                    file_path = chunk_path(chunk)
                    if file_path.exists():
                        with open(file_path, "rb") as f:
                            raw = f.read()

                        des_key = str(shared_secret).zfill(8)[:8].encode("utf-8")
                        encrypted = pyDes.des(des_key, pyDes.ECB, pad=None, padmode=pyDes.PAD_PKCS5).encrypt(raw)
                        encoded_chunk = base64.b64encode(encrypted).decode("utf-8")

                        response = json.dumps({
                            "chunk name": chunk,
                            "encrypted chunk": encoded_chunk
                        })
                        conn.sendall(response.encode("utf-8"))
                        print(f"[{ts()}] Securely sent {chunk}")
                        log_upload(chunk, get_user(ip))
                    else:
                        conn.sendall(json.dumps({"error": "File not found"}).encode("utf-8"))
                    break

        except json.JSONDecodeError:
            print(f"[{ts()}] Error: Invalid JSON from {ip}")
        except socket.error as e:
            print(f"[{ts()}] Socket error with {ip}: {e}")
        except Exception as e:
            print(f"[{ts()}] Error handling {ip}: {e}")


def create_uploader_socket():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("", PORT))
        server.listen(5)
        return server
    except Exception:
        server.close()
        raise


def uploader(server=None):
    if server is None:
        server = create_uploader_socket()

    with server:
        print(f"Chunk Uploader started. Listening on TCP port {PORT}...")

        while True:
            try:
                conn, addr = server.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            except KeyboardInterrupt:
                print("\nShutting down Chunk Uploader...")
                break
            except Exception as e:
                print(f"[{ts()}] Server error: {e}")


if __name__ == "__main__":
    uploader()
