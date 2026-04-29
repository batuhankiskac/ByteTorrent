import os
import time

from chunk_downloader import download_file, load_network_state


DOWNLOAD_LOG = "download_history.log"
UPLOAD_LOG = "upload_history.log"


def view_contents():
    state = load_network_state()
    if not state or not state.get("chunks"):
        print("\nNo content available on the network.")
        return

    chunks_map = state.get("chunks", {})
    contents = set()

    for name in chunks_map.keys():
        if "_" in name:
            contents.add(name.rsplit("_", 1)[0])

    print("\n--- Available Content ---")
    if not contents:
        print("  (No valid chunked files found.)")
    else:
        for c in sorted(contents):
            print(f"  - {c}")
    print("-------------------------")


def view_history():
    print("\n========== DOWNLOAD HISTORY ==========")
    if os.path.exists(DOWNLOAD_LOG):
        with open(DOWNLOAD_LOG, "r", encoding="utf-8") as f:
            print(f.read().strip() or "No downloads yet.")
    else:
        print("Download log not found.")

    print("\n========== UPLOAD HISTORY ==========")
    if os.path.exists(UPLOAD_LOG):
        with open(UPLOAD_LOG, "r", encoding="utf-8") as f:
            print(f.read().strip() or "No uploads yet.")
    else:
        print("Upload log not found.")
    print("====================================")


def main_menu():
    while True:
        print("\n--- BYTETORRENT MAIN MENU ---")
        print("1. View available content")
        print("2. Download content")
        print("3. View history")
        print("4. Exit")

        choice = input("Select an option (1-4): ")

        if choice == "1":
            view_contents()

        elif choice == "2":
            target = input("Enter file name to download (e.g. forest): ")
            secure = input("Secure download? (y/n): ").strip().lower()
            is_secure = (secure == "y")

            if is_secure:
                print("\n[INFO] Secure download (Diffie-Hellman) will be added in Phase 3.")
            else:
                download_file(target)

        elif choice == "3":
            view_history()

        elif choice == "4":
            print("Shutting down ByteTorrent...")
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    main_menu()
