import sys
import os
import threading
import time


_SRCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "srcs")
if _SRCS_DIR not in sys.path:
    sys.path.insert(0, _SRCS_DIR)

import content_discovery
import chunk_uploader
import main as main_module


def _start_services():
    print("\nStarting background services...\n")

    discovery_thread = threading.Thread(
        target=content_discovery.content_discovery,
        daemon=True,
        name="ContentDiscovery"
    )
    discovery_thread.start()
    print("  [OK] Content Discovery service started (UDP 6000)")
    time.sleep(0.3)

    uploader_thread = threading.Thread(
        target=chunk_uploader.uploader,
        daemon=True,
        name="ChunkUploader"
    )
    uploader_thread.start()
    print("  [OK] Chunk Uploader service started (TCP 6001)")
    time.sleep(0.3)

    print("\nAll services are running in the background.")
    print("Press Ctrl+C at any time to exit.\n")
    time.sleep(0.5)


def _main():
    print("=" * 50)
    print("  ByteTorrent P2P Client")
    print("=" * 50)

    _start_services()

    try:
        main_module.main_menu()
    except KeyboardInterrupt:
        print("\n\nShutting down ByteTorrent...")
    finally:
        print("Goodbye!")


if __name__ == "__main__":
    _main()
