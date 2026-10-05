#!/usr/bin/env python3
"""Claude Code status line: your old bar, then a session recap, then one usage line per account."""
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time

from common import STATE, config, state_file, write_atomic

RESET, DIM, BOLD = "\033[0m", "\033[2m", "\033[1m"
GREEN, YELLOW, RED = "\033[38;5;114m", "\033[38;5;179m", "\033[38;5;167m"
ANSI = re.compile(r"\033\[[0-9;]*m")
GREY, EMPTY, ORANGE, BLUE = "\033[38;5;245m", "\033[38;5;238m", "\033[38;5;173m", "\033[38;5;110m"


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def color(pct):
    return RED if pct >= 90 else YELLOW if pct >= 70 else GREEN


def visible_len(text):
    return len(ANSI.sub("", text))


def meter(pct, width):
    filled = min(width, max(0, round(pct / 100 * width)))
    return f"{color(pct)}{'━' * filled}{EMPTY}{'─' * (width - filled)}{RESET}"


def bar(label, pct, when, width):
    """Short form, used when the terminal is too narrow for the labeled table."""
    c = color(pct)
    return f"{GREY}{label}{RESET} {meter(pct, width)} {c}{pct:>3.0f}%{RESET} {GREY}{when or '':<6}{RESET}"


def cell(pct, when, width):
    """Labeled form: the bar, then how much is used, how much is left, and when it refills."""
    c = color(pct)
    left = max(0, 100 - pct)
    refill = f"refills in {when}" if when else ("not started" if pct == 0 else "")
    return (f"{meter(pct, width)} {c}{pct:>3.0f}% used{RESET}  {BOLD}{left:>3.0f}% left{RESET}  "
            f"{GREY}{refill:<17}{RESET}")


def context_line(raw, width):
    """How full this chat's memory (context window) is."""
    ctx = raw.get("context_window") or {}
    used = num(ctx.get("used_percentage"))
    if used is None:
        return []
    return [f"  {GREY}This chat's memory{RESET}  {meter(used, width)} {color(used)}{used:>3.0f}% used{RESET}  "
            f"{BOLD}{max(0, 100 - used):>3.0f}% left{RESET}  {GREY}before Claude summarizes older messages{RESET}"]


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


def windows_of(a):
    """The limits for one account, in order: 5-hour, weekly, then any per-model weekly limit."""
    u = a.get("usage") or {}
    out = [("5-hour limit", "5h", u.get("fiveHour")), ("Weekly limit", "week", u.get("sevenDay"))]
    out += [(f"{s.get('name') or 'Model'} weekly limit", s.get("name") or "model", s)
            for s in u.get("scoped") or [] if isinstance(s, dict)]
    return [(title, short, win) for title, short, win in out if num((win or {}).get("pct")) is not None]


def extra_spend(cfg, a):
    sp = (a.get("usage") or {}).get("spend") or {}
    used, limit = num(sp.get("used")), num(sp.get("limit"))
    if not cfg["show_extra_spend"] or used is None or not limit:
        return ""
    c = color(num(sp.get("pct")) or 100 * used / limit)
    return f"{GREY}paid extra this month{RESET} {c}${used:.0f} of ${limit:.0f}{RESET}"


def account_lines(cfg, columns):
    data = usage(cfg)
    if not isinstance(data, dict):
        return [f"{GREY}usage: no data yet (is claude-swap installed? run `cswap add`){RESET}"]
    accounts = [a for a in data.get("accounts") or [] if isinstance(a, dict)]
    if not accounts:
        return [f"{GREY}usage: no accounts yet. Run `cswap add --alias work` while logged in.{RESET}"]
    names = [str(cfg["names"].get(a.get("alias") or "") or a.get("alias") or a.get("email") or "?") for a in accounts]
    pad = max(len(n) for n in names)
    w = int(cfg["bar_width"])

    # Column titles across all accounts, so each limit lines up under its title.
    titles = []
    for a in accounts:
        for title, _, _ in windows_of(a):
            if title not in titles:
                titles.append(title)
    cell_w = visible_len(cell(100, "6d 23h", w))
    gap = "   "

    def row(a, name, labeled):
        mark = f"{GREEN}●{RESET} " if a.get("active") else "  "
        head = f"{mark}{BOLD}{name:<{pad}}{RESET}  "
        if a.get("usageStatus") != "ok" or not a.get("usage"):
            return head + f"{GREY}no data ({a.get('usageStatus')}){RESET}"
        wins = {title: (short, win) for title, short, win in windows_of(a)}
        if labeled:
            parts = [cell(num(wins[t][1]["pct"]), wins[t][1].get("countdown"), w) if t in wins else " " * cell_w
                     for t in titles]
        else:
            parts = [bar(short, num(win["pct"]), win.get("countdown"), w) for short, win in wins.values()]
        extra = extra_spend(cfg, a)
        if extra and labeled:
            return head + gap.join(parts) + "\n" + " " * (pad + 4) + extra
        return head + gap.join(parts + ([extra] if extra else []))

    def build(labeled):
        rows = []
        if labeled:
            rows.append(" " * (pad + 4) + gap.join(f"{GREY}{t.upper():<{cell_w}}{RESET}" for t in titles))
        for a, name in zip(accounts, names):
            try:
                rows.append(row(a, name, labeled))
            except Exception:
                rows.append(f"  {BOLD}{name:<{pad}}{RESET}  {GREY}no data (unreadable){RESET}")
        return rows

    labeled = build(True)
    if cfg["labels"] == "short" or max(visible_len(line) for r in labeled for line in r.split("\n")) > columns:
        return build(False)
    return labeled


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
        data = json.loads(raw)
        session_id = data.get("session_id", "")
    except (ValueError, AttributeError):
        data, session_id = {}, ""
    if cfg["top_command"]:
        try:
            top = subprocess.run(cfg["top_command"], shell=True, input=raw, capture_output=True,
                                 text=True, timeout=10).stdout.rstrip("\n")
            if top:
                print(top, flush=True)
        except Exception:
            pass
    # Each section fails on its own, so one bad value never blanks the whole status line.
    try:
        columns = int(os.environ.get("COLUMNS") or 0) or shutil.get_terminal_size((160, 20)).columns
    except ValueError:
        columns = 160
    sections = [lambda: recap_lines(cfg, session_id)]
    if cfg["show_context"]:
        sections.append(lambda: context_line(data, int(cfg["bar_width"])))
    sections.append(lambda: account_lines(cfg, columns))
    for section in sections:
        try:
            lines = section()
        except Exception:
            lines = []
        if lines:
            print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
