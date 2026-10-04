"""Shared paths and settings for claude-usage-bar."""
import json
import os
import time

HOME = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HOME, "state")
CONFIG = os.path.join(HOME, "config.json")
KEEP_DAYS = 14

DEFAULTS = {
    "top_command": "",           # your old status line; runs first and stays on top
    "names": {},                 # claude-swap alias -> name shown in the bar
    "bar_width": 12,
    "usage_cache_seconds": 60,
    "recap": True,
    "recap_model": "haiku",
    "recap_every_seconds": 180,
    "recap_width": 150,
    "recap_max_lines": 3,
    "timezone": "",              # e.g. "America/Denver"; blank = this computer's time zone
}


def config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG) as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            cfg.update({k: v for k, v in loaded.items() if v is not None})
    except (OSError, ValueError):
        pass
    if not isinstance(cfg["names"], dict):
        cfg["names"] = {}
    return cfg


def state_file(session_id, ext):
    os.makedirs(STATE, exist_ok=True)
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_") or "unknown"
    return os.path.join(STATE, f"{safe}.{ext}")


def write_atomic(path, text):
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def cleanup_old_state():
    """Delete state from chats older than two weeks. Runs at most once a day."""
    os.makedirs(STATE, exist_ok=True)
    marker = os.path.join(STATE, ".last-cleanup")
    try:
        if time.time() - os.path.getmtime(marker) < 86400:
            return
    except OSError:
        pass
    open(marker, "w").close()
    for name in os.listdir(STATE):
        p = os.path.join(STATE, name)
        try:
            if os.path.isfile(p) and time.time() - os.path.getmtime(p) > KEEP_DAYS * 86400:
                os.remove(p)
        except OSError:
            pass
