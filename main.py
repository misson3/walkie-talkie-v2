from __future__ import annotations

import asyncio
import logging
from enum import Enum

from audio_manager import AudioManager
from config import AppConfig, load_config
from interfaces.button import ButtonManager
from interfaces.pixels import Pixels
from telegram_handler import TelegramClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger(__name__)


class AppEvent(str, Enum):
    RECORD_TOGGLE = "record_toggle"
    REPLAY = "replay"


class WalkieTalkieApp:
    def __init__(self, config: AppConfig):
        self._config = config
        self._loop = asyncio.get_running_loop()
        self._events: asyncio.Queue[AppEvent] = asyncio.Queue()

        self._audio = AudioManager(audio_device=config.audio_device)
        self._pixels = Pixels()
        self._telegram = TelegramClient(
            token=config.telegram_token,
            chat_id=config.telegram_chat_id,
            peer_bot_username=config.peer_bot_username,
            destination_file=config.play_file_path,
        )

        self._button_manager = ButtonManager(
            record_pin=config.gpio_record_pin,
            replay_pin=config.gpio_replay_pin,
            on_record_pressed=lambda: self._emit_event(AppEvent.RECORD_TOGGLE),
            on_replay_pressed=lambda: self._emit_event(AppEvent.REPLAY),
            debounce_ms=config.debounce_ms,
            record_active_low=config.gpio_record_active_low,
            replay_active_low=config.gpio_replay_active_low,
        )

        self._last_recording_state = False
        self._last_playing_state = False

    def _log_startup_self_check(self) -> None:
        LOGGER.info("Startup self-check")
        LOGGER.info(
            "Button A: GPIO%s pull-up=%s active-low=%s",
            self._config.gpio_record_pin,
            self._config.gpio_record_active_low,
            self._config.gpio_record_active_low,
        )
        LOGGER.info(
            "Button B: GPIO%s pull-up=%s active-low=%s",
            self._config.gpio_replay_pin,
            self._config.gpio_replay_active_low,
            self._config.gpio_replay_active_low,
        )
        LOGGER.info("Audio device: %s", self._config.audio_device)
        LOGGER.info("Send voice path: %s", self._config.send_file_path)
        LOGGER.info("Play voice path: %s", self._config.play_file_path)
        LOGGER.info("Telegram chat id: %s", self._config.telegram_chat_id)
        LOGGER.info("Peer bot username: %s", self._config.peer_bot_username)

    def _emit_event(self, event: AppEvent) -> None:
        self._loop.call_soon_threadsafe(self._events.put_nowait, event)

    async def run(self) -> None:
        self._log_startup_self_check()
        self._button_manager.start()
        self._pixels.set_app_running(True)

        poll_task = asyncio.create_task(self._telegram_poll_loop())
        watchdog_task = asyncio.create_task(self._playback_watchdog_loop())

        try:
            while True:
                event = await self._events.get()
                if event is AppEvent.RECORD_TOGGLE:
                    await self._handle_record_toggle()
                elif event is AppEvent.REPLAY:
                    self._handle_replay_button()
        finally:
            poll_task.cancel()
            watchdog_task.cancel()
            await asyncio.gather(poll_task, watchdog_task, return_exceptions=True)
            self.shutdown()

    async def _handle_record_toggle(self) -> None:
        if self._audio.is_recording:
            LOGGER.info("Stopping recording")
            self._audio.stop_recording()
            self._pixels.set_recording(False)
            try:
                await self._telegram.send_voice(self._config.send_file_path)
                LOGGER.info("Uploaded %s", self._config.send_file_path)
            except Exception:
                LOGGER.exception("Failed to upload recorded voice")
            return

        started = self._audio.start_recording(self._config.send_file_path)
        if not started:
            LOGGER.warning("Record request ignored (busy)")
            return

        LOGGER.info("Recording started")
        self._pixels.set_recording(True)

    def _handle_replay_button(self) -> None:
        if self._audio.is_recording:
            LOGGER.info("Replay ignored while recording")
            return

        started = self._audio.start_playback(self._config.play_file_path)
        if not started:
            LOGGER.info("Replay ignored (busy or missing file)")
            return

        LOGGER.info("Playback started")
        self._pixels.set_playing(True)

    async def _telegram_poll_loop(self) -> None:
        while True:
            downloaded = await self._telegram.safe_poll_and_download_peer_voice(timeout_s=30)
            if downloaded:
                LOGGER.info("Peer voice downloaded and ready for replay")
            await asyncio.sleep(self._config.poll_interval_s)

    async def _playback_watchdog_loop(self) -> None:
        while True:
            recording = self._audio.is_recording
            playing = self._audio.is_playing

            if self._last_recording_state and not recording:
                self._pixels.set_recording(False)
            if self._last_playing_state and not playing:
                self._pixels.set_playing(False)

            self._last_recording_state = recording
            self._last_playing_state = playing
            await asyncio.sleep(0.1)

    def shutdown(self) -> None:
        self._audio.stop_recording()
        self._audio.stop_playback()
        self._pixels.set_recording(False)
        self._pixels.set_playing(False)
        self._pixels.set_app_running(False)
        self._button_manager.stop()


async def _main_async() -> None:
    config = load_config()
    app = WalkieTalkieApp(config)
    await app.run()


def main() -> None:
    try:
        asyncio.run(_main_async())
    except KeyboardInterrupt:
        LOGGER.info("Exiting on keyboard interrupt")


if __name__ == "__main__":
    main()
