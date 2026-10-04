#!/bin/bash
# Install claude-usage-bar into ~/.claude/usage-bar and wire it into Claude Code.
# Safe to run again: it updates the code and never duplicates settings.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/src"
DEST="$HOME/.claude/usage-bar"
SETTINGS="$HOME/.claude/settings.json"

PY="$(command -v /usr/bin/python3 || command -v python3 || true)"
[ -n "$PY" ] || { echo "Python 3 is required. Install it, then run this again."; exit 1; }
command -v claude >/dev/null || echo "Note: the 'claude' command was not found. The recap line needs it."

if ! command -v cswap >/dev/null; then
  echo "Installing claude-swap..."
  if command -v uv >/dev/null; then uv tool install claude-swap
  elif command -v pipx >/dev/null; then pipx install claude-swap
  else echo "Install uv (https://docs.astral.sh/uv/) or pipx, then run this again."; exit 1; fi
fi

mkdir -p "$DEST/state"
cp "$SRC"/*.py "$DEST"/
mkdir -p "$(dirname "$SETTINGS")"
[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"
cp "$SETTINGS" "$SETTINGS.bak-usage-bar-$(date +%Y%m%d%H%M%S)"
"$PY" "$DEST/settings_patch.py" install "$SETTINGS" "$DEST" "$PY"

cat <<MSG

Installed. Next steps:
  1. In a terminal, save the account you're logged in with:   cswap add --alias work
  2. In Claude Code, type /login and sign in with your other account (don't log out first).
  3. Save that one too:                                        cswap add --alias personal
  4. Switch back to the one you want to use:                   cswap switch work
  5. Restart Claude Code.

Optional: set display names and your time zone in $DEST/config.json
MSG
