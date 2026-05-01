from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from google.api_core.exceptions import GoogleAPICallError, InvalidArgument  # type: ignore[import-not-found]
from google.cloud import speech  # type: ignore[import-not-found]


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SttTranscript:
    text: str
    confidence: float | None
    used_fallback: bool


class GoogleSpeechToTextClient:
    def __init__(
        self,
        language_code: str,
        model: str = "",
        timeout_s: float = 15.0,
        credentials_path: str = "",
    ):
        if credentials_path:
            os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", credentials_path)

        self._language_code = language_code
        self._model = model.strip()
        self._timeout_s = timeout_s
        self._client = speech.SpeechClient()

    def transcribe_file(self, voice_file: Path) -> SttTranscript | None:
        payload = voice_file.read_bytes()
        if not payload:
            LOGGER.warning("STT skipped because input file is empty: %s", voice_file)
            return None

        try:
            response = self._recognize(
                audio_bytes=payload,
                encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
                sample_rate_hertz=16000,
            )
            parsed = self._parse_response(response)
            if parsed is None:
                return None
            return SttTranscript(
                text=parsed.text,
                confidence=parsed.confidence,
                used_fallback=False,
            )
        except InvalidArgument:
            LOGGER.warning(
                "Direct OGG_OPUS recognition failed with InvalidArgument. Trying FLAC fallback.",
                exc_info=True,
            )
            return self._transcribe_with_flac_fallback(voice_file)

    def _recognize(
        self,
        audio_bytes: bytes,
        encoding: speech.RecognitionConfig.AudioEncoding,
        sample_rate_hertz: int,
    ) -> speech.RecognizeResponse:
        config_kwargs: dict[str, object] = {
            "encoding": encoding,
            "sample_rate_hertz": sample_rate_hertz,
            "language_code": self._language_code,
            "enable_automatic_punctuation": True,
        }
        if self._model:
            config_kwargs["model"] = self._model

        config = speech.RecognitionConfig(**config_kwargs)
        audio = speech.RecognitionAudio(content=audio_bytes)
        return self._client.recognize(
            config=config, audio=audio, timeout=self._timeout_s
        )

    def _transcribe_with_flac_fallback(self, voice_file: Path) -> SttTranscript | None:
        with tempfile.TemporaryDirectory(prefix="stt-") as tmp_dir:
            flac_path = Path(tmp_dir) / "input.flac"
            command = [
                "ffmpeg",
                "-nostdin",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(voice_file),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "flac",
                str(flac_path),
            ]

            try:
                subprocess.run(command, check=True)
            except (OSError, subprocess.CalledProcessError):
                LOGGER.exception("FFmpeg conversion to FLAC failed")
                return None

            flac_bytes = flac_path.read_bytes()
            if not flac_bytes:
                LOGGER.warning("STT fallback produced empty FLAC output")
                return None

            try:
                response = self._recognize(
                    audio_bytes=flac_bytes,
                    encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
                    sample_rate_hertz=16000,
                )
            except GoogleAPICallError:
                LOGGER.exception("FLAC fallback recognition failed")
                return None

            parsed = self._parse_response(response)
            if parsed is None:
                return None
            return SttTranscript(
                text=parsed.text,
                confidence=parsed.confidence,
                used_fallback=True,
            )

    def _parse_response(
        self, response: speech.RecognizeResponse
    ) -> SttTranscript | None:
        transcripts: list[str] = []
        confidence: float | None = None

        for result in response.results:
            if not result.alternatives:
                continue
            top = result.alternatives[0]
            text = top.transcript.strip()
            if not text:
                continue
            transcripts.append(text)
            if confidence is None and getattr(top, "confidence", 0.0) > 0.0:
                confidence = float(top.confidence)

        if not transcripts:
            return None

        return SttTranscript(
            text=" ".join(transcripts), confidence=confidence, used_fallback=False
        )
