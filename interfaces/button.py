from __future__ import annotations

import threading
import time
from collections.abc import Callable

import RPi.GPIO as GPIO


class ButtonManager:
    def __init__(
        self,
        record_pin: int,
        replay_pin: int,
        on_record_pressed: Callable[[], None],
        on_replay_pressed: Callable[[], None],
        debounce_ms: int = 120,
        record_active_low: bool = True,
        replay_active_low: bool = True,
    ):
        self._record_pin = record_pin
        self._replay_pin = replay_pin
        self._on_record_pressed = on_record_pressed
        self._on_replay_pressed = on_replay_pressed
        self._debounce_s = debounce_ms / 1000.0
        self._record_active_low = record_active_low
        self._replay_active_low = replay_active_low

        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._last_record_pressed_at = 0.0
        self._last_replay_pressed_at = 0.0

    def start(self) -> None:
        GPIO.setmode(GPIO.BCM)
        if self._record_active_low:
            GPIO.setup(self._record_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        else:
            GPIO.setup(self._record_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        if self._replay_active_low:
            GPIO.setup(self._replay_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        else:
            GPIO.setup(self._replay_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
        GPIO.cleanup([self._record_pin, self._replay_pin])

    def _loop(self) -> None:
        prev_record = False
        prev_replay = False

        while not self._stop_event.is_set():
            record_state = GPIO.input(self._record_pin)
            record_pressed = record_state == GPIO.LOW if self._record_active_low else record_state == GPIO.HIGH

            replay_state = GPIO.input(self._replay_pin)
            replay_pressed = replay_state == GPIO.LOW if self._replay_active_low else replay_state == GPIO.HIGH

            now = time.monotonic()
            if record_pressed and not prev_record and (now - self._last_record_pressed_at) >= self._debounce_s:
                self._last_record_pressed_at = now
                self._on_record_pressed()

            if replay_pressed and not prev_replay and (now - self._last_replay_pressed_at) >= self._debounce_s:
                self._last_replay_pressed_at = now
                self._on_replay_pressed()

            prev_record = record_pressed
            prev_replay = replay_pressed
            time.sleep(0.01)
