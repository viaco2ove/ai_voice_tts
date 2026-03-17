from __future__ import annotations

import os
from typing import Any

from .engines.base import TtsEngine
from .engines.cosyvoice_http_engine import CosyVoiceHttpEngine
from .engines.edge_tts_engine import EdgeTtsEngine
from .engines.mock_engine import MockTtsEngine


def build_engine(
    provider_name: str | None = None,
    engine_name: str | None = None,
    options: dict[str, Any] | None = None,
) -> TtsEngine:
    del provider_name
    resolved_engine = (engine_name or os.getenv("TTS_ENGINE", "mock")).strip().lower()
    resolved_options = options or {}

    if resolved_engine == "mock":
        return MockTtsEngine(resolved_options)
    if resolved_engine == "edge_tts":
        return EdgeTtsEngine(resolved_options)
    if resolved_engine == "cosyvoice_http":
        return CosyVoiceHttpEngine(resolved_options)

    raise ValueError(f"Unsupported TTS engine: {resolved_engine}")
