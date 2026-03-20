from __future__ import annotations

from .base import AsrEngine, AsrResult


class MockAsrEngine(AsrEngine):
    @property
    def name(self) -> str:
        return "mock_asr"

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
        del audio_format, prompt, temperature
        if mode == "stream":
            text = f"mock partial ({len(audio_bytes)} bytes)"
            return AsrResult(text=text, language=language, segments=[], is_final=False)
        text = "mock transcription"
        return AsrResult(text=text, language=language, segments=[], is_final=True)
