from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class GatewayConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    output_dir: str = "output_audio"
    default_provider: str = "mock_local"


@dataclass
class StartupConfig:
    enabled: bool = False
    command: str = ""
    cwd: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    wait_strategy: str = "none"
    wait_seconds: float = 0.0
    tcp_host: str = "127.0.0.1"
    tcp_port: int | None = None
    startup_timeout_seconds: float = 180.0


@dataclass
class ProviderConfig:
    name: str
    engine: str
    enabled: bool = True
    default_voice_id: str = "default_female"
    default_format: str = "wav"
    supported_modes: list[str] = field(default_factory=lambda: ["text"])
    options: dict[str, Any] = field(default_factory=dict)
    startup: StartupConfig = field(default_factory=StartupConfig)


@dataclass
class VoicePreset:
    id: str
    label: str
    provider: str
    voice_id: str
    modes: list[str] = field(default_factory=lambda: ["text"])
    description: str = ""


@dataclass
class StylePreset:
    id: str
    label: str
    provider: str
    voice_id: str
    prompt_keywords: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class AppConfig:
    path: Path
    gateway: GatewayConfig
    providers: dict[str, ProviderConfig]
    voice_presets: list[VoicePreset]
    style_presets: list[StylePreset]


def _expand_env_values(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [_expand_env_values(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env_values(val) for key, val in value.items()}
    return value


def load_app_config(path: str | Path) -> AppConfig:
    config_path = Path(path).expanduser().resolve()
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    data = _expand_env_values(data)

    gateway_data = data.get("gateway", {})
    gateway = GatewayConfig(
        host=str(gateway_data.get("host", "0.0.0.0")),
        port=int(gateway_data.get("port", 8000)),
        output_dir=str(gateway_data.get("output_dir", "output_audio")),
        default_provider=str(gateway_data.get("default_provider", "mock_local")),
    )

    providers: dict[str, ProviderConfig] = {}
    for name, raw in (data.get("providers", {}) or {}).items():
        startup_raw = raw.get("startup", {}) or {}
        providers[name] = ProviderConfig(
            name=name,
            engine=str(raw["engine"]),
            enabled=bool(raw.get("enabled", True)),
            default_voice_id=str(raw.get("default_voice_id", "default_female")),
            default_format=str(raw.get("default_format", "wav")),
            supported_modes=list(raw.get("supported_modes", ["text"])),
            options=dict(raw.get("options", {})),
            startup=StartupConfig(
                enabled=bool(startup_raw.get("enabled", False)),
                command=str(startup_raw.get("command", "")),
                cwd=startup_raw.get("cwd"),
                env=dict(startup_raw.get("env", {})),
                wait_strategy=str(startup_raw.get("wait_strategy", "none")),
                wait_seconds=float(startup_raw.get("wait_seconds", 0)),
                tcp_host=str(startup_raw.get("tcp_host", "127.0.0.1")),
                tcp_port=startup_raw.get("tcp_port"),
                startup_timeout_seconds=float(startup_raw.get("startup_timeout_seconds", 180)),
            ),
        )

    voice_presets = [
        VoicePreset(
            id=str(item["id"]),
            label=str(item.get("label", item["id"])),
            provider=str(item["provider"]),
            voice_id=str(item["voice_id"]),
            modes=list(item.get("modes", ["text"])),
            description=str(item.get("description", "")),
        )
        for item in (data.get("voice_presets", []) or [])
    ]

    style_presets = [
        StylePreset(
            id=str(item["id"]),
            label=str(item.get("label", item["id"])),
            provider=str(item["provider"]),
            voice_id=str(item["voice_id"]),
            prompt_keywords=list(item.get("prompt_keywords", [])),
            description=str(item.get("description", "")),
        )
        for item in (data.get("style_presets", []) or [])
    ]

    return AppConfig(
        path=config_path,
        gateway=gateway,
        providers=providers,
        voice_presets=voice_presets,
        style_presets=style_presets,
    )

