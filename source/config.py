from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    # Telegram related settings
    telegram_token: str
    telegram_chat_id: int
    own_bot_username: str
    telegram_ignore_bot_usernames: tuple[str, ...]
    # MQTT related settings
    node_id: str
    mqtt_enabled: bool
    mqtt_broker_host: str
    mqtt_broker_port: int
    mqtt_topic_prefix: str
    mqtt_username: str
    mqtt_password: str
    # STT (Speech-to-Text) related settings
    stt_enabled: bool
    stt_language_code: str
    stt_model: str
    stt_timeout_s: float
    google_application_credentials: str
    # Hardware related settings
    audio_device: str
    gpio_record_pin: int
    gpio_replay_pin: int
    gpio_record_active_low: bool
    gpio_replay_active_low: bool
    debounce_ms: int
    poll_interval_s: float
    max_recording_duration_s: float
    # Sound file paths
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
    mqtt_enabled = _env_bool("MQTT_ENABLED", False)
    mqtt_broker_host = os.getenv("MQTT_BROKER_HOST", "").strip()
    mqtt_broker_port = _env_int("MQTT_BROKER_PORT", 1883)
    mqtt_topic_prefix = (
        os.getenv("MQTT_TOPIC_PREFIX", "walkie/v2").strip().strip("/") or "walkie/v2"
    )
    mqtt_username = os.getenv("MQTT_USERNAME", "").strip()
    mqtt_password = os.getenv("MQTT_PASSWORD", "")
    stt_enabled = _env_bool("STT_ENABLED", False)
    stt_language_code = os.getenv("STT_LANGUAGE_CODE", "ja-JP").strip() or "ja-JP"
    stt_model = os.getenv("STT_MODEL", "").strip()
    stt_timeout_s = _env_float("STT_TIMEOUT_S", 15.0)
    google_application_credentials = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    ).strip()

    audio_device = os.getenv("AUDIO_DEVICE", "hw:1,0").strip()
    record_pin = _env_int("GPIO_RECORD_PIN", 12)
    replay_pin = _env_int("GPIO_REPLAY_PIN", 13)
    record_active_low = _env_bool("GPIO_RECORD_ACTIVE_LOW", True)
    replay_active_low = _env_bool("GPIO_REPLAY_ACTIVE_LOW", True)
    debounce_ms = _env_int("DEBOUNCE_MS", 120)
    poll_interval_s = _env_float("POLL_INTERVAL_S", 1.5)
    max_recording_duration_s = _env_float("MAX_RECORDING_DURATION_S", 30.0)

    send_file = ogg_root / Path(os.getenv("SEND_FILE_NAME", "to-go-voice.ogg").strip())
    play_file = ogg_root / Path(
        os.getenv("PLAY_FILE_NAME", "to-play-voice.ogg").strip()
    )
    notification_sound = ogg_root / Path(
        os.getenv("NOTIFICATION_SOUND_NAME", "doorbell_short_decay.ogg").strip()
    )
    recording_start_sound = ogg_root / Path(
        os.getenv("RECORDING_START_SOUND_NAME", "rec_start_A.ogg").strip()
    )
    recording_stop_sound = ogg_root / Path(
        os.getenv("RECORDING_STOP_SOUND_NAME", "rec_stop_A.ogg").strip()
    )
    playback_end_sound = ogg_root / Path(
        os.getenv("PLAYBACK_END_SOUND_NAME", "rec_stop_C.ogg").strip()
    )
    max_duration_alert_sound = ogg_root / Path(
        os.getenv("MAX_DURATION_ALERT_SOUND_NAME", "max_dur_B.ogg").strip()
    )

    return AppConfig(
        # Telegram related settings
        telegram_token=token,
        telegram_chat_id=chat_id,
        own_bot_username=own_bot,
        telegram_ignore_bot_usernames=ignore_bot_usernames,
        # MQTT related settings
        node_id=node_id,
        mqtt_enabled=mqtt_enabled,
        mqtt_broker_host=mqtt_broker_host,
        mqtt_broker_port=mqtt_broker_port,
        mqtt_topic_prefix=mqtt_topic_prefix,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        # STT related settings
        stt_enabled=stt_enabled,
        stt_language_code=stt_language_code,
        stt_model=stt_model,
        stt_timeout_s=stt_timeout_s,
        google_application_credentials=google_application_credentials,
        # Hardware related settings
        audio_device=audio_device,
        gpio_record_pin=record_pin,
        gpio_replay_pin=replay_pin,
        gpio_record_active_low=record_active_low,
        gpio_replay_active_low=replay_active_low,
        debounce_ms=debounce_ms,
        poll_interval_s=poll_interval_s,
        max_recording_duration_s=max_recording_duration_s,
        # Audio file paths
        send_file_path=send_file,
        play_file_path=play_file,
        notification_sound_path=notification_sound,
        recording_start_sound_path=recording_start_sound,
        recording_stop_sound_path=recording_stop_sound,
        playback_end_sound_path=playback_end_sound,
        max_duration_alert_sound_path=max_duration_alert_sound,
    )
