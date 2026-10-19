"""Daily personal-account check-in. Default invocation is offline validation."""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from getpass import getpass
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession


def configuration(path):
    data = json.loads(Path(path).read_text())
    recipients = (
        json.loads(os.environ["TELEGRAM_RECIPIENTS"])
        if os.environ.get("TELEGRAM_RECIPIENTS")
        else data.get("recipients")
    )
    if not isinstance(recipients, dict) or not 1 <= len(recipients) <= 20:
        raise ValueError("Configure a mapping of 1–20 recipients to messages.")
    result = {}
    for recipient, message in recipients.items():
        if (
            not isinstance(message, str)
            or not message.strip()
            or len(message.encode("utf-16-le")) // 2 > 4096
        ):
            raise ValueError("Message must contain 1–4096 UTF-16 code units.")
        if not isinstance(recipient, str) or not re.fullmatch(
            r"me|@[A-Za-z][A-Za-z0-9_]{4,31}", recipient
        ):
            raise ValueError("Recipients must be 'me' or @usernames.")
        recipient = recipient.lower()
        if recipient in result and result[recipient] != message:
            raise ValueError("Conflicting messages for the same recipient.")
        result[recipient] = message
    return result


async def with_flood_wait(operation):
    """Retry once only when Telegram explicitly says to wait, up to 60 seconds."""
    try:
        return await operation()
    except FloodWaitError as error:
        if error.seconds > 60:
            raise
        await asyncio.sleep(error.seconds + 1)
        return await operation()


async def deliver(client, recipients):
    # Resolve everything before sending so a bad username fails without partial sends.
    peers = []
    for recipient, message in recipients.items():
        peer = await with_flood_wait(
            lambda recipient=recipient: client.get_input_entity(recipient)
        )
        peers.append((peer, message))
    for index, (peer, message) in enumerate(peers):
        if index:
            await asyncio.sleep(10)
        await with_flood_wait(
            lambda peer=peer, message=message: client.send_message(
                peer, message, parse_mode=None, link_preview=False
            )
        )
        print(f"Sent recipient {index + 1}/{len(peers)}.", flush=True)


async def send(recipients):
    session = os.environ["TELEGRAM_SESSION"].strip()
    if not session:
        raise ValueError("Missing session.")
    client = TelegramClient(
        StringSession(session),
        int(os.environ["TELEGRAM_API_ID"]),
        os.environ["TELEGRAM_API_HASH"],
        flood_sleep_threshold=0,
        request_retries=0,
        receive_updates=False,
    )
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise ValueError("Session expired; generate a new session locally.")
        if (await client.get_me()).bot:
            raise ValueError("A personal Telegram account is required.")
        await deliver(client, recipients)
    finally:
        await client.disconnect()


async def setup():
    if os.environ.get("CI") or not sys.stdin.isatty():
        raise ValueError("Session setup requires a local interactive terminal.")
    target = Path("session-secret.txt")
    if target.exists():
        raise ValueError("session-secret.txt already exists; move or delete it first.")
    api_id = int(getpass("Telegram API ID (hidden): "))
    api_hash = getpass("Telegram API hash (hidden): ")
    client = TelegramClient(StringSession(), api_id, api_hash)
    try:
        await client.start(
            phone=lambda: getpass("Phone number with country code (hidden): "),
            code_callback=lambda: getpass("Telegram login code (hidden): "),
            password=lambda: getpass("Telegram 2FA password (hidden): "),
        )
        if (await client.get_me()).bot:
            raise ValueError("A personal Telegram account is required.")
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            output.write(client.session.save())
        print("Saved session-secret.txt. Add it as TELEGRAM_SESSION, then delete it.")
    finally:
        await client.disconnect()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--send", action="store_true", help="Send real messages")
    mode.add_argument(
        "--setup", action="store_true", help="Log in locally; sends no messages"
    )
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()
    # Do not expose request bodies, recipient identifiers or credentials in logs.
    logging.disable(logging.CRITICAL)
    try:
        if args.setup:
            asyncio.run(setup())
        else:
            recipients = configuration(args.config)
            if args.send:
                asyncio.run(send(recipients))
            else:
                print(
                    f"Offline validation passed: {len(recipients)} recipient(s). Nothing sent."
                )
    except Exception as error:
        print(
            f"Failed ({type(error).__name__}). Check configuration, secrets and session; "
            "inspect delivery before retrying.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
