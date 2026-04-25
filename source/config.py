from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    node_id: str
    telegram_token: str
    telegram_chat_id: int
    own_bot_username: str
    telegram_ignore_bot_usernames: tuple[str, ...]
    transcript_prefix: str
    mqtt_enabled: bool
    mqtt_broker_host: str
    mqtt_broker_port: int
    mqtt_topic_prefix: str
    mqtt_username: str
    mqtt_password: str
    whisper_enabled: bool
    whisper_cli_path: Path
    whisper_model_path: Path
    whisper_language: str
    whisper_threads: int
    whisper_timeout_s: float
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
    notification_sound_path: Path
    recording_start_sound_path: Path
    recording_stop_sound_path: Path
    playback_end_sound_path: Path
    max_duration_alert_sound_path: Path


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


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer value for {name}: {value}") from exc


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid float value for {name}: {value}") from exc


def _env_csv(name: str) -> tuple[str, ...]:
    value = os.getenv(name, "")
    items = []
    for item in value.split(","):
        normalized = item.strip().lstrip("@").lower()
        if normalized:
            items.append(normalized)
    return tuple(dict.fromkeys(items))


def load_config(project_root: Path | None = None) -> AppConfig:
    root = project_root or Path(__file__).resolve().parent.parent
    ogg_root = root / "ogg"

    node_id = os.getenv("NODE_ID", "unnamed-node").strip() or "unnamed-node"
    token = _require_env("TELEGRAM_BOT_TOKEN")
    chat_id = int(_require_env("TELEGRAM_CHAT_ID"))
    own_bot = os.getenv("TELEGRAM_OWN_BOT_USERNAME", "").strip().lstrip("@").lower()
    ignore_bot_usernames = _env_csv("TELEGRAM_IGNORE_BOT_USERNAMES")
    transcript_prefix = os.getenv("TRANSCRIPT_PREFIX", "[transcript]").strip() or "[transcript]"
    mqtt_enabled = _env_bool("MQTT_ENABLED", False)
    mqtt_broker_host = os.getenv("MQTT_BROKER_HOST", "").strip()
    mqtt_broker_port = _env_int("MQTT_BROKER_PORT", 1883)
    mqtt_topic_prefix = os.getenv("MQTT_TOPIC_PREFIX", "walkie/v2").strip().strip("/") or "walkie/v2"
    mqtt_username = os.getenv("MQTT_USERNAME", "").strip()
    mqtt_password = os.getenv("MQTT_PASSWORD", "")
    whisper_enabled = _env_bool("WHISPER_ENABLED", False)
    whisper_cli_path = Path(
        os.getenv("WHISPER_CLI_PATH", "/home/pison/whisper.cpp/build/bin/whisper-cli").strip()
        or "/home/pison/whisper.cpp/build/bin/whisper-cli"
    )
    whisper_model_value = os.getenv("WHISPER_MODEL_PATH", "").strip()
    whisper_model_path = Path(whisper_model_value) if whisper_model_value else Path()
    whisper_language = os.getenv("WHISPER_LANGUAGE", "ja").strip() or "ja"
    whisper_threads = _env_int("WHISPER_THREADS", 2)
    whisper_timeout_s = _env_float("WHISPER_TIMEOUT_S", 180.0)
    if whisper_enabled and not whisper_model_value:
        raise RuntimeError("WHISPER_ENABLED is true but WHISPER_MODEL_PATH is empty")

    audio_device = "hw:1,0"
    record_pin = 12
    replay_pin = 13
    record_active_low = _env_bool("GPIO_RECORD_ACTIVE_LOW", True)
    replay_active_low = _env_bool("GPIO_REPLAY_ACTIVE_LOW", True)
    debounce_ms = 120
    poll_interval_s = 1.5
    max_recording_duration_s = 30.0

    send_file = ogg_root / "to-go-voice.ogg"
    play_file = ogg_root / "to-play-voice.ogg"
    notification_sound = ogg_root / "doorbell_short_decay.ogg"
    recording_start_sound = ogg_root / "rec_start_A.ogg"
    recording_stop_sound = ogg_root / "rec_stop_A.ogg"
    playback_end_sound = ogg_root / "rec_stop_C.ogg"
    max_duration_alert_sound = ogg_root / "max_dur_B.ogg"

    return AppConfig(
        node_id=node_id,
        telegram_token=token,
        telegram_chat_id=chat_id,
        own_bot_username=own_bot,
        telegram_ignore_bot_usernames=ignore_bot_usernames,
        transcript_prefix=transcript_prefix,
        mqtt_enabled=mqtt_enabled,
        mqtt_broker_host=mqtt_broker_host,
        mqtt_broker_port=mqtt_broker_port,
        mqtt_topic_prefix=mqtt_topic_prefix,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        whisper_enabled=whisper_enabled,
        whisper_cli_path=whisper_cli_path,
        whisper_model_path=whisper_model_path,
        whisper_language=whisper_language,
        whisper_threads=whisper_threads,
        whisper_timeout_s=whisper_timeout_s,
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
        notification_sound_path=notification_sound,
        recording_start_sound_path=recording_start_sound,
        recording_stop_sound_path=recording_stop_sound,
        playback_end_sound_path=playback_end_sound,
        max_duration_alert_sound_path=max_duration_alert_sound,
    )
