from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    telegram_token: str
    telegram_chat_id: int
    own_bot_username: str
    audio_device: str
    gpio_record_pin: int
    gpio_replay_pin: int
    gpio_record_active_low: bool
    gpio_replay_active_low: bool
    debounce_ms: int
    poll_interval_s: float
    max_recording_duration_s: float
    send_file_path: Path
    play_file_path: Path


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on", "y"}:
        return True
    if normalized in {"0", "false", "no", "off", "n"}:
        return False
    raise RuntimeError(f"Invalid boolean value for {name}: {value}")


def load_config(project_root: Path | None = None) -> AppConfig:
    root = project_root or Path(__file__).resolve().parent

    token = _require_env("TELEGRAM_BOT_TOKEN")
    chat_id = int(_require_env("TELEGRAM_CHAT_ID"))
    own_bot = os.getenv("TELEGRAM_OWN_BOT_USERNAME", "")

    audio_device = os.getenv("AUDIO_DEVICE", "hw:1,0")
    record_pin = int(os.getenv("GPIO_RECORD_PIN", "12"))
    #replay_pin = int(os.getenv("GPIO_REPLAY_PIN", "17"))
    replay_pin = int(os.getenv("GPIO_REPLAY_PIN", "13"))
    record_active_low = _env_bool("GPIO_RECORD_ACTIVE_LOW", True)
    replay_active_low = _env_bool("GPIO_REPLAY_ACTIVE_LOW", True)
    debounce_ms = int(os.getenv("GPIO_DEBOUNCE_MS", "120"))
    poll_interval_s = float(os.getenv("TELEGRAM_POLL_INTERVAL_S", "1.5"))
    max_recording_duration_s = float(os.getenv("MAX_RECORDING_DURATION_S", "30.0"))

    send_file = root / os.getenv("SEND_FILE_NAME", "to-go-voice.ogg")
    play_file = root / os.getenv("PLAY_FILE_NAME", "to-play-voice.ogg")

    return AppConfig(
        telegram_token=token,
        telegram_chat_id=chat_id,
        own_bot_username=own_bot,
        audio_device=audio_device,
        gpio_record_pin=record_pin,
        gpio_replay_pin=replay_pin,
        gpio_record_active_low=record_active_low,
        gpio_replay_active_low=replay_active_low,
        debounce_ms=debounce_ms,
        poll_interval_s=poll_interval_s,
        max_recording_duration_s=max_recording_duration_s,
        send_file_path=send_file,
        play_file_path=play_file,
    )
