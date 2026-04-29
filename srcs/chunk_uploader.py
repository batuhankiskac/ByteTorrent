import base64
import json
import os
import socket
import threading
import time
import diffie_hellman
import pyDes


PORT = 6001
BUFSIZE = 4096
LOG = "upload_history.log"
STATE = "network_state.json"


def log(chunk, user):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SENT - Chunk: {chunk} - To: {user}\n"
    with open(LOG, "a") as f:
        f.write(line)
    print(f"[{time.strftime('%X')}] Logged: {line.strip()}")


def get_user(ip):
    if not os.path.exists(STATE):
        return ip
    try:
        with open(STATE, "r") as f:
            return json.load(f).get("ip2user", {}).get(ip, ip)
    except Exception:
        return ip


def handle(conn, addr):
    ip = addr[0]
    shared_secret = None

    with conn:
        try:
            while True:
                req = conn.recv(BUFSIZE).decode("utf-8")
                if not req:
                    break

                msg = json.loads(req)

                if "requested_content" in msg:
                    chunk = msg.get("requested_content")
                    print(f"[{time.strftime('%X')}] Request received for chunk: {chunk} from {ip}")

                    if os.path.exists(chunk):
                        with open(chunk, "rb") as f:
                            data = base64.b64encode(f.read()).decode("utf-8")

                        resp = json.dumps({
                            "chunk name": chunk,
                            "data": data
                        })
                        conn.sendall(resp.encode("utf-8"))
                        print(f"[{time.strftime('%X')}] Successfully sent {chunk}")
                        log(chunk, get_user(ip))
                    else:
                        conn.sendall(json.dumps({"error": "File not found"}).encode("utf-8"))
                    break

                elif "key" in msg:
                    client_pub_key = int(msg["key"])
                    print(f"[{time.strftime('%X')}] Secure handshake initiated ({ip})")

                    my_private_key = diffie_hellman.generate_private_key()
                    my_pub_key = diffie_hellman.generate_public_key(my_private_key)
                    shared_secret = diffie_hellman.generate_shared_secret(client_pub_key, my_private_key)

                    resp = json.dumps({"key": str(my_pub_key)})
                    conn.sendall(resp.encode("utf-8"))

                elif "requested secured content" in msg:
                    chunk = msg.get("requested_secured_content")
                    print(f"[{time.strftime('%X')}] Secure request received for chunk: {chunk} from {ip}")

                    if not shared_secret:
                        conn.sendall(json.dumps({"error": "No shared key established"}).encode("utf-8"))
                        break

                    if os.path.exists(chunk):
                        with open(chunk, "rb") as f:
                            raw = f.read()

                        des_key = str(shared_secret).zfill(8)[:8].encode("utf-8")
                        encrypted = pyDes.des(des_key, pyDes.ECB, pad=None, padmode=pyDes.PAD_PKCS5).encrypt(raw)
                        safe = base64.b64encode(encrypted).decode("utf-8")

                        resp = json.dumps({
                            "chunk name": chunk,
                            "encrypted chunk": safe
                        })
                        conn.sendall(resp.encode("utf-8"))
                        print(f"[{time.strftime('%X')}] Securely sent {chunk}")
                        log(chunk, get_user(ip))
                    else:
                        conn.sendall(json.dumps({"error": "File not found"}).encode("utf-8"))
                    break

        except json.JSONDecodeError:
            print(f"[{time.strftime('%X')}] Error: Invalid JSON from {ip}")
        except socket.error as e:
            print(f"[{time.strftime('%X')}] Socket error with {ip}: {e}")
        except Exception as e:
            print(f"[{time.strftime('%X')}] Error handling {ip}: {e}")


def uploader():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("", PORT))
        srv.listen(5)

        print(f"Chunk Uploader started. Listening on TCP port {PORT}...")

        while True:
            try:
                conn, addr = srv.accept()
                threading.Thread(target=handle, args=(conn, addr), daemon=True).start()
            except KeyboardInterrupt:
                print("\nShutting down Chunk Uploader...")
                break
            except Exception as e:
                print(f"[{time.strftime('%X')}] Server error: {e}")


if __name__ == "__main__":
    uploader()
