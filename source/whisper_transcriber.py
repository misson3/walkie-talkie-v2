from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class WhisperTranscriber:
    def __init__(
        self,
        cli_path: Path,
        model_path: Path,
        language: str,
        threads: int,
        timeout_s: float,
    ):
        self._cli_path = cli_path
        self._model_path = model_path
        self._language = language
        self._threads = threads
        self._timeout_s = timeout_s

    def snapshot_input(self, source_file: Path) -> Path:
        if not source_file.exists():
            raise FileNotFoundError(source_file)

        source_suffix = source_file.suffix or ".ogg"
        with tempfile.NamedTemporaryFile(
            prefix=f"{source_file.stem}-whisper-",
            suffix=source_suffix,
            delete=False,
            dir=source_file.parent,
        ) as snapshot_handle:
            snapshot_path = Path(snapshot_handle.name)

        shutil.copy2(source_file, snapshot_path)
        return snapshot_path

    def transcribe_snapshot(self, snapshot_file: Path) -> str | None:
        with tempfile.TemporaryDirectory(prefix="whisper-transcribe-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            wav_path = temp_dir / "input.wav"
            output_prefix = temp_dir / "transcript"
            output_path = output_prefix.with_suffix(".txt")

            try:
                self._convert_to_wav(snapshot_file, wav_path)
                self._run_whisper(wav_path, output_prefix)
                if not output_path.exists():
                    LOGGER.warning("Whisper output text file was not created: %s", output_path)
                    return None
                return self._normalize_transcript(output_path.read_text(encoding="utf-8"))
            finally:
                snapshot_file.unlink(missing_ok=True)

    def _convert_to_wav(self, source_file: Path, wav_path: Path) -> None:
        command = [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-i",
            str(source_file),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            "-y",
            str(wav_path),
        ]
        self._run_command(command, timeout_s=self._timeout_s)

    def _run_whisper(self, wav_path: Path, output_prefix: Path) -> None:
        command = [
            str(self._cli_path),
            "-m",
            str(self._model_path),
            "-f",
            str(wav_path),
            "-l",
            self._language,
            "-t",
            str(self._threads),
            "-otxt",
            "-of",
            str(output_prefix),
            "-nt",
            "-np",
        ]
        self._run_command(command, timeout_s=self._timeout_s)

    def _run_command(self, command: list[str], timeout_s: float) -> None:
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except OSError as exc:
            raise RuntimeError(f"Failed to execute command: {command[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Command timed out after {timeout_s} seconds: {command[0]}") from exc

        if result.returncode != 0:
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            details = stderr or stdout or f"exit code {result.returncode}"
            raise RuntimeError(f"Command failed: {details}")

    @staticmethod
    def _normalize_transcript(content: str) -> str | None:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return None
        transcript = "\n".join(lines)
        return transcript or None