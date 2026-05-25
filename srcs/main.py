import multiprocessing

from srcs.chunk_downloader import download_file, load_state
from srcs import chunk_announcer
from srcs.file_utils import parse_chunk_base
from srcs.path_utils import DOWNLOAD_LOG, UPLOAD_LOG
from srcs.ui_utils import print_box_footer, print_box_title


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

    print_box_title("Available Content")
    if not contents:
        print("  (No valid chunked files found.)")
    else:
        for content in sorted(contents):
            print(f"  - {content}")
    print_box_footer()


def view_users():
    state = load_state()
    if not state or not state.get("ip2user"):
        print("\nNo users discovered yet.")
        return

    print_box_title("Available Users")
    for ip, user in sorted(state.get("ip2user", {}).items(), key=lambda item: item[1]):
        print(f"  - {user} ({ip})")
    print_box_footer()


def view_history():
    print_box_title("Download History")
    if DOWNLOAD_LOG.exists():
        with open(DOWNLOAD_LOG, "r", encoding="utf-8") as f:
            content = f.read().strip()
            print(content or "No downloads yet.")
    else:
        print("Download log not found.")
    print_box_footer()
    print_box_title("Upload History")
    if UPLOAD_LOG.exists():
        with open(UPLOAD_LOG, "r", encoding="utf-8") as f:
            content = f.read().strip()
            print(content or "No uploads yet.")
    else:
        print("Upload log not found.")
    print_box_footer()


def main_menu():
    while True:
        print_box_title("ByteTorrent Main Menu")
        print("1. View users")
        print("2. View available content")
        print("3. Download content")
        print("4. View history")
        print("5. Host a file")
        print("6. Exit")
        print_box_footer()

        choice = input("Select an option (1-6): ").strip()

        if choice == "1":
            view_users()

        elif choice == "2":
            view_contents()

        elif choice == "3":
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

        elif choice == "4":
            view_history()

        elif choice == "5":
            target = input("Enter file name to host: ").strip()
            if target:
                username = input("Enter your username: ").strip()
                if username:
                    global announcer_process
                    if announcer_process and announcer_process.is_alive():
                        chunk_announcer.prepare_file(target)
                        print(f"Added '{target}' to hosted chunks.")
                    else:
                        announcer_process = multiprocessing.Process(
                            target=chunk_announcer.start_announcer,
                            args=(username, target),
                            daemon=True,
                            name="ChunkAnnouncer"
                        )
                        announcer_process.start()
                        print(f"Hosting '{target}' as '{username}' in a child process...")
                else:
                    print("Username cannot be empty.")
            else:
                print("File name cannot be empty.")

        elif choice == "6":
            print("Shutting down ByteTorrent...")
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    main_menu()
