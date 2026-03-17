from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


VoiceMode = Literal["text", "clone", "mix", "prompt_voice"]
AudioFormat = Literal["wav", "mp3"]


class MixVoiceItem(BaseModel):
    voice_id: str = Field(min_length=1, max_length=128)
    weight: float = Field(default=1.0, gt=0)


class StandardTtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    provider: str | None = None
    mode: VoiceMode = "text"
    voice_id: str | None = None
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    format: AudioFormat | None = None
    use_cache: bool = True
    reference_audio_base64: str | None = None
    reference_text: str | None = None
    prompt_text: str | None = None
    mix_voices: list[MixVoiceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "StandardTtsRequest":
        if self.mode == "clone" and not self.reference_audio_base64:
            raise ValueError("clone 模式必须提供 reference_audio_base64")
        if self.mode == "mix" and len(self.mix_voices) < 2:
            raise ValueError("mix 模式至少需要 2 个音色")
        if self.mode == "prompt_voice" and not (self.prompt_text and self.prompt_text.strip()):
            raise ValueError("prompt_voice 模式必须提供 prompt_text")
        return self


class LegacyTtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    voice_id: str = Field(default="default_female")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    format: AudioFormat = "wav"
    reference_audio_base64: str | None = None
    reference_text: str | None = None
    use_cache: bool = True

    def to_standard(self) -> StandardTtsRequest:
        mode: VoiceMode = "clone" if self.reference_audio_base64 else "text"
        return StandardTtsRequest(
            text=self.text,
            mode=mode,
            voice_id=self.voice_id,
            speed=self.speed,
            format=self.format,
            reference_audio_base64=self.reference_audio_base64,
            reference_text=self.reference_text,
            use_cache=self.use_cache,
        )


class TtsResponse(BaseModel):
    provider: str
    engine: str
    mode: VoiceMode
    resolved_voice_id: str
    cache_hit: bool
    file_name: str
    audio_path: str
    audio_url: str
    audio_url_full: str | None = None


class ProviderInfo(BaseModel):
    provider: str
    engine: str
    enabled: bool
    default_voice_id: str
    default_format: AudioFormat
    supported_modes: list[VoiceMode]


class VoicePresetInfo(BaseModel):
    id: str
    label: str
    provider: str
    voice_id: str
    modes: list[VoiceMode]
    description: str = ""
