import json
import socket
import threading
import time


PORT = 6000
BUFSIZE = 4096
INTERVAL = 60
STATE = "network_state.json"


ip2user = {}
user2ip = {}
chunks = {}

lock = threading.Lock()


def save():
    state = {
        "ip2user": ip2user,
        "user2ip": user2ip,
        "chunks": chunks
    }
    with open(STATE, "w") as f:
        json.dump(state, f, indent=4)


def cleanup():
    global ip2user, user2ip, chunks
    while True:
        time.sleep(INTERVAL)
        with lock:
            ip2user.clear()
            user2ip.clear()
            chunks.clear()
            save()
        print(f"[{time.strftime('%X')}] Recency Check: State cleared.")


def content_discovery():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", PORT))

        threading.Thread(target=cleanup, daemon=True).start()

        print(f"Content Discovery started. Listening on UDP port {PORT}...")

        while True:
            try:
                data, addr = sock.recvfrom(BUFSIZE)
                ip = addr[0]

                msg = json.loads(data.decode("utf-8"))
                user = msg.get("username")
                chunk_list = msg.get("chunks", [])

                with lock:
                    ip2user[ip] = user
                    user2ip[user] = ip

                    for chunk in chunk_list:
                        users = chunks.setdefault(chunk, [])
                        if user not in users:
                            users.append(user)

                    save()

                print(f"[{time.strftime('%X')}] Peer Found: {user} ({ip}) hosts {', '.join(chunk_list)}")

            except json.JSONDecodeError:
                print(f"[{time.strftime('%X')}] Error: Invalid JSON from {addr}")
            except socket.error as e:
                print(f"[{time.strftime('%X')}] Socket error: {e}")
            except KeyboardInterrupt:
                print("\nShutting down Content Discovery...")
                break
            except Exception as e:
                print(f"[{time.strftime('%X')}] Error: {e}")


if __name__ == "__main__":
    content_discovery()
