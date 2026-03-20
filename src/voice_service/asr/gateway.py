from __future__ import annotations

from .base import AsrResult
from .factory import build_asr_engine
from ..config import AppConfig, AsrProviderConfig
from ..models import AsrProviderInfo, AsrResponse


class AsrGateway:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.providers = {name: provider for name, provider in config.asr_providers.items() if provider.enabled}
        self.engines = {
            name: build_asr_engine(provider.engine, provider.options)
            for name, provider in self.providers.items()
        }

    def list_providers(self) -> list[AsrProviderInfo]:
        return [
            AsrProviderInfo(
                provider=provider.name,
                engine=provider.engine,
                enabled=provider.enabled,
                supported_modes=list(provider.supported_modes),
            )
            for provider in self.providers.values()
        ]

    def supports_stream(self, provider_name: str | None) -> bool:
        provider = self._resolve_provider(provider_name)
        engine = self.engines[provider.name]
        return bool(engine.supports_stream)

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        audio_format: str | None,
        provider_name: str | None,
        language: str | None,
        prompt: str | None,
        temperature: float | None,
        mode: str = "file",
    ) -> AsrResponse:
        provider = self._resolve_provider(provider_name)
        engine = self.engines[provider.name]
        result = await engine.transcribe(
            audio_bytes=audio_bytes,
            audio_format=audio_format,
            language=language,
            prompt=prompt,
            temperature=temperature,
            mode=mode,
        )
        return _to_response(provider, engine.name, result)

    def _resolve_provider(self, provider_name: str | None) -> AsrProviderConfig:
        resolved = provider_name or self.config.asr_gateway.default_provider
        provider = self.providers.get(resolved)
        if not provider:
            raise ValueError(f"asr provider 不存在或未启用: {resolved}")
        return provider


def _to_response(provider: AsrProviderConfig, engine_name: str, result: AsrResult) -> AsrResponse:
    return AsrResponse(
        provider=provider.name,
        engine=engine_name,
        text=result.text,
        language=result.language,
        segments=result.segments,
        is_final=result.is_final,
    )
