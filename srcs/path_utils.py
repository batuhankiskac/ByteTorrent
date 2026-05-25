from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = PROJECT_ROOT / "network_state.json"
DOWNLOAD_LOG = PROJECT_ROOT / "download_history.log"
UPLOAD_LOG = PROJECT_ROOT / "upload_history.log"
CHUNK_DIR = PROJECT_ROOT / "chunks"


def ensure_chunk_dir():
    CHUNK_DIR.mkdir(exist_ok=True)
    return CHUNK_DIR


def chunk_path(chunk_name):
    return ensure_chunk_dir() / chunk_name
