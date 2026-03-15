from __future__ import annotations

import os

from .engines.base import TtsEngine
from .engines.cosyvoice_http_engine import CosyVoiceHttpEngine
from .engines.edge_tts_engine import EdgeTtsEngine
from .engines.mock_engine import MockTtsEngine


def build_engine() -> TtsEngine:
    engine_name = os.getenv("TTS_ENGINE", "mock").strip().lower()

    if engine_name == "mock":
        return MockTtsEngine()
    if engine_name == "edge_tts":
        return EdgeTtsEngine()
    if engine_name == "cosyvoice_http":
        return CosyVoiceHttpEngine()

    raise ValueError(f"Unsupported TTS_ENGINE: {engine_name}")
