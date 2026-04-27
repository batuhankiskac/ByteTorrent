import json
import os
import socket
import time

BROADCAST_IP = "192.168.1.255"
BROADCAST_PORT = 6000
ANNOUNCE_INTERVAL = 8

def chunk_announcer():
    username = input("Enter your username: ")
    file_to_host = input("Enter the file name to host: ")

    # Ece hoca chunk parçalayan kod vericekmiş. Burada çağrılacak

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while True:
            chunks = [f for f in os.listdir() if "_" in f and "." not in f]

            payload = json.dumps({
                "username": username,
                "chunks": chunks
            }).encode("utf-8")

            try:
                udp_socket.sendto(payload, (BROADCAST_IP, BROADCAST_PORT))
                print(f"[{time.strftime('%X')}] Announcement sent: {chunks}")
            except Exception as e:
                print(f"Error sending announcement: {e}")

            time.sleep(ANNOUNCE_INTERVAL)


if __name__ == "__main__":
    chunk_announcer()
