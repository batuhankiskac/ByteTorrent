import atexit
import multiprocessing
import signal
import time

from srcs import content_discovery
from srcs import chunk_uploader
from srcs import main as main_module
from srcs.ui_utils import print_box_footer, print_box_title


active_processes: list[multiprocessing.Process] = []
shutdown_started = False


def run_content_discovery(startup_pipe):
    try:
        sock = content_discovery.create_discovery_socket()
    except OSError as e:
        startup_pipe.send(("error", str(e)))
        startup_pipe.close()
        return

    startup_pipe.send(("ok", None))
    startup_pipe.close()
    content_discovery.content_discovery(sock)


def run_chunk_uploader(startup_pipe):
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
        run_content_discovery
    )
    if discovery_error:
        print(f"  [ERROR] Content Discovery could not start on UDP 6000: {discovery_error}")
    else:
        print("  [OK] Content Discovery process started (UDP 6000)")

    uploader_process, uploader_error = start_child_process(
        "ChunkUploader",
        run_chunk_uploader
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


def shutdown_and_exit(signum: int | None = None, _frame=None):
    global shutdown_started
    if shutdown_started:
        return

    shutdown_started = True
    if active_processes:
        print("\nShutting down ByteTorrent...")
        stop_services(active_processes)

    if signum is not None:
        raise SystemExit(0)


def configure_shutdown_hooks():
    atexit.register(shutdown_and_exit)
    signal.signal(signal.SIGINT, shutdown_and_exit)
    signal.signal(signal.SIGTERM, shutdown_and_exit)


def main():
    global active_processes
    configure_shutdown_hooks()
    print_box_title("ByteTorrent P2P Client")

    processes = start_services()
    if processes is None:
        print("Goodbye!")
        return

    active_processes = processes

    try:
        main_module.main_menu()
    finally:
        stop_services(processes)
        active_processes = []
        print("Goodbye!")


if __name__ == "__main__":
    main()
