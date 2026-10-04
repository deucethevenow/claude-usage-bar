#!/usr/bin/env python3
"""Write a short recap of one Claude Code chat for the status line, using a small, fast model."""
import json
import os
import subprocess
import sys
import time

from common import STATE, config, state_file, write_atomic

MAX_CHARS = 14000
PROMPT = """You write the short recap shown under a Claude Code chat.
Read the chat excerpt below. Speak to the user as "you". Write 2 to 3 sentences, 40 to 60 words total:
1. What the user is trying to get done, with the specific names of the things involved.
2. Where the work stands right now (what is finished, what is not).
3. The next step, and who owes it (the user or Claude).
Plain words a sixth grader understands. No em dashes. No preamble, no quotes, no labels. Output only the recap."""


def text_of(content):
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text")


def excerpt_of(transcript):
    turns = []
    with open(transcript) as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if not isinstance(e, dict) or e.get("type") not in ("user", "assistant") or e.get("isMeta"):
                continue
            t = text_of((e.get("message") or {}).get("content")).strip()
            if t and not t.startswith("<"):
                turns.append(f"{e['type'].upper()}: {t[:2000]}")
    excerpt = ""
    for t in reversed(turns):
        if len(excerpt) + len(t) > MAX_CHARS:
            break
        excerpt = t + "\n\n" + excerpt
    return excerpt


def main(session_id, transcript, delay):
    if delay > 0:
        time.sleep(delay)
        try:
            os.remove(state_file(session_id, "pending"))
        except OSError:
            pass
        open(state_file(session_id, "stamp"), "w").close()
    excerpt = excerpt_of(transcript)
    if not excerpt:
        return
    # Run from an empty folder so the helper doesn't load any CLAUDE.md or memory files:
    # only the chat excerpt is sent, and the call stays small.
    empty = os.path.join(STATE, "empty")
    os.makedirs(empty, exist_ok=True)
    r = subprocess.run(
        ["claude", "-p", "--model", config()["recap_model"], "--setting-sources", "", "--strict-mcp-config",
         "--no-session-persistence", "--tools", "", "--system-prompt", PROMPT],
        input=excerpt, capture_output=True, text=True, timeout=90, cwd=empty,
        env=dict(os.environ, CLAUDE_USAGE_BAR_CHILD="1", MAX_THINKING_TOKENS="0", DISABLE_PROMPT_CACHING="1"))
    recap = " ".join(r.stdout.split()).replace("—", ", ")
    if r.returncode == 0 and 20 < len(recap) < 800:
        write_atomic(state_file(session_id, "recap"), recap)


if __name__ == "__main__":
    try:
        main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 0)
    except Exception:
        pass
