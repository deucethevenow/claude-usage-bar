# claude-usage-bar

See how much Claude you have left on **every** account, plus a running recap of what each chat is doing, right at the bottom of Claude Code.

> Built on [claude-swap](https://github.com/realiti4/claude-swap) by @realiti4 and [claude-powerline](https://github.com/Owloops/claude-powerline) by @Owloops. See [Credits](#credits).

```
 my-project  ✱ Opus 5.5  § $4.13  ☉ $83.85                          ← your current status line (kept as-is)
※ You're adding a usage bar for your Work and Personal accounts. The bar works on both accounts. Next, you're
  sharing it on GitHub, and Claude needs your OK before it goes public.  last edit Oct 4, 3:40pm MDT
● Work          5h ━━━━━━━─────  61% 1h 5m    week ━───────────  12% 6d 1h    Fable ────────────   0% 6d 1h    extra $150/$150 this month
  Personal Max  5h ────────────   2% 4h 55m   week ━───────────  10% 2d 21h   Fable ────────────   0% 2d 21h
```

In the terminal, the bars are colored: green under 70% used, yellow at 70 to 89%, and red at 90% or more.

## The problem it solves

If you use Claude Code a lot, you run into three annoyances:

1. **You can't see how close you are to a limit until you hit it.** Claude has a 5-hour limit, a weekly limit, and a separate weekly limit for some models (like Fable). Most status lines only show the account you're logged in with, and some don't show the model limit at all.
2. **If you have two accounts (say, a work seat and a personal Max plan), you can't compare them.** You have to switch accounts or open a website to see which one has room left.
3. **With several chats open, you lose track of what each one is doing.** Claude Code shows a recap only after you've been away for a while.

This tool adds three things to the bottom of Claude Code:

- **One usage line per account**, showing the 5-hour limit, the weekly limit, any per-model weekly limit (like Fable), and paid extra usage if it's on. Each one shows how much you've used and when it refills. A green dot marks the account you're using now.
- **A recap line** with 2 to 3 plain sentences about what this chat is working on, where it stands, and the next step. It updates as you work.
- **The time Claude last edited a file** in this chat, in your time zone.

## What makes it easy

- **One command to install.** The installer copies the files, installs [claude-swap](https://github.com/realiti4/claude-swap) if you don't have it, and updates your Claude Code settings for you.
- **It keeps your current status line.** Whatever you had before (claude-powerline, ccstatusline, your own script) stays on top. The new lines go underneath.
- **It's safe to run again.** Running the installer twice doesn't add anything twice, and it backs up your settings each time.
- **One command to undo.** `./uninstall.sh` puts your old status line back exactly as it was, including any extra settings like padding. It removes only its own hooks.
- **No API key needed.** The recap uses your normal Claude Code login with the small, fast Haiku model.
- **It can't break your status line.** If a usage number is missing or claude-swap is offline, your old status line still shows, and the bad part is skipped. A failed usage check waits a minute before trying again.
- **It stays fast.** Usage numbers are saved for 60 seconds, so the bar doesn't slow Claude Code down. The recap is written in the background.

## Install

You need: macOS or Linux, Python 3, Claude Code, and either [uv](https://docs.astral.sh/uv/) or pipx (to install claude-swap).

```bash
git clone https://github.com/deucethevenow/claude-usage-bar.git
cd claude-usage-bar
./install.sh
```

### Add your accounts

claude-swap needs to save each account once. Do this in a normal terminal:

1. Save the account you're logged in with now:
   ```bash
   cswap add --alias work
   ```
2. In Claude Code, type `/login` and sign in with your other account. **Do not run `/logout` first.** Logging out can cancel the saved login for the first account.
3. Save the second account:
   ```bash
   cswap add --alias personal
   ```
4. Switch back to the account you want to use:
   ```bash
   cswap switch work
   ```
5. Restart Claude Code.

Only have one account? It still works. You'll get one usage line and the recap.

## Settings

Change settings in `~/.claude/usage-bar/config.json`. The installer creates this file. See `config.example.json` for every option.

| Setting | What it does | Default |
|---|---|---|
| `top_command` | Your old status line. It shows on top. Leave it blank to hide it. | Whatever you had before installing |
| `names` | Display names for your claude-swap aliases, like `{"work": "Work Team"}` | The alias itself |
| `timezone` | Time zone for "last edit", like `America/Denver` | Your computer's time zone |
| `recap` | Turn the recap line on or off | `true` |
| `recap_every_seconds` | The shortest wait between recap updates | `180` |
| `bar_width` | How many characters wide each bar is | `12` |

## How it works

```
Claude Code ──(status line, every few seconds)──► bar.py
                                                   ├─ runs your old status line, prints it first
                                                   ├─ prints this chat's recap + last edit time
                                                   └─ prints usage per account (from `cswap list --json`, saved for 60s)

Claude finishes a reply ──(Stop hook)──► recap_hook.py ──► recap_gen.py (in the background)
                                                            reads the last part of the chat,
                                                            asks Haiku for a 2 to 3 sentence recap,
                                                            saves it for this chat only

Claude edits a file ──(PostToolUse hook)──► lastedit_hook.py ──► saves the time
```

- Each chat has its own recap and its own last-edit time, so two chats side by side show different recaps.
- Usage numbers come from claude-swap, which reads the same usage report that Claude Code's `/usage` shows.
- If Claude replies again before the 3-minute wait is up, one more recap is queued for when the wait ends. That way the last reply before you step away still gets a recap.
- Files older than two weeks are deleted automatically.

## Cost and privacy

- **Recap cost:** Each recap update is one small Haiku call. It sends about 4,500 tokens and gets back about 100, which is roughly half a cent at Haiku's prices. It runs at most once every 3 minutes per chat, and only after Claude replies, so a busy chat costs at most about 10 cents an hour. It counts toward the usage of the account you're logged in with. Set `"recap": false` to turn it off.
- **What gets sent:** Only the most recent text of the chat (up to about 14,000 characters, with no tool output) goes to Claude, the same service you're already chatting with. The helper runs from an empty folder, so it doesn't send your CLAUDE.md files or memory notes. Nothing goes anywhere else.
- **Where data lives:** Everything stays on your machine in `~/.claude/usage-bar/state/`.

## Tests

```bash
bash tests/test.sh
```

This installs into a throwaway folder with a fake claude-swap. It checks install, reinstall, uninstall and the status line, and it never touches your real settings or accounts.

## Uninstall

```bash
./uninstall.sh
```

This puts your old status line back, removes the two hooks, and deletes `~/.claude/usage-bar`. claude-swap stays installed. Remove it with `uv tool uninstall claude-swap`.

## Credits

This project borrows from two open-source projects and builds on top of them. All the credit for the hard parts goes to their authors. If this helps you, please star their repos too.

- **[claude-swap](https://github.com/realiti4/claude-swap) by [@realiti4](https://github.com/realiti4).** It stores several Claude logins, switches between them, and reads each account's usage. Every usage number in this bar comes from claude-swap. The bar style (thin lines, the color levels, the countdown to each refill, and the dot on the active account) copies the look of its `cswap watch` dashboard.
- **[claude-powerline](https://github.com/Owloops/claude-powerline) by [@Owloops](https://github.com/Owloops).** It's the status line shown on top in the example above. This project started as an add-on underneath it, and it still keeps your claude-powerline bar (or any other status line) on top.

claude-usage-bar doesn't change or ship either project's code. It installs claude-swap as a separate tool, runs your existing status line as-is, and adds its own lines underneath. Both projects keep their own licenses.

MIT License.
