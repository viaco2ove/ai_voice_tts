from __future__ import annotations

import json
from typing import Any

from .base import AsrEngine, AsrResult


class VoskAsrEngine(AsrEngine):
    @property
    def name(self) -> str:
        return "vosk"

    @property
    def supports_stream(self) -> bool:
        return True

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        audio_format: str | None,
        language: str | None,
        prompt: str | None,
        temperature: float | None,
        mode: str = "file",
    ) -> AsrResult:
        del audio_format, language, prompt, temperature
        try:
            from vosk import KaldiRecognizer, Model  # type: ignore
        except ImportError as exc:
            raise RuntimeError("vosk is not installed. Run: pip install vosk") from exc

        model_path = str(self.options.get("model_path", "models/vosk"))
        sample_rate = int(self.options.get("sample_rate", 16000))
        model = Model(model_path)
        rec = KaldiRecognizer(model, sample_rate)

        if mode == "stream":
            if rec.AcceptWaveform(audio_bytes):
                result = json.loads(rec.Result())
                return AsrResult(text=str(result.get("text", "")).strip(), language=None, segments=[], is_final=False)
            result = json.loads(rec.PartialResult())
            return AsrResult(text=str(result.get("partial", "")).strip(), language=None, segments=[], is_final=False)

        rec.AcceptWaveform(audio_bytes)
        result = json.loads(rec.FinalResult())
        return AsrResult(text=str(result.get("text", "")).strip(), language=None, segments=[], is_final=True)
