#!/usr/bin/env python3
"""Add or remove claude-usage-bar in ~/.claude/settings.json. Used by install.sh and uninstall.sh."""
import json
import os
import shutil
import sys

HOOK_FILES = ("recap_hook.py", "lastedit_hook.py")


def load(path):
    with open(path) as f:
        return json.load(f)


def save(path, data):
    """Write through symlinks and keep the file's permissions."""
    real = os.path.realpath(path)
    tmp = f"{real}.usage-bar.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    if os.path.exists(real):
        shutil.copymode(real, tmp)
    os.replace(tmp, real)


def ours(cmd, dest):
    return any(f'"{dest}/{name}"' in cmd for name in HOOK_FILES + ("bar.py",))


def strip_hooks(s, dest):
    """Remove only this tool's hook entries; keep every other hook, even in the same group."""
    hooks = s.get("hooks") or {}
    for event in list(hooks):
        kept = []
        for g in hooks[event]:
            g["hooks"] = [h for h in g.get("hooks", []) if not ours(h.get("command", ""), dest)]
            if g["hooks"]:
                kept.append(g)
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]


def install(settings_path, dest, py):
    s = load(settings_path)
    cfg_path = os.path.join(dest, "config.json")
    cfg = load(cfg_path) if os.path.exists(cfg_path) else {"names": {}, "timezone": ""}
    current = s.get("statusLine")
    if current and not ours((current or {}).get("command", ""), dest):
        # The user's own status line: keep all of it for uninstall, and show it on top.
        cfg["previous_status_line"] = current
        cfg["top_command"] = current.get("command", "")
        print("Keeping your current status line on top of the new lines.")
    cfg.setdefault("top_command", "")
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")

    s["statusLine"] = {"type": "command", "command": f'"{py}" "{dest}/bar.py"'}
    strip_hooks(s, dest)
    hooks = s.setdefault("hooks", {})
    hooks.setdefault("Stop", []).append(
        {"hooks": [{"type": "command", "command": f'"{py}" "{dest}/recap_hook.py"', "timeout": 5}]})
    hooks.setdefault("PostToolUse", []).append(
        {"matcher": "Edit|Write|MultiEdit|NotebookEdit",
         "hooks": [{"type": "command", "command": f'"{py}" "{dest}/lastedit_hook.py"', "timeout": 5}]})
    save(settings_path, s)


def uninstall(settings_path, dest):
    s = load(settings_path)
    try:
        previous = load(os.path.join(dest, "config.json")).get("previous_status_line")
    except (OSError, ValueError):
        previous = None
    if ours((s.get("statusLine") or {}).get("command", ""), dest):
        if previous:
            s["statusLine"] = previous
        else:
            s.pop("statusLine", None)
    strip_hooks(s, dest)
    save(settings_path, s)


if __name__ == "__main__":
    if sys.argv[1] == "install":
        install(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        uninstall(sys.argv[2], sys.argv[3])
