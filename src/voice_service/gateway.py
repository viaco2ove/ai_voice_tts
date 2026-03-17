from __future__ import annotations

import hashlib
from pathlib import Path

from .config import AppConfig, ProviderConfig, StylePreset, VoicePreset
from .engine_factory import build_engine
from .models import ProviderInfo, StandardTtsRequest, TtsResponse, VoicePresetInfo


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
        resolved_format = req.format or provider.default_format
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
            style = self._resolve_style_preset(req.prompt_text or "")
            if not style:
                raise ValueError("未找到可匹配的提示词音色，请在配置文件中补充 style_presets")
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

        if not resolved_voice_id:
            resolved_voice_id = provider.default_voice_id
        if not resolved_voice_id:
            raise ValueError("未解析到 voice_id")
        return provider, resolved_voice_id

    def _find_voice_preset(self, voice_or_preset_id: str) -> VoicePreset | None:
        for item in self.config.voice_presets:
            if item.id == voice_or_preset_id:
                return item
        return None

    def _resolve_style_preset(self, prompt_text: str) -> StylePreset | None:
        prompt_text = prompt_text.strip().lower()
        if not prompt_text:
            return None

        best_match: tuple[int, StylePreset] | None = None
        for item in self.config.style_presets:
            score = sum(1 for keyword in item.prompt_keywords if keyword.strip().lower() in prompt_text)
            if score <= 0:
                continue
            if best_match is None or score > best_match[0]:
                best_match = (score, item)
        return best_match[1] if best_match else None
