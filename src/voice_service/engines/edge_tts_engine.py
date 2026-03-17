from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import TtsEngine


class EdgeTtsEngine(TtsEngine):
    """Online TTS via edge-tts. Requires network and edge-tts package."""

    @property
    def name(self) -> str:
        return "edge_tts"

    async def synthesize(
        self,
        *,
        text: str,
        voice_id: str,
        speed: float,
        output_path: Path,
        audio_format: str,
        mode: str = "text",
        reference_audio_base64: str | None = None,
        reference_text: str | None = None,
        prompt_text: str | None = None,
        mix_voices: list[dict[str, Any]] | None = None,
    ) -> None:
        if mode not in {"text", "prompt_voice", "mix"}:
            raise ValueError("edge_tts 暂不支持 clone 模式")
        if audio_format != "mp3":
            raise ValueError("edge_tts engine currently supports mp3 only")

        try:
            import edge_tts  # type: ignore
        except ImportError as exc:
            raise RuntimeError("edge-tts is not installed. Run: pip install edge-tts") from exc

        voice = voice_id or self.options.get("default_voice_id", "zh-CN-XiaoxiaoNeural")
        rate_percent = int((speed - 1.0) * 100)
        rate_str = f"{rate_percent:+d}%"
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate_str)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await communicate.save(str(output_path))
