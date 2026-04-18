from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import paho.mqtt.client as mqtt  # type: ignore[import-not-found,import-untyped]


LOGGER = logging.getLogger(__name__)

DisconnectCallback = Callable[
    [mqtt.Client, object, mqtt.DisconnectFlags, mqtt.ReasonCode, mqtt.Properties | None],
    None,
]


def normalize_mqtt_topic_prefix(topic_prefix: str) -> str:
    return topic_prefix.strip().strip("/")


def build_mqtt_audio_topic(topic_prefix: str, sender_id: str) -> str:
    return f"{normalize_mqtt_topic_prefix(topic_prefix)}/audio/{sender_id}"


def extract_sender_id_from_topic(topic: str, topic_prefix: str) -> str | None:
    normalized_prefix = normalize_mqtt_topic_prefix(topic_prefix)
    expected_prefix = f"{normalized_prefix}/audio/"
    if not topic.startswith(expected_prefix):
        return None
    sender_id = topic[len(expected_prefix) :]
    return sender_id or None


def should_accept_mqtt_message(topic: str, topic_prefix: str, local_node_id: str) -> bool:
    sender_id = extract_sender_id_from_topic(topic, topic_prefix)
    return sender_id is not None and sender_id != local_node_id


@dataclass(frozen=True)
class MqttVoiceMessage:
    sender_id: str
    topic: str
    payload: bytes


class MqttVoiceClient:
    def __init__(
        self,
        node_id: str,
        broker_host: str,
        broker_port: int,
        topic_prefix: str,
        username: str = "",
        password: str = "",
    ):
        if not broker_host:
            raise RuntimeError("MQTT_ENABLED is true but MQTT_BROKER_HOST is empty")

        self._node_id = node_id
        self._broker_host = broker_host
        self._broker_port = broker_port
        self._topic_prefix = normalize_mqtt_topic_prefix(topic_prefix)
        self._username = username
        self._password = password
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[MqttVoiceMessage] = asyncio.Queue()
        self._connected = asyncio.Event()
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        if self._username:
            self._client.username_pw_set(self._username, self._password)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = cast(DisconnectCallback, self._on_disconnect)
        self._client.on_message = self._on_message

    @property
    def publish_topic(self) -> str:
        return build_mqtt_audio_topic(self._topic_prefix, self._node_id)

    @property
    def subscribe_topic(self) -> str:
        return f"{self._topic_prefix}/audio/+"

    async def start(self, timeout_s: float = 10.0) -> bool:
        self._loop = asyncio.get_running_loop()
        self._connected.clear()
        LOGGER.info(
            "Connecting to MQTT broker %s:%s with publish=%s subscribe=%s username=%s",
            self._broker_host,
            self._broker_port,
            self.publish_topic,
            self.subscribe_topic,
            self._username or "<none>",
        )
        self._client.connect_async(self._broker_host, self._broker_port)
        self._client.loop_start()
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=timeout_s)
        except TimeoutError as exc:
            LOGGER.warning(
                "Timed out connecting to MQTT broker within %s seconds; continuing in degraded mode and waiting for background reconnect",
                timeout_s,
            )
            LOGGER.debug("Initial MQTT connect timeout details", exc_info=exc)
            return False
        return True

    async def publish_file(self, file_path: Path, qos: int = 1) -> None:
        payload = file_path.read_bytes()
        await self.publish_bytes(payload=payload, qos=qos)

    async def publish_bytes(self, payload: bytes, qos: int = 1) -> None:
        if not self._connected.is_set():
            raise RuntimeError("MQTT broker is not connected")
        result = self._client.publish(self.publish_topic, payload=payload, qos=qos)
        await asyncio.to_thread(result.wait_for_publish)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed with rc={result.rc}")

    async def get_message(self) -> MqttVoiceMessage:
        return await self._queue.get()

    def close(self) -> None:
        try:
            self._client.loop_stop()
        finally:
            self._client.disconnect()

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: object,
        _flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        if reason_code != mqtt.CONNACK_ACCEPTED:
            LOGGER.error("MQTT connect failed: %s", reason_code)
            return

        LOGGER.info("MQTT connected")
        client.subscribe(self.subscribe_topic, qos=1)
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._connected.set)

    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: object,
        _disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None = None,
    ) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._connected.clear)
        LOGGER.info("MQTT disconnected: %s", reason_code)

    def _on_message(
        self,
        _client: mqtt.Client,
        _userdata: object,
        message: mqtt.MQTTMessage,
    ) -> None:
        sender_id = extract_sender_id_from_topic(message.topic, self._topic_prefix)
        if sender_id is None:
            LOGGER.warning("Ignoring MQTT message on unexpected topic %s", message.topic)
            return
        if not should_accept_mqtt_message(message.topic, self._topic_prefix, self._node_id):
            LOGGER.debug("Ignoring own MQTT message on %s", message.topic)
            return

        LOGGER.info(
            "Received MQTT voice message from %s on %s (%s bytes)",
            sender_id,
            message.topic,
            len(message.payload),
        )
        mqtt_message = MqttVoiceMessage(
            sender_id=sender_id,
            topic=message.topic,
            payload=bytes(message.payload),
        )
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, mqtt_message)