"""Offline checks: no Telegram connection or credentials needed."""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from telethon.errors import FloodWaitError

import check_in


class CheckInTest(unittest.TestCase):
    def test_configuration(self):
        with tempfile.NamedTemporaryFile(mode="w+") as config:
            config.write('{"message":"hello","recipients":["me"]}')
            config.flush()
            with patch.dict(
                os.environ, {"TELEGRAM_RECIPIENTS": '["@Alice", "@alice", "me"]'}
            ):
                self.assertEqual(
                    check_in.configuration(config.name)[1], ["@alice", "me"]
                )
            with patch.dict(os.environ, {"TELEGRAM_RECIPIENTS": '["+61412345678"]'}):
                with self.assertRaises(ValueError):
                    check_in.configuration(config.name)

    def test_delivery_and_flood_wait(self):
        async def check():
            client = AsyncMock()
            client.get_input_entity.side_effect = ["first", "second"]
            client.send_message.side_effect = [
                FloodWaitError(None, capture=2),
                None,
                None,
            ]
            with patch("check_in.asyncio.sleep", new_callable=AsyncMock) as sleep:
                await check_in.deliver(client, "hello", ["me", "@alice"])
                self.assertEqual(
                    [call.args[0] for call in sleep.call_args_list], [3, 10]
                )
                self.assertEqual(client.send_message.await_count, 3)
                self.assertFalse(client.send_message.call_args.kwargs["link_preview"])
                self.assertIsNone(client.send_message.call_args.kwargs["parse_mode"])
            for errors in (
                [FloodWaitError(None, capture=61)],
                [FloodWaitError(None, capture=1)] * 2,
                [RuntimeError("network")],
            ):
                operation = AsyncMock(side_effect=errors)
                with patch("check_in.asyncio.sleep", new_callable=AsyncMock):
                    with self.assertRaises((FloodWaitError, RuntimeError)):
                        await check_in.with_flood_wait(operation)
                self.assertEqual(operation.await_count, len(errors))
            client.reset_mock()
            client.get_input_entity.side_effect = [
                "first",
                ValueError("unknown recipient"),
            ]
            with self.assertRaises(ValueError):
                await check_in.deliver(client, "hello", ["me", "@alice"])
            client.send_message.assert_not_awaited()

        asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
