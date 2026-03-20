from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AsrResult:
    text: str
    language: str | None = None
    segments: list[dict[str, Any]] = field(default_factory=list)
    is_final: bool = True


class AsrEngine(ABC):
    def __init__(self, options: dict[str, Any] | None = None) -> None:
        self.options = options or {}

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    def supports_stream(self) -> bool:
        return False

    @abstractmethod
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
        raise NotImplementedError
