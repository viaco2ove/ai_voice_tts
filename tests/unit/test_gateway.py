from __future__ import annotations

import unittest
from pathlib import Path

from src.voice_service.config import (
    AppConfig,
    AsrGatewayConfig,
    GatewayConfig,
    ProviderConfig,
    StartupConfig,
    StylePreset,
    VoicePreset,
)
from src.voice_service.gateway import TtsGateway
from src.voice_service.models import StandardTtsRequest


class PromptVoiceFallbackTests(unittest.TestCase):
    def _build_gateway(self) -> TtsGateway:
        config = AppConfig(
            path=Path("config/services.yaml"),
            gateway=GatewayConfig(default_provider="cosyvoice_local"),
            providers={
                "cosyvoice_local": ProviderConfig(
                    name="cosyvoice_local",
                    engine="mock",
                    default_voice_id="default_female",
                    default_format="wav",
                    supported_modes=["text", "prompt_voice"],
                    startup=StartupConfig(),
                ),
                "edge_online": ProviderConfig(
                    name="edge_online",
                    engine="mock",
                    default_voice_id="zh-CN-XiaoxiaoNeural",
                    default_format="wav",
                    supported_modes=["text", "prompt_voice"],
                    startup=StartupConfig(),
                ),
            },
            voice_presets=[
                VoicePreset(
                    id="default_female",
                    label="默认中文女声",
                    provider="cosyvoice_local",
                    voice_id="default_female",
                    description="默认中文女声，适合通用播报",
                ),
                VoicePreset(
                    id="default_male",
                    label="默认中文男声",
                    provider="cosyvoice_local",
                    voice_id="default_male",
                    description="默认中文男声，适合说明类内容",
                ),
                VoicePreset(
                    id="edge_xiaoxiao",
                    label="Edge 晓晓",
                    provider="edge_online",
                    voice_id="zh-CN-XiaoxiaoNeural",
                    description="云端中文女声",
                ),
            ],
            style_presets=[
                StylePreset(
                    id="warm_story",
                    label="温柔讲述",
                    provider="cosyvoice_local",
                    voice_id="default_female",
                    prompt_keywords=["温柔", "治愈", "讲述", "故事"],
                    description="适合故事解说、情绪平稳内容",
                ),
                StylePreset(
                    id="steady_male",
                    label="沉稳男声",
                    provider="cosyvoice_local",
                    voice_id="default_male",
                    prompt_keywords=["沉稳", "纪录片", "说明", "男声", "男性", "磁性", "口播", "坚定", "干练"],
                    description="适合纪录片旁白和口播",
                ),
                StylePreset(
                    id="bright_stream",
                    label="明快播报",
                    provider="edge_online",
                    voice_id="zh-CN-XiaoxiaoNeural",
                    prompt_keywords=["活泼", "明快", "播报", "直播", "明亮", "自信", "朝气", "有力", "爽朗"],
                    description="适合轻快播报场景",
                ),
            ],
            asr_gateway=AsrGatewayConfig(),
            asr_providers={},
        )
        return TtsGateway(config)

    def test_prompt_voice_falls_back_to_default_voice_when_no_style_matches(self) -> None:
        gateway = self._build_gateway()
        req = StandardTtsRequest(
            text="请更自然一点。",
            mode="prompt_voice",
            prompt_text="自然 亲切 日常对话",
        )

        provider, resolved_voice_id = gateway._resolve_provider_and_voice(req)

        self.assertEqual(provider.name, "cosyvoice_local")
        self.assertEqual(resolved_voice_id, "default_female")

    def test_prompt_voice_prefers_explicit_voice_id_when_no_style_matches(self) -> None:
        gateway = self._build_gateway()
        req = StandardTtsRequest(
            text="请更自然一点。",
            provider="cosyvoice_local",
            voice_id="custom_voice",
            mode="prompt_voice",
            prompt_text="自然 亲切 日常对话",
        )

        _, resolved_voice_id = gateway._resolve_provider_and_voice(req)

        self.assertEqual(resolved_voice_id, "custom_voice")

    def test_prompt_voice_matches_freeform_male_prompt_to_male_style(self) -> None:
        gateway = self._build_gateway()
        req = StandardTtsRequest(
            text="你好，欢迎见到你。",
            mode="prompt_voice",
            prompt_text="一位干练明亮有力的青年男性，语调张扬自信，语速偏快，充满活力与朝气，口吻坚定果决。",
        )

        provider, resolved_voice_id = gateway._resolve_provider_and_voice(req)

        self.assertEqual(provider.name, "cosyvoice_local")
        self.assertEqual(resolved_voice_id, "default_male")

    def test_prompt_voice_matches_gentle_story_prompt_to_warm_story(self) -> None:
        gateway = self._build_gateway()
        req = StandardTtsRequest(
            text="今天给你讲一个小故事。",
            mode="prompt_voice",
            prompt_text="温暖治愈、细腻温柔地讲述一个故事。",
        )

        provider, resolved_voice_id = gateway._resolve_provider_and_voice(req)

        self.assertEqual(provider.name, "cosyvoice_local")
        self.assertEqual(resolved_voice_id, "default_female")
