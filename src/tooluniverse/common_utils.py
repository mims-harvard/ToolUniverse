import os
import json
import time
import threading
import base64
import io
from typing import Any, Dict, Tuple

_LOCK = threading.Lock()


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def vsd_generated_path() -> str:
    base = os.environ.get("TOOLUNIVERSE_VSD_DIR") or os.path.join(
        os.path.expanduser("~"), ".tooluniverse", "vsd"
    )
    ensure_dir(base)
    return os.path.join(base, "generated_tools.json")


def read_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path: str, data: Any):
    ensure_dir(os.path.dirname(path))
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)


def b64_png(png_bytes: bytes) -> str:
    return base64.b64encode(png_bytes).decode("ascii")
