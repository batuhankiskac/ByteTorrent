import json
import socket
import time
import base64
import os

PORT = 6001
STATE_FILE = "network_state.json"
LOG_FILE = "download_history.log"

def log_download(chunk_name, user):
 
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{current_time}] DOWNLOADED - Chunk: {chunk_name} - From: {user}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)
    print(f"[{time.strftime('%X')}] Logged: {log_entry.strip()}")

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

def download_chunk(chunk_name, state):
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

        print(f"[{time.strftime('%X')}] Connecting to {user} ({ip}) for '{chunk_name}'...")
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5.0) 
                sock.connect((ip, PORT))
                
  
                request = json.dumps({"requested_content": chunk_name})
                sock.sendall(request.encode("utf-8"))
                
         
                response_data = receive_all(sock)
                if not response_data:
                    raise socket.error("Empty response received.")
                
                response = json.loads(response_data)
                
                if "error" in response:
                    print(f"[{time.strftime('%X')}] {user} returned an error: {response['error']}")
                    continue 
                
              
                encoded_data = response.get("data", "")
                decoded_data = base64.b64decode(encoded_data)
                
                with open(chunk_name, "wb") as f:
                    f.write(decoded_data)
                    
                print(f"[{time.strftime('%X')}] Success: '{chunk_name}' was downloaded from {user} and saved.")
                log_download(chunk_name, user)
                return True 
                
        except (socket.error, socket.timeout) as e:
            print(f"[{time.strftime('%X')}] {user} ({ip}) is offline or unreachable (Error: {e}). Switching to next IP...")
        except json.JSONDecodeError:
            print(f"[{time.strftime('%X')}] Data from {user} ({ip}) could not be parsed. Switching to next IP...")

    print(f"[{time.strftime('%X')}] Failed: '{chunk_name}' could not be downloaded, all sources exhausted.")
    return False

def download_file(file_name, num_chunks=3):
    state = load_network_state()
    if not state:   
        return

    print(f"\n--- Starting download for '{file_name}' ---")
    all_success = True
    
    for i in range(1, num_chunks + 1):
        chunk_name = f"{file_name}_{i}"
        success = download_chunk(chunk_name, state)
        if not success:
            all_success = False
            break 

    if all_success:
        print(f"\n[{time.strftime('%X')}] All chunks downloaded successfully. Proceed to the merge step.")
    else:
        print(f"\n[{time.strftime('%X')}] Download incomplete. Missing chunks.")

if __name__ == "__main__":
    
    target_file = input("Enter the name of the file you want to download: ")
    download_file(target_file)