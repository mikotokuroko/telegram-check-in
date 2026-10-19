# Telegram daily check-in

Send a configured command to each recipient from your **personal Telegram account**, daily at **midnight (00:00) Australia/Melbourne**, using Telethon and GitHub Actions. No bot, Premium subscription, or always-on Mac. Sending starts disabled. Each recipient has its own message in `config.json`; `me` means your Saved Messages.

## One-time local setup

Requires Python 3.12+. Run these commands from this project folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest -v
python check_in.py
```

The last two commands are offline and send nothing.

1. Sign into [my.telegram.org](https://my.telegram.org) and open **API development tools** to create an application. Keep the `api_id` and `api_hash` private.
2. Run `python check_in.py --setup` **on your own computer**. Enter your API ID/hash, phone number, Telegram login code, and 2FA password if requested. These prompts are hidden. This logs in but sends no messages.
3. The resulting `session-secret.txt` contains a **StringSession**, not a SQLite session file. It is created with owner-only permissions and ignored by Git. Treat it as account access: anyone with it can act as you. Never paste it into chat, source code, workflow YAML, or logs.

## Configure and upload

Create a private GitHub repository and upload this folder's contents to its root, including `.github/workflows/daily.yml` and `.gitignore`. Do not upload `.venv`, local configuration, or credential files. No credentials are included in this project. Review staged files before any commit.

Edit the `recipients` object in `config.json` to map each username to its message, for example `{"@alice": "/qd", "@bobbb": "/sign"}`. Recipients are `me` or public `@usernames`; use only intended chats. Phone numbers and numeric IDs are intentionally unsupported. Usernames can change owners, so keep the list current. Case-insensitive duplicate usernames with identical messages are collapsed; conflicting messages are rejected. Maximum: 20 recipients, with a 10-second delay between sends. Messages are plain text with link previews off.

In **Settings → Secrets and variables → Actions → Secrets**, create:

| Repository secret | Value |
| --- | --- |
| `TELEGRAM_API_ID` | Your API ID |
| `TELEGRAM_API_HASH` | Your API hash |
| `TELEGRAM_SESSION` | Entire contents of `session-secret.txt` |
| `TELEGRAM_RECIPIENTS` (optional) | JSON object mapping usernames to messages; overrides `config.json` |

Delete `session-secret.txt` after saving its value in GitHub. Never commit API credentials, phone numbers, login codes, 2FA passwords, or sessions. GitHub needs neither your phone number nor your 2FA password. To revoke this session, terminate its device under **Telegram Settings → Devices**; generate a replacement locally if needed.

For private local configuration, copy `config.json` to the ignored `config.local.json` and use `python check_in.py --config config.local.json`. `TELEGRAM_RECIPIENTS`, when present, overrides the file’s recipient mapping. If missing or empty, Actions uses `config.json`. The six requested recipients and commands are already configured; only the three API/session secrets are required.

## Validate, then enable

1. Open **Actions → Daily Telegram check-in → Run workflow**. Leave **Send real messages** unchecked. This installs dependencies, runs offline tests, and validates configuration without logging in.
2. When ready to authorize real daily sends, add the repository **variable** `CHECK_IN_ENABLED` with the exact value `true`. The next scheduled run will send. A manual run sends only when both this variable and the **Send real messages** checkbox are enabled.
3. To stop, change that variable to `false` or disable the workflow. Cancel an already-running job separately.

For a deliberately authorized local send, provide `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_SESSION` in your process environment through a secure mechanism, then run `python check_in.py --send`. Avoid entering secret values as shell command arguments or storing them in shell history.

## Timing and failure behavior

The workflow uses GitHub's native `timezone: Australia/Melbourne`, so daylight saving changes require no edits. Change `0 0 * * *` to choose a different local time. Midnight avoids Melbourne’s repeated/skipped hours around DST changes. GitHub may delay midnight runs during high load; this is a target time, not an exact delivery guarantee.

GitHub schedules are best effort: runs may be delayed or dropped. The workflow must be on the default branch. Public repositories' schedules may be disabled after 60 days without repository activity; a private repository avoids that inactivity rule. Hosted runner usage is subject to your account's Actions quota/billing. This small job normally consumes little time but is not an unconditional free-service guarantee.

Recipients are resolved before any message is sent. A Telegram FloodWait of at most 60 seconds is waited out and retried once; longer or repeated waits fail the run. Other errors stop immediately. Logs report counts and error types, never message text, recipients, or credentials.

**There is no exactly-once delivery guarantee.** A failure after some sends leaves partial delivery; a connection failure can leave delivery uncertain. Inspect Telegram before trying again. GitHub re-runs skip the sending step, and concurrent workflow runs are serialized, but a new manual dispatch can still duplicate today's message. No automatic catch-up or whole-job retry is included. Enable GitHub Actions failure notifications and inspect failures; expired/revoked sessions need local setup again.

## Sources

- [GitHub scheduled workflows and timezone support](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Telethon StringSession and session security](https://docs.telethon.dev/en/stable/concepts/sessions.html)
- [Telethon FloodWait handling](https://docs.telethon.dev/en/stable/quick-references/faq.html#how-can-i-except-floodwaiterror)
