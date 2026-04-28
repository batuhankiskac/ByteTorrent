import base64
import json
import os
import socket
import threading
import time


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

    with conn:
        try:
            req = conn.recv(BUFSIZE).decode("utf-8")
            if not req:
                return

            msg = json.loads(req)
            chunk = msg.get("requested_content")

            if chunk:
                print(f"[{time.strftime('%X')}] Request received for chunk: {chunk} from {ip}")

                if os.path.exists(chunk):
                    with open(chunk, "rb") as f:
                        data = base64.b64encode(f.read()).decode("utf-8")

                    resp = json.dumps({
                        "chunk_name": chunk,
                        "data": data
                    })
                    conn.sendall(resp.encode("utf-8"))
                    print(f"[{time.strftime('%X')}] Successfully sent {chunk} to {ip}")
                    log(chunk, get_user(ip))
                else:
                    print(f"[{time.strftime('%X')}] Error: Chunk '{chunk}' not found.")
                    conn.sendall(json.dumps({"error": "File not found"}).encode("utf-8"))

            elif "key" in msg or "requested_secured_content" in msg:
                print(f"[{time.strftime('%X')}] Secure request received. (Phase 3)")

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
