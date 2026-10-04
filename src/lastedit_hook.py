#!/usr/bin/env python3
"""PostToolUse hook (Edit/Write): remember when Claude last changed a file in this chat."""
import json
import sys
from datetime import datetime

from common import cleanup_old_state, config, state_file, write_atomic

try:
    session_id = json.load(sys.stdin).get("session_id", "")
except (ValueError, AttributeError):
    sys.exit(0)
if session_id:
    tz = config()["timezone"]
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(tz)) if tz else datetime.now().astimezone()
    except Exception:
        now = datetime.now().astimezone()
    stamp = f"{now:%b} {now.day}, {now.hour % 12 or 12}:{now:%M}{'am' if now.hour < 12 else 'pm'} {now:%Z}"
    write_atomic(state_file(session_id, "lastedit"), stamp)
    cleanup_old_state()
