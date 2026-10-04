#!/bin/bash
# Remove claude-usage-bar from Claude Code and put your old status line back.
set -euo pipefail
DEST="$HOME/.claude/usage-bar"
SETTINGS="$HOME/.claude/settings.json"
PY="$(command -v /usr/bin/python3 || command -v python3)"

if [ -f "$SETTINGS" ] && [ -f "$DEST/settings_patch.py" ]; then
  cp "$SETTINGS" "$SETTINGS.bak-usage-bar-$(date +%Y%m%d%H%M%S)"
  "$PY" "$DEST/settings_patch.py" uninstall "$SETTINGS" "$DEST"
fi
rm -rf "${DEST:?}"
echo "Removed. Your old status line is back. claude-swap is still installed (remove it with: uv tool uninstall claude-swap)."
