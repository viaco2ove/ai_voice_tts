from __future__ import annotations

import math
import struct
import wave
from pathlib import Path
from typing import Any

from .base import TtsEngine


class MockTtsEngine(TtsEngine):
    """Fallback engine that writes a short tone WAV for local pipeline testing."""

    @property
    def name(self) -> str:
        return "mock"

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
        if audio_format != "wav":
            raise ValueError("mock engine only supports wav")

        sample_rate = 24000
        duration_seconds = max(0.4, min(4.0, len(text) / 24.0))
        total_frames = int(sample_rate * duration_seconds)
        amplitude = 8000
        frequency = 440.0 if voice_id.endswith("male") else 523.25
        if mode == "clone" and reference_audio_base64:
            frequency = 659.25
        elif mode == "mix" and mix_voices:
            frequency = 587.33
        elif mode == "prompt_voice" and prompt_text:
            frequency = 493.88

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            for i in range(total_frames):
                sample = amplitude * math.sin(2.0 * math.pi * frequency * i / sample_rate)
                wav_file.writeframes(struct.pack("<h", int(sample)))
