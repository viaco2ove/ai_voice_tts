from __future__ import annotations

from typing import Any

from .base import AsrEngine, AsrResult


class LocalWhisperAsrEngine(AsrEngine):
    @property
    def name(self) -> str:
        return "local_whisper"

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
        del audio_format
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:
            raise RuntimeError("faster-whisper is not installed. Run: pip install faster-whisper") from exc

        model_name = str(self.options.get("model", "base"))
        device = str(self.options.get("device", "cpu"))
        compute_type = str(self.options.get("compute_type", "int8"))
        beam_size = int(self.options.get("beam_size", 5))
        vad_filter = bool(self.options.get("vad_filter", True))
        best_of = int(self.options.get("best_of", 5))

        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        segments, info = model.transcribe(
            audio=audio_bytes,
            language=language,
            prompt=prompt,
            temperature=temperature,
            beam_size=beam_size,
            best_of=best_of,
            vad_filter=vad_filter,
        )

        result_segments: list[dict[str, Any]] = []
        texts: list[str] = []
        for seg in segments:
            result_segments.append({"start": seg.start, "end": seg.end, "text": seg.text})
            texts.append(seg.text)

        text = "".join(texts).strip()
        is_final = mode != "stream"
        return AsrResult(text=text, language=info.language, segments=result_segments, is_final=is_final)
