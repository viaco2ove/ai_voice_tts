from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TtsEngine(ABC):
    """Abstract TTS engine interface."""

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
        reference_audio_base64: str | None = None,
    ) -> None:
        raise NotImplementedError
