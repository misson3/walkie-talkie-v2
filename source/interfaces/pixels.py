from __future__ import annotations

import threading

from . import apa102


class Pixels:
    """Role-based LED controller for the 3 on-board APA102 LEDs.

    LED1 (index 0): app running indicator (green)
    LED2 (index 1): recording indicator (red)
    LED3 (index 2): playback indicator (blue)
    """

    APP_LED = 0
    RECORD_LED = 1
    PLAY_LED = 2

    def __init__(self):
        self.dev = apa102.APA102(num_led=3)
        self._lock = threading.Lock()
        self._app_on = False
        self._record_on = False
        self._play_on = False
        self._render()

    def set_app_running(self, enabled: bool) -> None:
        with self._lock:
            self._app_on = enabled
            self._render()

    def set_recording(self, enabled: bool) -> None:
        with self._lock:
            self._record_on = enabled
            self._render()

    def set_playing(self, enabled: bool) -> None:
        with self._lock:
            self._play_on = enabled
            self._render()

    def off(self) -> None:
        with self._lock:
            self._app_on = False
            self._record_on = False
            self._play_on = False
            self._render()

    def _render(self) -> None:
        self.dev.set_pixel(self.APP_LED, 0, 32 if self._app_on else 0, 0)
        self.dev.set_pixel(self.RECORD_LED, 64 if self._record_on else 0, 0, 0)
        self.dev.set_pixel(self.PLAY_LED, 0, 0, 255 if self._play_on else 0)
        self.dev.show()
