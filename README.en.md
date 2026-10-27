# Telegram daily check-in

[简体中文](README.md) | **English**

Sending check-in commands to bots by hand every day is easy to forget and a little tedious. This small tool uses your **personal Telegram account** to send daily check-in commands to selected chats. Each bot can have its own command. Set it up once, then let GitHub Actions run it on schedule.

Default schedule: **midnight (00:00) Melbourne time every day** (`Australia/Melbourne`, with automatic daylight saving adjustments). No Telegram Premium or always-on computer required.

## Features

- **Send from your personal account:** Telethon logs into your account; no Telegram Bot needs to be created.
- **Individual commands:** Set a different message for each recipient, such as `/qd`, `/sign`, or `/checkin`.
- **Automatic daily runs:** GitHub Actions starts the job on schedule and exits when sending is complete.
- **Sequential sending:** A 10-second pause between sends, with up to 20 recipients.
- **Check before enabling:** The default command only validates configuration. New deployments require an explicit switch before sending.

## Quick start

### 1. Prepare the project

Place the project files at the root of your own **private GitHub repository**. Include the hidden `.github` directory and `.gitignore` file. The scheduled workflow is in `.github/workflows/daily.yml`.

Install Python 3.12 or later locally, then run these commands from the project directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Get your Telegram API credentials

Open [my.telegram.org](https://my.telegram.org), sign in, and go to **API development tools**. Create an application and note its `api_id` and `api_hash`.

These credentials are used to connect to Telegram. Do not put them in the code or commit them to the repository.

### 3. Create a login session

Run this on your own computer:

```sh
python check_in.py --setup
```

Follow the prompts for your API ID, API hash, phone number with country code, Telegram login code, and two-step verification password if enabled. Input is hidden; type normally and press Enter.

After login, the script creates `session-secret.txt`. It contains a **StringSession login session** that later runs can reuse without requesting a new code every day. This step only logs in; it sends no messages.

**The session is an account login credential.** Do not share it, paste it into a chat, or upload it to the repository. The script creates the file with owner-only read/write permissions, and `.gitignore` excludes it.

### 4. Configure check-in commands

Edit [config.json](config.json) and add usernames with their commands under `recipients`:

```json
{
  "recipients": {
    "@alice": "/qd",
    "@bobbb": "/sign",
    "me": "/checkin"
  }
}
```

This is a format example; replace the recipients with your own. `me` means your Saved Messages. The project already has a configuration, so review it before use.

- Public `@usernames` and `me` are supported; phone numbers and numeric IDs are not.
- Usernames are case-insensitive. Duplicate usernames with the same message are merged; conflicting messages cause an error.
- Messages must not be empty and may contain up to 4096 UTF-16 code units.
- Messages are sent as plain text, with link previews disabled.
- Usernames may change or be transferred, so keep the configuration up to date.

To keep recipients out of the repository, use the `TELEGRAM_RECIPIENTS` Secret described below to override the configuration. For local use, you can also copy the file to `config.local.json` and run `python check_in.py --config config.local.json`. Git ignores this file.

### 5. Add GitHub Secrets

In your repository, open **Settings → Secrets and variables → Actions → Secrets**, click **New repository secret**, and add:

| Name | Value | Required |
| --- | --- | --- |
| `TELEGRAM_API_ID` | Telegram API ID | Yes |
| `TELEGRAM_API_HASH` | Telegram API hash | Yes |
| `TELEGRAM_SESSION` | Full contents of `session-secret.txt` | Yes |
| `TELEGRAM_RECIPIENTS` | JSON object mapping usernames to messages, such as `{"@alice":"/qd"}` | No |

A nonempty `TELEGRAM_RECIPIENTS` value completely replaces the recipient configuration in `config.json`. If it is missing or empty, the file's configuration is used.

On macOS, copy the session without displaying it in the terminal:

```sh
pbcopy < session-secret.txt
```

After pasting and saving it as a GitHub Secret, delete the local `session-secret.txt`. Your phone number, login code, and two-step verification password do not need to be uploaded to GitHub. API credentials and the session belong in Secrets, never in committed code.

### 6. Check and enable automatic check-ins

First, check locally:

```sh
python -m unittest -v
python check_in.py
```

Neither command connects to Telegram or sends messages.

Next, open **Actions → Daily Telegram check-in → Run workflow** in your repository. Leave **Send real messages** unchecked and run a configuration check.

Once it passes, open **Settings → Secrets and variables → Actions → Variables** and create this repository variable:

| Name | Value |
| --- | --- |
| `CHECK_IN_ENABLED` | `true` |

The next scheduled run will send messages. To test immediately, manually run the workflow and select **Send real messages**. A manual run sends only when the switch is `true` and that checkbox is selected.

## Change the schedule

Edit this section in [.github/workflows/daily.yml](.github/workflows/daily.yml):

```yaml
schedule:
  - cron: '0 0 * * *'
    timezone: Australia/Melbourne
```

The current schedule is midnight Melbourne time every day. Change `cron` to adjust the time; the timezone setting handles daylight saving automatically.

GitHub scheduled jobs can be delayed or dropped during busy periods; **exact timing is not guaranteed**. The workflow must be on the default branch. Public repositories may have scheduled workflows disabled after 60 days without activity; private repositories are not subject to that inactivity rule. Costs depend on your GitHub Actions allowance and billing settings.

## FAQ

### How do I pause it?

Set the repository variable `CHECK_IN_ENABLED` to `false`, or disable the workflow in Actions. Cancel any job that has already started separately.

### Does a successful send mean the check-in succeeded?

Not necessarily. A successful send means Telegram accepted the message. Check the bot's reply to confirm whether the check-in succeeded or a reward was credited. The script does not read or evaluate bot replies.

### Are failed sends retried automatically?

The script resolves every recipient before sending anything. If Telegram returns a FloodWait of at most 60 seconds, it waits and retries once. A longer wait, another rate limit, or any other error stops the run.

Some messages may already have been sent before a failure, and a network interruption can leave delivery uncertain. **Check the chat history before retrying** to avoid duplicates. GitHub re-runs skip the sending step, but a new manual run can send that day's commands again. The script does not automatically catch up on missed days or guarantee exactly-once delivery.

### What if the login session expires?

Run `python check_in.py --setup` locally to create a new session, then update `TELEGRAM_SESSION`. If the old `session-secret.txt` still exists, move or delete it first. To revoke a session, terminate its login under **Telegram Settings → Devices**.

### Can I send directly from my computer?

Yes. Securely set the `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_SESSION` environment variables, then run:

```sh
python check_in.py --send
```

This command sends real messages. Do not put credentials directly in command arguments or shell history.

## Documentation

- [GitHub Actions scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Telethon login sessions](https://docs.telethon.dev/en/stable/concepts/sessions.html)
- [Telethon FloodWait handling](https://docs.telethon.dev/en/stable/quick-references/faq.html#how-can-i-except-floodwaiterror)
