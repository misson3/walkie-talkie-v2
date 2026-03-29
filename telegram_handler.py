from __future__ import annotations

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
        peer_bot_username: str,
        destination_file: Path,
    ):
        self._bot = Bot(token=token)
        self._chat_id = chat_id
        self._peer_bot_username = peer_bot_username.lstrip("@").lower()
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
            return False

        for update in updates:
            self._offset = update.update_id + 1
            message = update.effective_message
            if message is None or message.voice is None:
                continue
            if message.chat_id != self._chat_id:
                continue

            username = (message.from_user.username or "").lower() if message.from_user else ""
            if username != self._peer_bot_username:
                continue

            file = await self._bot.get_file(message.voice.file_id)
            tmp_file = self._destination_file.with_suffix(".tmp")
            await file.download_to_drive(custom_path=str(tmp_file))
            tmp_file.replace(self._destination_file)
            LOGGER.info("Downloaded peer voice message to %s", self._destination_file)
            return True

        return False

    async def safe_poll_and_download_peer_voice(self, timeout_s: int = 30) -> bool:
        try:
            return await self.poll_and_download_peer_voice(timeout_s=timeout_s)
        except TelegramError:
            LOGGER.exception("Telegram polling/downloading failed")
            return False
