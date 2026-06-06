import json
from typing import Any

from srcs.path_utils import STATE_FILE
from srcs.ui_utils import timestamp


def load_state(default=None) -> Any:
    if not STATE_FILE.exists():
        if default is None:
            print(f"[{timestamp()}] Error: {STATE_FILE} not found.")
        return default

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        if default is None:
            print(f"[{timestamp()}] Error: {STATE_FILE} could not be read (Invalid JSON).")
        return default


def save_state(state) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)


def get_user_by_ip(ip):
    state = load_state(default={})
    return state.get("ip2user", {}).get(ip, ip)
