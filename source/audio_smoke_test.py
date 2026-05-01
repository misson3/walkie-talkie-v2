from __future__ import annotations

import argparse
import asyncio
import logging
import subprocess
from pathlib import Path

from .audio_manager import AudioManager
from .config import load_config


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


async def record_and_verify(duration_s: float = 5.0) -> None:
    cfg = load_config()
    audio = AudioManager(audio_device=cfg.audio_device)

    test_file = Path("/tmp/audio_smoke_test.ogg")
    test_file.parent.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Starting %s-second audio recording test to %s", duration_s, test_file)

    started = audio.start_recording(test_file)
    if not started:
        LOGGER.error("Failed to start recording")
        return

    await asyncio.sleep(duration_s)
    stopped = audio.stop_recording()
    if not stopped:
        LOGGER.warning("Recording stop returned False (may be OK)")

    await asyncio.sleep(0.5)

    if not test_file.exists():
        LOGGER.error("No output file created at %s", test_file)
        return

    file_size = test_file.stat().st_size
    LOGGER.info("Output file: %s, size: %s bytes", test_file, file_size)

    if file_size == 0:
        LOGGER.error("Output file is empty")
        return

    try:
        result = subprocess.run(
            ["file", str(test_file)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        LOGGER.info("File type: %s", result.stdout.strip())
    except Exception:
        LOGGER.warning("Could not run 'file' command")

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", "-show_streams", str(test_file)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            LOGGER.info("FFprobe output:\n%s", result.stdout)
        else:
            LOGGER.warning("FFprobe failed: %s", result.stderr)
    except FileNotFoundError:
        LOGGER.warning("ffprobe not installed; skipping detailed format check")
    except Exception:
        LOGGER.warning("Could not run ffprobe")

    LOGGER.info(
        "Manual playback command: ffmpeg -i %s -ac 2 -f alsa %s",
        test_file,
        cfg.audio_device,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Audio record/format smoke test")
    parser.add_argument(
        "--seconds", type=float, default=5.0, help="Record duration in seconds"
    )
    args = parser.parse_args()
    asyncio.run(record_and_verify(duration_s=args.seconds))


if __name__ == "__main__":
    main()
