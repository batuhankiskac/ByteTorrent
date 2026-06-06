import multiprocessing

from srcs.chunk_downloader import download_file
from srcs import chunk_announcer
from srcs.file_utils import parse_chunk_base
from srcs.path_utils import DOWNLOAD_LOG, UPLOAD_LOG
from srcs.state_store import load_state
from srcs.ui_utils import print_box_bottom, print_box_up


announcer_process: multiprocessing.Process | None = None


def stop_announcer():
    global announcer_process
    if announcer_process and announcer_process.is_alive():
        announcer_process.terminate()
        announcer_process.join(timeout=1)
    announcer_process = None


def view_contents():
    state = load_state()
    if not state or not state.get("chunks"):
        print("\nNo content available on the network.")
        return

    chunks_map = state.get("chunks", {})
    contents = set()

    for name in chunks_map.keys():
        base = parse_chunk_base(name)
        if base:
            contents.add(base)

    print_box_up("Available Content")
    if not contents:
        print("  (No valid chunked files found.)")
    else:
        for content in sorted(contents):
            print(f"  - {content}")
    print_box_bottom()


def view_users():
    state = load_state()
    if not state or not state.get("ip2user"):
        print("\nNo users discovered yet.")
        return

    print_box_up("Available Users")
    for ip, user in sorted(state.get("ip2user", {}).items(), key=lambda item: item[1]):
        print(f"  - {user} ({ip})")
    print_box_bottom()


def read_log(path, empty_message):
    if not path.exists():
        return empty_message
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip() or empty_message


def view_history():
    print_box_up("History")
    print("Download History:")
    print(read_log(DOWNLOAD_LOG, "No downloads yet."))
    print("\nUpload History:")
    print(read_log(UPLOAD_LOG, "No uploads yet."))
    print_box_bottom()


def handle_download():
    target = input("Enter file name to download (e.g. forest): ").strip()
    secure = input("Secure download? (y/n): ").strip().lower()

    download_process = multiprocessing.Process(
        target=download_file,
        args=(target,),
        kwargs={"is_secure": secure == "y"},
        name="ChunkDownloader"
    )
    download_process.start()
    download_process.join()


def handle_host_file():
    target = input("Enter file name to host: ").strip()
    if not target:
        print("File name cannot be empty.")
        return

    username = input("Enter your username: ").strip()
    if not username:
        print("Username cannot be empty.")
        return

    global announcer_process
    if announcer_process and announcer_process.is_alive():
        chunk_announcer.prepare_file(target)
        print(f"Added '{target}' to hosted chunks.")
        return

    new_announcer = multiprocessing.Process(
        target=chunk_announcer.start_announcer,
        args=(username, target),
        daemon=True,
        name="ChunkAnnouncer"
    )
    new_announcer.start()
    announcer_process = new_announcer
    print(f"Hosting '{target}' as '{username}' in a child process...")


def main_menu():
    try:
        while True:
            print_box_up("ByteTorrent Main Menu")
            print("1. View users")
            print("2. View available content")
            print("3. Download content")
            print("4. View history")
            print("5. Host a file")
            print("6. Exit")
            print_box_bottom()

            choice = input("Select an option (1-6): ").strip()

            if choice == "1":
                view_users()

            elif choice == "2":
                view_contents()

            elif choice == "3":
                handle_download()

            elif choice == "4":
                view_history()

            elif choice == "5":
                handle_host_file()

            elif choice == "6":
                print("Shutting down ByteTorrent...")
                break
            else:
                print("Invalid option. Please try again.")
    finally:
        stop_announcer()


if __name__ == "__main__":
    main_menu()
