#!/usr/bin/env python3
"""Stop hook: refresh this chat's recap in the background, at most once every few minutes.

If a reply lands inside the wait window, one delayed refresh is queued for when the window ends,
so the last reply before you step away still gets a recap.
"""
import json
import os
import subprocess
import sys
import time

from common import HOME, cleanup_old_state, config, state_file

if os.environ.get("CLAUDE_USAGE_BAR_CHILD"):
    sys.exit(0)  # the recap writer runs Claude itself; don't loop
cfg = config()
cleanup_old_state()
if not cfg["recap"]:
    sys.exit(0)
try:
    d = json.load(sys.stdin)
    session_id, transcript = d.get("session_id", ""), d.get("transcript_path", "")
except (ValueError, AttributeError):
    sys.exit(0)
if not session_id or not os.path.isfile(transcript):
    sys.exit(0)

stamp, pending = state_file(session_id, "stamp"), state_file(session_id, "pending")
try:
    wait = float(cfg["recap_every_seconds"]) - (time.time() - os.path.getmtime(stamp))
except OSError:
    wait = 0
if wait > 0:
    if os.path.exists(pending) and time.time() - os.path.getmtime(pending) < wait + 300:
        sys.exit(0)  # a delayed refresh is already queued
    open(pending, "w").close()
else:
    open(stamp, "w").close()

subprocess.Popen([sys.executable, os.path.join(HOME, "recap_gen.py"), session_id, transcript, str(max(0, int(wait)))],
                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                 start_new_session=True)
