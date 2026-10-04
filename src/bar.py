#!/usr/bin/env python3
"""Claude Code status line: your old bar, then a session recap, then one usage line per account."""
import json
import os
import subprocess
import sys
import textwrap
import time

from common import STATE, config, state_file, write_atomic

RESET, DIM, BOLD = "\033[0m", "\033[2m", "\033[1m"
GREEN, YELLOW, RED = "\033[38;5;114m", "\033[38;5;179m", "\033[38;5;167m"
GREY, EMPTY, ORANGE, BLUE = "\033[38;5;245m", "\033[38;5;238m", "\033[38;5;173m", "\033[38;5;110m"


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def color(pct):
    return RED if pct >= 90 else YELLOW if pct >= 70 else GREEN


def bar(label, pct, when, width):
    filled = min(width, max(0, round(pct / 100 * width)))
    c = color(pct)
    return (f"{GREY}{label}{RESET} {c}{'━' * filled}{EMPTY}{'─' * (width - filled)}{RESET} "
            f"{c}{pct:>3.0f}%{RESET} {GREY}{when or '':<6}{RESET}")


def usage(cfg):
    """Read claude-swap usage. Saved for a minute, and a failed read also waits a minute before retrying."""
    cache = os.path.join(STATE, "cswap.json")
    failed = os.path.join(STATE, "cswap.failed")

    def fresh(path):
        try:
            return time.time() - os.path.getmtime(path) < cfg["usage_cache_seconds"]
        except OSError:
            return False

    def cached():
        try:
            with open(cache) as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    if fresh(cache) or fresh(failed):
        return cached()
    os.makedirs(STATE, exist_ok=True)
    open(failed, "w").close()  # claim this refresh so other chats don't run cswap at the same moment
    try:
        out = subprocess.run(["cswap", "list", "--json"], capture_output=True, text=True, timeout=8).stdout
        json.loads(out)
        write_atomic(cache, out)
        os.remove(failed)
    except Exception:
        pass
    return cached()


def account_line(a, name, pad, w):
    mark = f"{GREEN}●{RESET} " if a.get("active") else "  "
    u = a.get("usage") or {}
    if a.get("usageStatus") != "ok" or not u:
        return f"{mark}{BOLD}{name:<{pad}}{RESET}  {GREY}no data ({a.get('usageStatus')}){RESET}"
    windows = [("5h", u.get("fiveHour")), ("week", u.get("sevenDay"))]
    windows += [(s.get("name") or "model", s) for s in u.get("scoped") or [] if isinstance(s, dict)]
    parts = []
    for label, win in windows:
        pct = num((win or {}).get("pct"))
        if pct is not None:
            parts.append(bar(label, pct, win.get("countdown"), w))
    sp = u.get("spend") or {}
    used, limit = num(sp.get("used")), num(sp.get("limit"))
    if used is not None and limit:
        c = color(num(sp.get("pct")) or 100 * used / limit)
        parts.append(f"{GREY}extra{RESET} {c}${used:.0f}/${limit:.0f}{RESET} {GREY}this month{RESET}")
    return f"{mark}{BOLD}{name:<{pad}}{RESET}  " + "   ".join(parts)


def account_lines(cfg):
    data = usage(cfg)
    if not isinstance(data, dict):
        return [f"{GREY}usage: no data yet (is claude-swap installed? run `cswap add`){RESET}"]
    accounts = [a for a in data.get("accounts") or [] if isinstance(a, dict)]
    if not accounts:
        return [f"{GREY}usage: no accounts yet. Run `cswap add --alias work` while logged in.{RESET}"]
    names = [str(cfg["names"].get(a.get("alias") or "") or a.get("alias") or a.get("email") or "?") for a in accounts]
    pad = max(len(n) for n in names)
    rows = []
    for a, name in zip(accounts, names):
        try:
            rows.append(account_line(a, name, pad, int(cfg["bar_width"])))
        except Exception:
            rows.append(f"  {BOLD}{name:<{pad}}{RESET}  {GREY}no data (unreadable){RESET}")
    return rows


def read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def recap_lines(cfg, session_id):
    if not cfg["recap"] or not session_id:
        return []
    recap, edit = read(state_file(session_id, "recap")), read(state_file(session_id, "lastedit"))
    if not recap and not edit:
        return []
    text = recap or "Recap appears after the next reply."
    lines = textwrap.wrap(text, int(cfg["recap_width"]))[:int(cfg["recap_max_lines"])] or [text]
    out = [f"{ORANGE}※{RESET} {DIM}{lines[0]}{RESET}"] + [f"  {DIM}{line}{RESET}" for line in lines[1:]]
    if edit:
        out[-1] += f"  {BLUE}last edit {edit}{RESET}"
    return out


def main():
    raw = sys.stdin.read()
    cfg = config()
    try:
        session_id = json.loads(raw).get("session_id", "")
    except (ValueError, AttributeError):
        session_id = ""
    if cfg["top_command"]:
        try:
            top = subprocess.run(cfg["top_command"], shell=True, input=raw, capture_output=True,
                                 text=True, timeout=10).stdout.rstrip("\n")
            if top:
                print(top, flush=True)
        except Exception:
            pass
    # Each section fails on its own, so one bad value never blanks the whole status line.
    for section in (lambda: recap_lines(cfg, session_id), lambda: account_lines(cfg)):
        try:
            lines = section()
        except Exception:
            lines = []
        if lines:
            print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
