import base64
import json
import os
import socket
import time
import diffie_hellman
import pyDes


PORT = 6001
STATE_FILE = "network_state.json"
LOG_FILE = "download_history.log"


def log_download(chunk, user):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] DOWNLOADED - Chunk: {chunk} - From: {user}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(f"[{time.strftime('%X')}] Logged: {line.strip()}")


def load_network_state():
    if not os.path.exists(STATE_FILE):
        print(f"[{time.strftime('%X')}] Error: {STATE_FILE} not found.")
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[{time.strftime('%X')}] Error: {STATE_FILE} could not be read (Invalid JSON).")
        return None


def receive_all(sock):
    data = b""
    while True:
        packet = sock.recv(4096)
        if not packet:
            break
        data += packet
    return data.decode("utf-8")


def download_chunk(chunk_name, state, is_secure=False):
    chunks_map = state.get("chunks", {})
    user2ip_map = state.get("user2ip", {})

    users_with_chunk = chunks_map.get(chunk_name, [])

    if not users_with_chunk:
        print(f"[{time.strftime('%X')}] Error: '{chunk_name}' not found on the network.")
        return False

    for user in users_with_chunk:
        ip = user2ip_map.get(user)
        if not ip:
            continue

        mode = "Secure" if is_secure else "Plain"
        print(f"[{time.strftime('%X')}] Connecting [{mode}] to {user} ({ip}) for '{chunk_name}'...")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5.0)
                sock.connect((ip, PORT))

                if is_secure:
                    my_priv_key = diffie_hellman.generate_private_key()
                    my_pub_key = diffie_hellman.generate_public_key(my_priv_key)
                    sock.sendall(json.dumps({"key": str(my_pub_key)}).encode("utf-8"))

                    resp_data = sock.recv(4096).decode("utf-8")
                    server_pub_key = int(json.loads(resp_data)["key"])

                    shared_secret = diffie_hellman.generate_shared_secret(server_pub_key, my_priv_key)

                    req = json.dumps({"requested_secured_content": chunk_name})
                    sock.sendall(req.encode("utf-8"))

                    response_data = receive_all(sock)
                    response = json.loads(response_data)

                    if "error" in response:
                        print(f"[{time.strftime('%X')}] {user} returned an error: {response['error']}")
                        continue

                    encrypted_bytes = base64.b64decode(response.get("encrypted_chunk", ""))
                    des_key = str(shared_secret).zfill(8)[:8].encode("utf-8")
                    decrypted = pyDes.des(des_key, pyDes.ECB, pad=None, padmode=pyDes.PAD_PKCS5).decrypt(encrypted_bytes)

                    with open(chunk_name, "wb") as f:
                        f.write(decrypted)

                    print(f"[{time.strftime('%X')}] Success (Secure): '{chunk_name}' downloaded from {user}.")
                    log_download(chunk_name, user)
                    return True

                else:
                    request = json.dumps({"requested_content": chunk_name})
                    sock.sendall(request.encode("utf-8"))

                    response_data = receive_all(sock)
                    if not response_data:
                        raise socket.error("Empty response received.")

                    response = json.loads(response_data)

                    if "error" in response:
                        print(f"[{time.strftime('%X')}] {user} returned an error: {response['error']}")
                        continue

                    decoded_data = base64.b64decode(response.get("data", ""))

                    with open(chunk_name, "wb") as f:
                        f.write(decoded_data)

                    print(f"[{time.strftime('%X')}] Success (Plain): '{chunk_name}' downloaded from {user}.")
                    log_download(chunk_name, user)
                    return True

        except (socket.error, socket.timeout) as e:
            print(f"[{time.strftime('%X')}] {user} ({ip}) is offline or unreachable. Error: {e}")
        except json.JSONDecodeError:
            print(f"[{time.strftime('%X')}] Data from {user} ({ip}) could not be parsed.")
        except Exception as e:
            print(f"[{time.strftime('%X')}] Download error: {e}")

    print(f"[{time.strftime('%X')}] Failed: '{chunk_name}' could not be downloaded from any source.")
    return False


def download_file(file_name, is_secure=False, num_chunks=3):
    state = load_network_state()
    if not state:
        return

    print(f"\n--- Starting {'secure' if is_secure else 'plain'} download for '{file_name}' ---")
    all_success = True

    for i in range(1, num_chunks + 1):
        chunk_name = f"{file_name}_{i}"
        success = download_chunk(chunk_name, state, is_secure)
        if not success:
            all_success = False
            break

    if all_success:
        print(f"\n[{time.strftime('%X')}] All chunks downloaded successfully. Proceed to merge.")
    else:
        print(f"\n[{time.strftime('%X')}] Download incomplete. Missing chunks.")


if __name__ == "__main__":
    target = input("Enter the name of the file you want to download: ")
    download_file(target)
