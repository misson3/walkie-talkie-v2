from __future__ import annotations

import argparse
import logging
import time

import RPi.GPIO as GPIO

from .config import load_config
from .interfaces.pixels import Pixels


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


def _is_pressed(level: int, active_low: bool) -> bool:
    return (level == GPIO.LOW) if active_low else (level == GPIO.HIGH)


def run(duration_s: float) -> None:
    cfg = load_config()
    pixels = Pixels()

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(
        cfg.gpio_record_pin,
        GPIO.IN,
        pull_up_down=GPIO.PUD_UP if cfg.gpio_record_active_low else GPIO.PUD_DOWN,
    )
    GPIO.setup(
        cfg.gpio_replay_pin,
        GPIO.IN,
        pull_up_down=GPIO.PUD_UP if cfg.gpio_replay_active_low else GPIO.PUD_DOWN,
    )

    LOGGER.info("Starting hardware smoke test for %.1f seconds", duration_s)
    LOGGER.info(
        "Button A GPIO%s active_low=%s | Button B GPIO%s active_low=%s",
        cfg.gpio_record_pin,
        cfg.gpio_record_active_low,
        cfg.gpio_replay_pin,
        cfg.gpio_replay_active_low,
    )

    try:
        start = time.monotonic()
        while time.monotonic() - start < duration_s:
            level_a = GPIO.input(cfg.gpio_record_pin)
            level_b = GPIO.input(cfg.gpio_replay_pin)
            pressed_a = _is_pressed(level_a, cfg.gpio_record_active_low)
            pressed_b = _is_pressed(level_b, cfg.gpio_replay_active_low)

            pixels.set_app_running(True)
            pixels.set_recording(pressed_a)
            pixels.set_playing(pressed_b)

            LOGGER.info(
                "A: level=%s pressed=%s | B: level=%s pressed=%s",
                level_a,
                pressed_a,
                level_b,
                pressed_b,
            )
            time.sleep(0.2)
    finally:
        pixels.off()
        GPIO.cleanup([cfg.gpio_record_pin, cfg.gpio_replay_pin])
        LOGGER.info("Hardware smoke test finished")


def main() -> None:
    parser = argparse.ArgumentParser(description="GPIO/LED smoke test")
    parser.add_argument("--seconds", type=float, default=20.0, help="Test duration in seconds")
    args = parser.parse_args()
    run(duration_s=args.seconds)


if __name__ == "__main__":
    main()
