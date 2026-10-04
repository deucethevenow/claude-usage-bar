#!/bin/bash
# Checks install, uninstall and the status line against a throwaway home folder. Run: bash tests/test.sh
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$(command -v /usr/bin/python3 || command -v python3)"
FAIL=0
ok() { echo "PASS  $1"; }
bad() { echo "FAIL  $1"; FAIL=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

T=$(mktemp -d); export HOME=$T
mkdir -p "$T/.claude" "$T/dotfiles" "$T/bin"
# A fake cswap so the test never touches real accounts.
cat > "$T/bin/cswap" <<'X'
#!/bin/bash
echo '{"accounts":[{"number":1,"alias":"work","active":true,"usageStatus":"ok","usage":{"fiveHour":{"pct":null,"countdown":"1h"},"sevenDay":{"pct":95,"countdown":"2d"}}}]}'
X
chmod +x "$T/bin/cswap"; export PATH="$T/bin:$PATH"

cat > "$T/dotfiles/settings.json" <<'X'
{"statusLine":{"type":"command","command":"echo OLD-BAR","padding":2},
 "hooks":{"Stop":[{"hooks":[{"type":"command","command":"bash ~/Projects/claude-usage-bar/my-own-hook.sh"},
                            {"type":"command","command":"keep-me"}]}]}}
X
chmod 600 "$T/dotfiles/settings.json"
ln -s "$T/dotfiles/settings.json" "$T/.claude/settings.json"
S="$T/.claude/settings.json"

bash "$REPO/install.sh" >/dev/null && bash "$REPO/install.sh" >/dev/null
check "settings.json is still a symlink"            '[ -L "$S" ]'
check "file permissions kept (600)"                 '[ "$(stat -f %Lp "$T/dotfiles/settings.json" 2>/dev/null || stat -c %a "$T/dotfiles/settings.json")" = 600 ]'
check "installing twice adds one Stop hook"         '[ "$("$PY" -c "import json;print(sum(\"recap_hook\" in h[\"command\"] for g in json.load(open(\"$S\"))[\"hooks\"][\"Stop\"] for h in g[\"hooks\"]))")" = 1 ]'
check "user hooks with usage-bar in the path stay"  'grep -q my-own-hook "$S" && grep -q keep-me "$S"'

OUT=$(echo '{"session_id":"t1"}' | "$PY" "$T/.claude/usage-bar/bar.py" | sed "s/$(printf '\033')\[[0-9;]*m//g")
check "old status line still prints on top"         'echo "$OUT" | head -1 | grep -q OLD-BAR'
check "a null usage number doesn't blank the bar"   'echo "$OUT" | grep -q "week ━.* 95%"'

echo '{"names":null,"top_command":"echo OLD-BAR"}' > "$T/.claude/usage-bar/config.json"
OUT=$(echo '{}' | "$PY" "$T/.claude/usage-bar/bar.py" 2>&1)
check "names: null in config doesn't crash"         'echo "$OUT" | grep -q work'

# A failing cswap should be retried at most once a minute.
rm -f "$T/.claude/usage-bar/state/cswap."*
printf '#!/bin/bash\nsleep 2; exit 1\n' > "$T/bin/cswap"
echo '{}' | "$PY" "$T/.claude/usage-bar/bar.py" >/dev/null
START=$(date +%s); echo '{}' | "$PY" "$T/.claude/usage-bar/bar.py" >/dev/null; END=$(date +%s)
check "a failed usage read isn't retried right away" '[ $((END - START)) -lt 2 ]'

# The user changes their status line, then installs again: uninstall should bring back the newer one.
"$PY" - "$S" <<'X'
import json, sys
p = sys.argv[1]; s = json.load(open(p)); s["statusLine"] = {"type": "command", "command": "echo NEWER-BAR", "padding": 1}
json.dump(s, open(p, "w"))
X
bash "$REPO/install.sh" >/dev/null
bash "$REPO/uninstall.sh" >/dev/null
check "uninstall restores the full newer status line" '"$PY" -c "import json,sys; s=json.load(open(\"$S\")); sys.exit(s[\"statusLine\"]!={\"type\":\"command\",\"command\":\"echo NEWER-BAR\",\"padding\":1})"'
check "uninstall removes only its own hooks"        '! grep -q "usage-bar/recap_hook" "$S" && grep -q my-own-hook "$S" && grep -q keep-me "$S"'
check "uninstall keeps the symlink"                 '[ -L "$S" ]'
check "uninstall deletes the install folder"        '[ ! -d "$T/.claude/usage-bar" ]'

rm -f "$S"; bash "$REPO/uninstall.sh" >/dev/null 2>&1
check "uninstall with no settings file exits cleanly" '[ $? -eq 0 ]'

rm -rf "${T:?}"
[ $FAIL -eq 0 ] && echo "All checks passed." || { echo "Some checks failed."; exit 1; }
