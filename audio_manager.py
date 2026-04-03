from __future__ import annotations

import logging
import subprocess
import threading
import time
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class AudioManager:
    def __init__(self, audio_device: str):
        self.audio_device = audio_device
        self._lock = threading.Lock()
        self._record_process: subprocess.Popen[bytes] | None = None
        self._play_process: subprocess.Popen[bytes] | None = None

    def start_recording(self, output_file: Path) -> bool:
        with self._lock:
            self._clear_finished_processes_locked()
            if self.is_recording or self.is_playing:
                return False

            output_file.parent.mkdir(parents=True, exist_ok=True)
            command = [
                "ffmpeg",
                "-nostdin",
                "-loglevel",
                "error",
                "-f",
                "alsa",
                "-i",
                self.audio_device,
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "libopus",
                "-b:a",
                "24k",
                "-y",
                str(output_file),
            ]
            try:
                self._record_process = subprocess.Popen(command)
            except OSError:
                LOGGER.exception("Failed to start recording process")
                self._record_process = None
                return False
            return True

    def stop_recording(self, timeout_s: float = 5.0) -> bool:
        with self._lock:
            process = self._record_process
            self._record_process = None

        if process is None:
            return False

        process.terminate()
        try:
            process.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout_s)

        return process.returncode == 0

    def play_recording_end_beep(
        self,
        high_frequency_hz: int = 2525,
        low_frequency_hz: int = 2475,
        high_duration_s: float = 0.25,
        low_duration_s: float = 0.25,
        gap_s: float = 0.05,
        volume: float = 1.0,
        allow_while_recording: bool = False,
    ) -> bool:
        with self._lock:
            self._clear_finished_processes_locked()
            if self.is_playing:
                return False
            if self.is_recording and not allow_while_recording:
                return False

        try:
            first_ok = self._play_tone(high_frequency_hz, high_duration_s, volume)
            if not first_ok:
                return False

            if gap_s > 0:
                time.sleep(gap_s)

            second_ok = self._play_tone(low_frequency_hz, low_duration_s, volume)
            return second_ok
        except OSError:
            LOGGER.exception("Failed to play recording end beep")
            return False
        except subprocess.SubprocessError:
            LOGGER.exception("Recording end beep process failed")
            return False

    def _play_tone(self, frequency_hz: int, duration_s: float, volume: float) -> bool:
        command = [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency_hz}:duration={duration_s}",
            "-af",
            f"volume={volume}",
            "-ac",
            "2",
            "-f",
            "alsa",
            self.audio_device,
        ]
        timeout_s = max(1.0, duration_s + 1.0)
        result = subprocess.run(command, timeout=timeout_s)
        return result.returncode == 0

    def start_playback(self, input_file: Path) -> bool:
        with self._lock:
            self._clear_finished_processes_locked()
            if self.is_recording or self.is_playing:
                return False
            if not input_file.exists():
                return False

            command = [
                "ffmpeg",
                "-nostdin",
                "-loglevel",
                "error",
                "-i",
                str(input_file),
                "-ac",
                "2",
                "-f",
                "alsa",
                self.audio_device,
            ]
            try:
                self._play_process = subprocess.Popen(command)
            except OSError:
                LOGGER.exception("Failed to start playback process")
                self._play_process = None
                return False
            return True

    def stop_playback(self, timeout_s: float = 3.0) -> bool:
        with self._lock:
            process = self._play_process
            self._play_process = None

        if process is None:
            return False

        process.terminate()
        try:
            process.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout_s)

        return process.returncode == 0

    @property
    def is_recording(self) -> bool:
        process = self._record_process
        return process is not None and process.poll() is None

    @property
    def is_playing(self) -> bool:
        process = self._play_process
        return process is not None and process.poll() is None

    def _clear_finished_processes_locked(self) -> None:
        if self._record_process is not None and self._record_process.poll() is not None:
            LOGGER.info("Previous recording process exited with code %s", self._record_process.returncode)
            self._record_process = None

        if self._play_process is not None and self._play_process.poll() is not None:
            LOGGER.info("Previous playback process exited with code %s", self._play_process.returncode)
            self._play_process = None
