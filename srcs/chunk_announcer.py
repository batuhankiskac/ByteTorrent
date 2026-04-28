import json
import os
import socket
import time


IP = "192.168.1.255"
PORT = 6000
INTERVAL = 8


def announcer():
    username = input("Enter your username: ")
    file_to_host = input("Enter the file name to host: ")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while True:
            chunks = [f for f in os.listdir() if "_" in f and "." not in f]

            msg = json.dumps({
                "username": username,
                "chunks": chunks
            }).encode("utf-8")

            try:
                sock.sendto(msg, (IP, PORT))
                print(f"[{time.strftime('%X')}] Announcement sent: {chunks}")
            except Exception as e:
                print(f"Error sending announcement: {e}")

            time.sleep(INTERVAL)


if __name__ == "__main__":
    announcer()
