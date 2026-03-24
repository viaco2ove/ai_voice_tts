from __future__ import annotations

import unittest

from src.voice_service.engines.cosyvoice_http_engine import CosyVoiceHttpEngine


class CosyVoiceHttpEngineTests(unittest.TestCase):
    def test_prompt_voice_uses_instruct_api_when_configured(self) -> None:
        engine = CosyVoiceHttpEngine(
            {
                "api_url": "http://127.0.0.1:9233/tts",
                "instruct_api_url": "http://127.0.0.1:9233/instruct",
                "request_mode": "form",
            }
        )

        api_url = engine._resolve_api_url("prompt_voice")

        self.assertEqual(api_url, "http://127.0.0.1:9233/instruct")

    def test_prompt_voice_form_payload_contains_prompt_text(self) -> None:
        engine = CosyVoiceHttpEngine({"request_mode": "form"})

        payload = engine._build_form_payload(
            text="你好",
            voice_id="default_male",
            speed=1.0,
            mode="prompt_voice",
            reference_audio_base64=None,
            reference_text=None,
            prompt_text="青年男性，干练，坚定",
        )

        self.assertEqual(payload["role"], "中文男")
        self.assertEqual(payload["prompt_text"], "青年男性，干练，坚定")
