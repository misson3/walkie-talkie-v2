from __future__ import annotations

import json
import logging
import subprocess
import tempfile
import wave
from pathlib import Path


LOGGER = logging.getLogger(__name__)

# Module-level model cache: model_path -> vosk.Model instance
_MODEL_CACHE: dict[str, object] = {}


def _get_model(model_path: str) -> object:
    """Load and cache a Vosk model by directory path."""
    if model_path not in _MODEL_CACHE:
        from vosk import Model  # type: ignore[import-not-found]

        LOGGER.info("Loading Vosk model from %s", model_path)
        _MODEL_CACHE[model_path] = Model(model_path)
        LOGGER.info("Vosk model loaded from %s", model_path)
    return _MODEL_CACHE[model_path]


def _convert_to_wav(input_path: Path, output_path: Path) -> bool:
    """Convert any audio file to 16 kHz mono PCM WAV using ffmpeg."""
    command = [
        "ffmpeg",
        "-nostdin",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        "-y",
        str(output_path),
    ]
    try:
        result = subprocess.run(command, timeout=30.0)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        LOGGER.exception("ffmpeg wav conversion failed for %s", input_path)
        return False


def transcribe(audio_path: Path, model_path: str) -> str | None:
    """
    Transcribe audio_path using the Vosk model at model_path.

    The audio file is converted to 16 kHz mono WAV before recognition.
    Returns the recognised text (may be empty string) or None on hard failure.
    """
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        LOGGER.warning("Transcription skipped: file missing or empty: %s", audio_path)
        return None

    if not model_path:
        LOGGER.warning("Transcription skipped: VOSK_MODEL_PATH is not configured")
        return None

    try:
        model = _get_model(model_path)
    except Exception:
        LOGGER.exception("Failed to load Vosk model from %s", model_path)
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = Path(tmpdir) / "transcribe.wav"
        if not _convert_to_wav(audio_path, wav_path):
            LOGGER.warning("Transcription skipped: wav conversion failed")
            return None

        try:
            from vosk import KaldiRecognizer  # type: ignore[import-not-found]

            with wave.open(str(wav_path), "rb") as wf:
                sample_rate = wf.getframerate()
                rec = KaldiRecognizer(model, sample_rate)
                rec.SetWords(True)

                text_parts: list[str] = []
                while True:
                    data = wf.readframes(4000)
                    if not data:
                        break
                    if rec.AcceptWaveform(data):
                        part = json.loads(rec.Result()).get("text", "").strip()
                        if part:
                            text_parts.append(part)

                final_part = json.loads(rec.FinalResult()).get("text", "").strip()
                if final_part:
                    text_parts.append(final_part)

            full_text = " ".join(text_parts).strip()
            LOGGER.info("Transcription result for %s: %r", audio_path.name, full_text)
            return full_text

        except Exception:
            LOGGER.exception("Vosk recognition failed for %s", audio_path)
            return None


# ---------------------------------------------------------------------------
# Smoke test:  python -m source.vosk_transcriber <model_path> <audio_file>
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

    if len(sys.argv) != 3:
        print("Usage: python -m source.vosk_transcriber <model_path> <audio_file>")
        sys.exit(1)

    _model_path = sys.argv[1]
    _audio_path = Path(sys.argv[2])

    result = transcribe(_audio_path, _model_path)
    if result is None:
        print("Transcription failed (see log above)")
        sys.exit(1)
    elif result == "":
        print("Transcription produced empty text (silence or inaudible)")
    else:
        print(f"Transcription: {result}")
