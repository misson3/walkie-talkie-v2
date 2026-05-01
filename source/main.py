from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from pathlib import Path

from .audio_manager import AudioManager
from .config import AppConfig, load_config
from .interfaces.button import ButtonManager
from .interfaces.pixels import Pixels
from .mqtt_handler import MqttVoiceClient, MqttVoiceMessage
from .telegram_handler import TelegramClient
from . import vosk_transcriber


logging.basicConfig(
    level=logging.DEBUG,
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
            own_username=config.own_bot_username,
            ignore_bot_usernames=config.telegram_ignore_bot_usernames,
            destination_file=config.play_file_path,
        )
        self._mqtt = (
            MqttVoiceClient(
                node_id=config.node_id,
                broker_host=config.mqtt_broker_host,
                broker_port=config.mqtt_broker_port,
                topic_prefix=config.mqtt_topic_prefix,
                username=config.mqtt_username,
                password=config.mqtt_password,
            )
            if config.mqtt_enabled
            else None
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
        self._recording_start_time: float | None = None

    def _log_startup_self_check(self) -> None:
        LOGGER.info("Startup self-check")
        LOGGER.info("Node id: %s", self._config.node_id)
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
        LOGGER.info("Ignored bot usernames: %s", list(self._config.telegram_ignore_bot_usernames))
        LOGGER.info(
            "MQTT config: enabled=%s broker=%s:%s prefix=%s username=%s",
            self._config.mqtt_enabled,
            self._config.mqtt_broker_host or "<unset>",
            self._config.mqtt_broker_port,
            self._config.mqtt_topic_prefix,
            self._config.mqtt_username or "<none>",
        )

    def _emit_event(self, event: AppEvent) -> None:
        self._loop.call_soon_threadsafe(self._events.put_nowait, event)

    async def run(self) -> None:
        self._log_startup_self_check()
        await self._telegram.log_startup_diagnostics()
        if self._mqtt is not None:
            await self._mqtt.start()
        self._button_manager.start()
        self._pixels.set_app_running(True)

        poll_task = asyncio.create_task(self._telegram_poll_loop())
        watchdog_task = asyncio.create_task(self._playback_watchdog_loop())
        mqtt_task = asyncio.create_task(self._mqtt_poll_loop()) if self._mqtt is not None else None

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
            tasks = [poll_task, watchdog_task]
            if mqtt_task is not None:
                mqtt_task.cancel()
                tasks.append(mqtt_task)
            await asyncio.gather(*tasks, return_exceptions=True)
            self.shutdown()

    async def _handle_record_toggle(self) -> None:
        if self._audio.is_recording:
            LOGGER.info("Stopping recording")
            stopped = self._audio.stop_recording()
            if not stopped:
                LOGGER.warning("Recording process exited with non-zero status")
            self._pixels.set_recording(False)
            beeped = self._audio.play_notification_file(self._config.recording_stop_sound_path)
            if not beeped:
                LOGGER.warning("Could not play recording stop sound")
            await self._broadcast_local_voice(self._config.send_file_path)
            await self._transcribe_and_post(self._config.send_file_path)
            return

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._audio.play_notification_file(self._config.recording_start_sound_path),
        )

        started = self._audio.start_recording(self._config.send_file_path)
        if not started:
            LOGGER.warning("Record request ignored (busy)")
            return

        LOGGER.info("Recording started")
        self._pixels.set_recording(True)
        self._recording_start_time = time.time()

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
            downloaded = await self._telegram.poll_with_retry(
                timeout_s=30,
                max_attempts=3,
                initial_backoff_s=1.0,
            )
            if downloaded:
                await self._play_incoming_audio("telegram-human")
            else:
                LOGGER.debug("No peer voice message downloaded in this poll cycle")
            await asyncio.sleep(self._config.poll_interval_s)

    async def _mqtt_poll_loop(self) -> None:
        assert self._mqtt is not None
        while True:
            message = await self._mqtt.get_message()
            await self._save_incoming_audio(message)
            await self._play_incoming_audio(f"mqtt-peer:{message.sender_id}")

    async def _playback_watchdog_loop(self) -> None:
        while True:
            recording = self._audio.is_recording
            playing = self._audio.is_playing

            if self._last_recording_state and not recording:
                self._pixels.set_recording(False)
                self._recording_start_time = None

            if recording and self._recording_start_time is not None:
                elapsed = time.time() - self._recording_start_time
                if elapsed >= self._config.max_recording_duration_s:
                    LOGGER.info(
                        "Max recording duration (%s s) reached, auto-stopping",
                        self._config.max_recording_duration_s,
                    )
                    self._audio.stop_recording()
                    self._pixels.set_recording(False)
                    self._recording_start_time = None
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: self._audio.play_notification_file(
                            self._config.max_duration_alert_sound_path
                        ),
                    )
                    await self._broadcast_local_voice(self._config.send_file_path)
                    await self._transcribe_and_post(self._config.send_file_path)

            if self._last_playing_state and not playing:
                self._pixels.set_playing(False)
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self._audio.play_notification_file(self._config.playback_end_sound_path),
                )

            self._last_recording_state = recording
            self._last_playing_state = playing
            await asyncio.sleep(0.1)

    def shutdown(self) -> None:
        if self._mqtt is not None:
            self._mqtt.close()
        self._audio.stop_recording()
        self._audio.stop_playback()
        self._pixels.set_recording(False)
        self._pixels.set_playing(False)
        self._pixels.set_app_running(False)
        self._button_manager.stop()

    async def _transcribe_and_post(self, voice_file: Path) -> None:
        if not self._config.stt_enabled:
            return

        import shutil
        import tempfile

        LOGGER.info("STT: starting transcription of %s", voice_file)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                copy_path = Path(tmpdir) / voice_file.name
                shutil.copy2(voice_file, copy_path)

                loop = asyncio.get_running_loop()
                text = await loop.run_in_executor(
                    None,
                    lambda: vosk_transcriber.transcribe(
                        copy_path, self._config.stt_model_path
                    ),
                )

            if text is None:
                LOGGER.warning("STT: transcription returned None (model/conversion error)")
                return

            if len(text) < self._config.stt_min_chars:
                LOGGER.info("STT: result too short (%r), skipping post", text)
                return

            message = f"{self._config.stt_message_prefix} {text}"
            LOGGER.info("STT: posting to Telegram: %r", message)
            await self._telegram.send_text(message)

        except Exception:
            LOGGER.exception("STT: unexpected error during transcription/post")

    async def _broadcast_local_voice(self, voice_file: Path) -> None:
        try:
            await self._telegram.send_voice(voice_file)
            LOGGER.info("Uploaded %s to Telegram", voice_file)
        except Exception:
            LOGGER.exception("Failed to upload recorded voice to Telegram")

        if self._mqtt is None:
            return

        try:
            await self._mqtt.publish_file(voice_file)
            LOGGER.info("Published %s to MQTT", voice_file)
        except Exception:
            LOGGER.exception("Failed to publish recorded voice to MQTT")

    async def _save_incoming_audio(self, message: MqttVoiceMessage) -> None:
        self._config.play_file_path.parent.mkdir(parents=True, exist_ok=True)
        self._config.play_file_path.write_bytes(message.payload)
        LOGGER.info(
            "Saved MQTT voice message from %s to %s",
            message.sender_id,
            self._config.play_file_path,
        )

    async def _play_incoming_audio(self, source: str) -> None:
        LOGGER.info("Incoming voice available from %s, playing doorbell then auto-playback", source)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._audio.play_notification_file(
                self._config.notification_sound_path
            ),
        )
        started = self._audio.start_playback(self._config.play_file_path)
        if started:
            self._pixels.set_playing(True)
        else:
            LOGGER.warning("Auto-playback skipped for %s (busy or file missing)", source)


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
