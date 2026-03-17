from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class TtsEngine(ABC):
    """Abstract TTS engine interface."""

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        self.options = options or {}

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError
