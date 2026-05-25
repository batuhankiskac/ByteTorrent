import multiprocessing
import time

from srcs import content_discovery
from srcs import chunk_uploader
from srcs import main as main_module
from srcs.ui_utils import print_box_footer, print_box_title


def run_content_discovery_service(startup_pipe):
    try:
        sock = content_discovery.create_discovery_socket()
    except OSError as e:
        startup_pipe.send(("error", str(e)))
        startup_pipe.close()
        return

    startup_pipe.send(("ok", None))
    startup_pipe.close()
    content_discovery.content_discovery(sock)


def run_chunk_uploader_service(startup_pipe):
    try:
        server = chunk_uploader.create_uploader_socket()
    except OSError as e:
        startup_pipe.send(("error", str(e)))
        startup_pipe.close()
        return

    startup_pipe.send(("ok", None))
    startup_pipe.close()
    chunk_uploader.uploader(server)


def start_child_process(name, target):
    parent_pipe, child_pipe = multiprocessing.Pipe(duplex=False)
    process = multiprocessing.Process(
        target=target,
        args=(child_pipe,),
        daemon=True,
        name=name
    )
    process.start()
    child_pipe.close()

    if not parent_pipe.poll(3):
        process.terminate()
        process.join(timeout=1)
        parent_pipe.close()
        return None, "startup timed out"

    status, detail = parent_pipe.recv()
    parent_pipe.close()
    if status != "ok":
        process.join(timeout=1)
        return None, detail

    return process, None


def start_services():
    print_box_title("Starting Background Services")

    discovery_process, discovery_error = start_child_process(
        "ContentDiscovery",
        run_content_discovery_service
    )
    if discovery_error:
        print(f"  [ERROR] Content Discovery could not start on UDP 6000: {discovery_error}")
    else:
        print("  [OK] Content Discovery process started (UDP 6000)")

    uploader_process, uploader_error = start_child_process(
        "ChunkUploader",
        run_chunk_uploader_service
    )
    if uploader_error:
        print(f"  [ERROR] Chunk Uploader could not start on TCP 6001: {uploader_error}")
    else:
        print("  [OK] Chunk Uploader process started (TCP 6001)")

    processes = [p for p in (discovery_process, uploader_process) if p is not None]

    if discovery_error or uploader_error:
        for process in processes:
            process.terminate()
            process.join(timeout=1)
        print("\nOne or more background services failed to start.")
        print_box_footer()
        return None

    print("\nAll services are running as child processes.")
    print("Press Ctrl+C at any time to exit.\n")
    print_box_footer()
    time.sleep(0.5)
    return processes


def stop_services(processes):
    for process in processes:
        if process.is_alive():
            process.terminate()
        process.join(timeout=1)


def main():
    print_box_title("ByteTorrent P2P Client")

    processes = start_services()
    if processes is None:
        print("Goodbye!")
        return

    try:
        main_module.main_menu()
    except KeyboardInterrupt:
        print("\n\nShutting down ByteTorrent...")
    finally:
        stop_services(processes)
        print("Goodbye!")


if __name__ == "__main__":
    main()
