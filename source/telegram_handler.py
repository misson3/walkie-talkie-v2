from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from pathlib import Path

from telegram import Bot
from telegram.error import TelegramError


LOGGER = logging.getLogger(__name__)


def normalize_telegram_username(username: str) -> str:
    return username.strip().lstrip("@").lower()


def build_ignore_bot_usernames(
    own_username: str = "",
    ignore_bot_usernames: Iterable[str] = (),
) -> set[str]:
    normalized_usernames = {
        normalize_telegram_username(username)
        for username in ignore_bot_usernames
        if normalize_telegram_username(username)
    }
    normalized_own_username = normalize_telegram_username(own_username)
    if normalized_own_username:
        normalized_usernames.add(normalized_own_username)
    return normalized_usernames


def should_ignore_telegram_sender(sender_username: str, ignore_bot_usernames: set[str]) -> bool:
    normalized_sender = normalize_telegram_username(sender_username)
    return bool(normalized_sender) and normalized_sender in ignore_bot_usernames


class TelegramClient:
    def __init__(
        self,
        token: str,
        chat_id: int,
        destination_file: Path,
        own_username: str = "",
        ignore_bot_usernames: Iterable[str] = (),
    ):
        self._bot = Bot(token=token)
        self._chat_id = chat_id
        self._own_username = normalize_telegram_username(own_username)
        self._ignore_bot_usernames = build_ignore_bot_usernames(
            own_username=self._own_username,
            ignore_bot_usernames=ignore_bot_usernames,
        )
        self._destination_file = destination_file
        self._offset: int | None = None

    async def log_startup_diagnostics(self) -> None:
        try:
            me = await self._bot.get_me()
            bot_username = (me.username or "").lower()
            LOGGER.info(
                "Telegram bot identity: id=%s username=@%s own_username_env=@%s",
                me.id,
                bot_username,
                self._own_username,
            )
            LOGGER.info("Telegram ignored bot usernames: %s", sorted(self._ignore_bot_usernames))

            if self._own_username and bot_username and self._own_username != bot_username:
                LOGGER.warning(
                    "Configured TELEGRAM_OWN_BOT_USERNAME (@%s) does not match token bot (@%s)",
                    self._own_username,
                    bot_username,
                )

            webhook_info = await self._bot.get_webhook_info()
            if webhook_info.url:
                LOGGER.warning(
                    "Webhook is set to %s; long polling via getUpdates may return no updates",
                    webhook_info.url,
                )
            else:
                LOGGER.info("Webhook is not set (long polling mode)")

            try:
                chat = await self._bot.get_chat(self._chat_id)
                LOGGER.info(
                    "Configured chat is visible: id=%s type=%s title=%s",
                    chat.id,
                    chat.type,
                    getattr(chat, "title", ""),
                )
            except TelegramError:
                LOGGER.exception(
                    "Configured TELEGRAM_CHAT_ID (%s) is not accessible by this bot",
                    self._chat_id,
                )

            try:
                member = await self._bot.get_chat_member(self._chat_id, me.id)
                LOGGER.info("Bot membership in configured chat: status=%s", member.status)
                if str(member.status).lower() == "restricted":
                    LOGGER.warning(
                        "Bot is restricted in this chat. Receiving updates may be limited by chat permissions."
                    )
            except TelegramError:
                LOGGER.exception(
                    "Failed to get bot membership for chat_id=%s",
                    self._chat_id,
                )
        except TelegramError:
            LOGGER.exception("Telegram startup diagnostics failed")

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

            sender = message.from_user.username or "" if message.from_user else ""
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

            if should_ignore_telegram_sender(sender, self._ignore_bot_usernames):
                LOGGER.debug("Update %s: ignored bot sender @%s, skipping", update.update_id, sender)
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
