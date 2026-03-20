from __future__ import annotations

from typing import Any

from .base import AsrEngine
from .http_asr_engine import HttpAsrEngine
from .local_whisper_engine import LocalWhisperAsrEngine
from .mock_asr_engine import MockAsrEngine


def build_asr_engine(engine_name: str, options: dict[str, Any] | None = None) -> AsrEngine:
    resolved = engine_name.strip().lower()
    resolved_options = options or {}

    if resolved == "mock_asr":
        return MockAsrEngine(resolved_options)
    if resolved == "asr_http":
        return HttpAsrEngine(resolved_options)
    if resolved == "local_whisper":
        return LocalWhisperAsrEngine(resolved_options)

    raise ValueError(f"Unsupported ASR engine: {engine_name}")
