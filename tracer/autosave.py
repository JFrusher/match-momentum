"""Atomic disk persistence + rehydrate-on-launch.

Write-temp-then-os.replace keeps the session file always whole: a crash
mid-write leaves the previous good file untouched. A corrupt/missing file
loads as None — the app then offers a fresh start, which is the intended
crash-recovery behavior, not a swallowed error.
"""

import json
import os
from pathlib import Path

SESSION_DIR = Path(__file__).parent / "sessions"
SESSION_FILE = SESSION_DIR / "session.json"


def save_session(state: dict, path: Path = SESSION_FILE):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def load_session(path: Path = SESSION_FILE):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def clear_session(path: Path = SESSION_FILE):
    path.unlink(missing_ok=True)
