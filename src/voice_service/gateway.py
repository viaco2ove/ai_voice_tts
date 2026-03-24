from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .config import AppConfig, ProviderConfig, StylePreset, VoicePreset
from .engine_factory import build_engine
from .models import ProviderInfo, StandardTtsRequest, TtsResponse, VoicePresetInfo


SIGNAL_TERMS: dict[str, tuple[str, ...]] = {
    "male": ("男声", "男性", "男生", "男", "青年男性", "青年男", "少年感", "磁性男"),
    "female": ("女声", "女性", "女生", "女", "少女", "御姐", "甜妹"),
    "gentle": ("温柔", "治愈", "柔和", "轻柔", "温暖", "暖心", "细腻", "抒情"),
    "story": ("故事", "讲述", "叙述", "娓娓道来", "旁白"),
    "steady": ("沉稳", "稳重", "成熟", "纪录片", "说明", "口播", "专业", "坚定", "果决", "磁性", "低沉", "干练"),
    "bright": ("活泼", "明快", "明亮", "清亮", "轻快", "朝气", "元气", "年轻", "青年", "张扬", "自信", "热情", "有力", "爽朗"),
    "broadcast": ("播报", "直播", "主持", "主播", "口播"),
}


class TtsGateway:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.output_dir = Path(config.gateway.output_dir).resolve()
        self.providers = {name: provider for name, provider in config.providers.items() if provider.enabled}
        self.engines = {
            name: build_engine(provider_name=name, engine_name=provider.engine, options=provider.options)
            for name, provider in self.providers.items()
        }

    def health(self) -> dict[str, str]:
        return {
            "status": "ok",
            "default_provider": self.config.gateway.default_provider,
            "providers": ",".join(sorted(self.providers.keys())),
        }

    def list_providers(self) -> list[ProviderInfo]:
        return [
            ProviderInfo(
                provider=provider.name,
                engine=provider.engine,
                enabled=provider.enabled,
                default_voice_id=provider.default_voice_id,
                default_format=provider.default_format,
                supported_modes=list(provider.supported_modes),
            )
            for provider in self.providers.values()
        ]

    def list_voice_presets(self) -> list[VoicePresetInfo]:
        return [
            VoicePresetInfo(
                id=item.id,
                label=item.label,
                provider=item.provider,
                voice_id=item.voice_id,
                modes=list(item.modes),
                description=item.description,
            )
            for item in self.config.voice_presets
        ]

    async def synthesize(self, req: StandardTtsRequest) -> TtsResponse:
        provider, resolved_voice_id = self._resolve_provider_and_voice(req)
        resolved_format = self._resolve_output_format(provider, req.format)
        engine = self.engines[provider.name]
        self.output_dir.mkdir(parents=True, exist_ok=True)

        file_name = f"{self._cache_key(req, provider.name, resolved_voice_id, resolved_format)}.{resolved_format}"
        output_path = self.output_dir / file_name

        if req.use_cache and output_path.exists():
            return self._build_response(req, provider.name, engine.name, resolved_voice_id, True, file_name, output_path)

        await engine.synthesize(
            text=req.text,
            voice_id=resolved_voice_id,
            speed=req.speed,
            output_path=output_path,
            audio_format=resolved_format,
            mode=req.mode,
            reference_audio_base64=req.reference_audio_base64,
            reference_text=req.reference_text,
            prompt_text=req.prompt_text,
            mix_voices=[item.model_dump() for item in req.mix_voices],
        )
        return self._build_response(req, provider.name, engine.name, resolved_voice_id, False, file_name, output_path)

    def _resolve_output_format(self, provider: ProviderConfig, requested_format: str | None) -> str:
        resolved_format = requested_format or provider.default_format

        # edge_tts 当前只支持 mp3。prompt_voice/mix 可能把请求路由到 edge_online，
        # 前端若仍然固定传 wav，会导致不必要的 400。这里统一回退到 provider 默认格式。
        if provider.engine == "edge_tts" and resolved_format != "mp3":
            return provider.default_format or "mp3"
        return resolved_format

    def _build_response(
        self,
        req: StandardTtsRequest,
        provider: str,
        engine: str,
        resolved_voice_id: str,
        cache_hit: bool,
        file_name: str,
        output_path: Path,
    ) -> TtsResponse:
        return TtsResponse(
            provider=provider,
            engine=engine,
            mode=req.mode,
            resolved_voice_id=resolved_voice_id,
            cache_hit=cache_hit,
            file_name=file_name,
            audio_path=str(output_path),
            audio_url=f"/audio/{file_name}",
        )

    def _cache_key(self, req: StandardTtsRequest, provider_name: str, resolved_voice_id: str, resolved_format: str) -> str:
        ref_hash = ""
        if req.reference_audio_base64:
            ref_hash = hashlib.sha256(req.reference_audio_base64.encode("utf-8")).hexdigest()[:12]
        mix_signature = ",".join(f"{item.voice_id}:{item.weight:.3f}" for item in req.mix_voices)
        normalized = "|".join(
            [
                provider_name,
                req.mode,
                req.text.strip(),
                resolved_voice_id.strip(),
                f"{req.speed:.2f}",
                resolved_format,
                (req.reference_text or "").strip(),
                (req.prompt_text or "").strip(),
                mix_signature,
                ref_hash,
            ]
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]

    def _resolve_provider_and_voice(self, req: StandardTtsRequest) -> tuple[ProviderConfig, str]:
        provider_name = req.provider or self.config.gateway.default_provider
        resolved_voice_id = req.voice_id or ""

        if req.mode == "prompt_voice":
            prompt_text = req.prompt_text or ""
            current_provider = self.providers.get(provider_name)
            # 按 provider 的真实能力分流：
            # 1. 当前 provider 支持原生 prompt/instruct，就优先走真实能力，不跨 provider 路由。
            # 2. 当前 provider 不支持原生 prompt，再退回到 style_presets 做路由。
            if current_provider and self._provider_supports_native_prompt(current_provider):
                style = self._resolve_style_preset(prompt_text, provider_name=current_provider.name)
                if style:
                    resolved_voice_id = style.voice_id
                if not resolved_voice_id:
                    inferred_voice_id = self._infer_voice_from_prompt(current_provider.name, prompt_text)
                    if inferred_voice_id:
                        resolved_voice_id = inferred_voice_id
            else:
                style = self._resolve_style_preset(prompt_text)
                if style:
                    provider_name = style.provider
                    resolved_voice_id = style.voice_id

        if req.mode == "mix":
            dominant = max(req.mix_voices, key=lambda item: item.weight)
            resolved_voice_id = dominant.voice_id

        preset = self._find_voice_preset(resolved_voice_id)
        if preset:
            provider_name = req.provider or preset.provider
            resolved_voice_id = preset.voice_id

        provider = self.providers.get(provider_name)
        if not provider:
            raise ValueError(f"provider 不存在或未启用: {provider_name}")
        if req.mode not in provider.supported_modes:
            raise ValueError(f"provider={provider.name} 不支持 mode={req.mode}")

        if req.mode == "prompt_voice" and not resolved_voice_id:
            inferred_voice_id = self._infer_voice_from_prompt(provider.name, req.prompt_text or "")
            if inferred_voice_id:
                resolved_voice_id = inferred_voice_id

        if not resolved_voice_id:
            resolved_voice_id = provider.default_voice_id
        if not resolved_voice_id:
            raise ValueError("未解析到 voice_id")
        return provider, resolved_voice_id

    def _find_voice_preset(self, voice_or_preset_id: str) -> VoicePreset | None:
        for item in self.config.voice_presets:
            if item.id == voice_or_preset_id or item.voice_id == voice_or_preset_id:
                return item
        return None

    def _resolve_style_preset(self, prompt_text: str, provider_name: str | None = None) -> StylePreset | None:
        prompt_text = self._normalize_text(prompt_text)
        if not prompt_text:
            return None

        best_match: tuple[int, int, StylePreset] | None = None
        for item in self.config.style_presets:
            if provider_name and item.provider != provider_name:
                continue
            score, direct_hits = self._score_style_preset(prompt_text, item)
            if score <= 0:
                continue
            if best_match is None or (score, direct_hits) > (best_match[0], best_match[1]):
                best_match = (score, direct_hits, item)
        return best_match[2] if best_match else None

    def _provider_supports_native_prompt(self, provider: ProviderConfig) -> bool:
        if bool(provider.options.get("native_prompt_enabled", False)):
            return True
        return bool(str(provider.options.get("instruct_api_url", "")).strip())

    def _score_style_preset(self, prompt_text: str, item: StylePreset) -> tuple[int, int]:
        style_text = self._style_search_text(item)
        prompt_groups = self._extract_signal_groups(prompt_text)
        style_groups = self._extract_signal_groups(style_text)

        score = 0
        direct_hits = 0

        normalized_id = self._normalize_text(item.id)
        normalized_label = self._normalize_text(item.label)
        if normalized_id and normalized_id in prompt_text:
            score += 8
            direct_hits += 1
        if normalized_label and normalized_label in prompt_text:
            score += 10
            direct_hits += 1

        for keyword in item.prompt_keywords:
            normalized_keyword = self._normalize_text(keyword)
            if normalized_keyword and normalized_keyword in prompt_text:
                score += 6
                direct_hits += 1

        score += 3 * len(prompt_groups & style_groups)

        if "male" in prompt_groups and "female" in style_groups:
            score -= 6
        if "female" in prompt_groups and "male" in style_groups:
            score -= 6

        return score, direct_hits

    def _infer_voice_from_prompt(self, provider_name: str, prompt_text: str) -> str | None:
        prompt_groups = self._extract_signal_groups(self._normalize_text(prompt_text))
        if "male" not in prompt_groups and "female" not in prompt_groups:
            return None

        preferred_gender = "male" if "male" in prompt_groups and "female" not in prompt_groups else None
        if preferred_gender is None and "female" in prompt_groups and "male" not in prompt_groups:
            preferred_gender = "female"
        if preferred_gender is None:
            return None

        best_match: tuple[int, VoicePreset] | None = None
        for item in self.config.voice_presets:
            if item.provider != provider_name:
                continue
            voice_groups = self._extract_signal_groups(self._voice_search_text(item))
            score = 0
            if preferred_gender in voice_groups:
                score += 4
            if preferred_gender == "male" and "female" in voice_groups:
                score -= 4
            if preferred_gender == "female" and "male" in voice_groups:
                score -= 4
            if score <= 0:
                continue
            if best_match is None or score > best_match[0]:
                best_match = (score, item)
        return best_match[1].voice_id if best_match else None

    def _style_search_text(self, item: StylePreset) -> str:
        parts = [item.id, item.label, item.description, *item.prompt_keywords]
        bound_voice = self._find_voice_preset(item.voice_id)
        if bound_voice:
            parts.extend([bound_voice.label, bound_voice.voice_id, bound_voice.description])
        return self._normalize_text(" ".join(parts))

    def _voice_search_text(self, item: VoicePreset) -> str:
        return self._normalize_text(" ".join([item.id, item.label, item.voice_id, item.description]))

    def _extract_signal_groups(self, text: str) -> set[str]:
        return {group for group, terms in SIGNAL_TERMS.items() if any(term in text for term in terms)}

    def _normalize_text(self, value: str) -> str:
        normalized = re.sub(r"[\s,，。！？；：、/|()（）<>《》【】\\[\\]\"'“”‘’_-]+", " ", value.lower()).strip()
        return re.sub(r"\s+", " ", normalized)
