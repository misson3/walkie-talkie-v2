from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from telegram import Bot
from telegram.error import TelegramError


LOGGER = logging.getLogger(__name__)


class TelegramClient:
    def __init__(
        self,
        token: str,
        chat_id: int,
        destination_file: Path,
        own_username: str = "",
    ):
        self._bot = Bot(token=token)
        self._chat_id = chat_id
        self._own_username = own_username.lstrip("@").lower()
        self._destination_file = destination_file
        self._offset: int | None = None

    async def send_voice(self, voice_file: Path) -> None:
        with voice_file.open("rb") as voice_stream:
            await self._bot.send_voice(
                chat_id=self._chat_id,
                voice=voice_stream,
                filename=voice_file.name,
            )

    async def poll_and_download_peer_voice(self, timeout_s: int = 30) -> bool:
        updates = await self._bot.get_updates(
            offset=self._offset,
            timeout=timeout_s,
            allowed_updates=["message"],
        )
        if not updates:
            LOGGER.debug("No updates received")
            return False

        LOGGER.debug("Received %s update(s)", len(updates))

        for update in updates:
            self._offset = update.update_id + 1
            message = update.effective_message

            if message is None:
                LOGGER.debug("Update %s: no message, skipping", update.update_id)
                continue

            sender = (message.from_user.username or "").lower() if message.from_user else ""
            LOGGER.debug(
                "Update %s: chat_id=%s sender=@%s has_voice=%s",
                update.update_id,
                message.chat_id,
                sender,
                message.voice is not None,
            )

            if message.voice is None:
                LOGGER.debug("Update %s: not a voice message, skipping", update.update_id)
                continue

            if message.chat_id != self._chat_id:
                LOGGER.debug(
                    "Update %s: chat_id %s != expected %s, skipping",
                    update.update_id,
                    message.chat_id,
                    self._chat_id,
                )
                continue

            # Skip messages sent by this bot itself to avoid echo
            if self._own_username and sender == self._own_username:
                LOGGER.debug("Update %s: own message, skipping", update.update_id)
                continue

            LOGGER.info(
                "Downloading voice message from @%s (update %s)",
                sender,
                update.update_id,
            )
            file = await self._bot.get_file(message.voice.file_id)
            tmp_file = self._destination_file.with_suffix(".tmp")
            await file.download_to_drive(custom_path=str(tmp_file))
            tmp_file.replace(self._destination_file)
            LOGGER.info("Downloaded voice message to %s", self._destination_file)
            return True

        return False

    async def safe_poll_and_download_peer_voice(self, timeout_s: int = 30) -> bool:
        try:
            return await self.poll_and_download_peer_voice(timeout_s=timeout_s)
        except TelegramError:
            LOGGER.exception("Telegram polling/downloading failed")
            return False

    async def poll_with_retry(
        self,
        timeout_s: int = 30,
        max_attempts: int = 3,
        initial_backoff_s: float = 1.0,
    ) -> bool:
        attempt = 0
        backoff = initial_backoff_s

        while attempt < max_attempts:
            attempt += 1
            try:
                return await self.poll_and_download_peer_voice(timeout_s=timeout_s)
            except TelegramError:
                LOGGER.exception("Telegram poll attempt %s/%s failed", attempt, max_attempts)
                if attempt >= max_attempts:
                    return False
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, 10.0)

        return False
