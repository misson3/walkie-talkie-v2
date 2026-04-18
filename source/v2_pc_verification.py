from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import load_config
from .mqtt_handler import (
    MqttVoiceClient,
    build_mqtt_audio_topic,
    extract_sender_id_from_topic,
    should_accept_mqtt_message,
)
from .telegram_handler import (
    build_ignore_bot_usernames,
    should_ignore_telegram_sender,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


@contextmanager
def patched_environ(updates: dict[str, str]) -> Iterator[None]:
    previous_values = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            os.environ[key] = value
        yield
    finally:
        for key, previous_value in previous_values.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value


def verify_config(project_root: Path) -> None:
    LOGGER.info("Verifying V2 config parsing")
    with patched_environ(
        {
            "TELEGRAM_BOT_TOKEN": "123456:TEST_TOKEN",
            "TELEGRAM_CHAT_ID": "12345",
            "TELEGRAM_OWN_BOT_USERNAME": "@Koe1_Bot",
            "TELEGRAM_IGNORE_BOT_USERNAMES": " @koe2_bot , koe1_bot, @koe2_bot ",
            "NODE_ID": "pi_a",
            "MQTT_ENABLED": "true",
            "MQTT_BROKER_HOST": "100.64.0.10",
            "MQTT_BROKER_PORT": "1883",
            "MQTT_TOPIC_PREFIX": "/walkie/v2/",
            "MQTT_USERNAME": "walkie",
            "MQTT_PASSWORD": "secret-pass",
        }
    ):
        config = load_config(project_root=project_root)

    assert config.node_id == "pi_a"
    assert config.own_bot_username == "koe1_bot"
    assert config.telegram_ignore_bot_usernames == ("koe2_bot", "koe1_bot")
    assert config.mqtt_enabled is True
    assert config.mqtt_broker_host == "100.64.0.10"
    assert config.mqtt_broker_port == 1883
    assert config.mqtt_topic_prefix == "walkie/v2"
    assert config.mqtt_username == "walkie"
    assert config.mqtt_password == "secret-pass"
    assert config.send_file_path == project_root / "ogg" / "to-go-voice.ogg"
    assert config.play_file_path == project_root / "ogg" / "to-play-voice.ogg"


def verify_telegram_rules() -> None:
    LOGGER.info("Verifying Telegram sender filtering rules")
    ignored = build_ignore_bot_usernames(
        own_username="@koe1_bot",
        ignore_bot_usernames=["koe2_bot", "@koe1_bot", " ", "@koe2_bot"],
    )

    assert ignored == {"koe1_bot", "koe2_bot"}
    assert should_ignore_telegram_sender("@koe1_bot", ignored) is True
    assert should_ignore_telegram_sender("koe2_bot", ignored) is True
    assert should_ignore_telegram_sender("HumanUser", ignored) is False
    assert should_ignore_telegram_sender("", ignored) is False


def verify_mqtt_rules() -> None:
    LOGGER.info("Verifying MQTT topic rules")
    client = MqttVoiceClient(
        node_id="pi_a",
        broker_host="127.0.0.1",
        broker_port=1883,
        topic_prefix="/walkie/v2/",
        username="walkie",
        password="secret-pass",
    )

    peer_topic = build_mqtt_audio_topic("walkie/v2", "pi_b")
    own_topic = client.publish_topic

    assert own_topic == "walkie/v2/audio/pi_a"
    assert client.subscribe_topic == "walkie/v2/audio/+"
    assert peer_topic == "walkie/v2/audio/pi_b"
    assert extract_sender_id_from_topic(peer_topic, "walkie/v2") == "pi_b"
    assert extract_sender_id_from_topic("unexpected/topic", "walkie/v2") is None
    assert should_accept_mqtt_message(peer_topic, "walkie/v2", "pi_a") is True
    assert should_accept_mqtt_message(own_topic, "walkie/v2", "pi_a") is False
    assert should_accept_mqtt_message("unexpected/topic", "walkie/v2", "pi_a") is False


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    verify_config(project_root)
    verify_telegram_rules()
    verify_mqtt_rules()
    LOGGER.info("V2 PC-side verification passed")


if __name__ == "__main__":
    main()