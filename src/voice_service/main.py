from __future__ import annotations

import base64
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from .config import AppConfig, GatewayConfig, ProviderConfig, load_app_config
from .gateway import TtsGateway
from .models import LegacyTtsRequest, ProviderInfo, StandardTtsRequest, TtsResponse, VoicePresetInfo


DEFAULT_CONFIG_PATH = Path(os.getenv("VOICE_CONFIG_PATH", "config/services.yaml")).expanduser()


def _build_fallback_config() -> AppConfig:
    engine = os.getenv("TTS_ENGINE", "mock")
    output_dir = os.getenv("TTS_OUTPUT_DIR", "output_audio")
    default_voice = os.getenv("TTS_DEFAULT_VOICE_ID", "default_female")
    default_format = os.getenv("TTS_DEFAULT_FORMAT", "wav")
    supported_modes = ["text"]
    if engine == "cosyvoice_http":
        supported_modes = ["text", "clone", "mix", "prompt_voice"]
    elif engine == "edge_tts":
        supported_modes = ["text", "mix", "prompt_voice"]

    return AppConfig(
        path=DEFAULT_CONFIG_PATH.resolve(),
        gateway=GatewayConfig(output_dir=output_dir, default_provider="default"),
        providers={
            "default": ProviderConfig(
                name="default",
                engine=engine,
                default_voice_id=default_voice,
                default_format=default_format,
                supported_modes=supported_modes,
            )
        },
        voice_presets=[],
        style_presets=[],
    )


def load_runtime_config() -> AppConfig:
    if DEFAULT_CONFIG_PATH.exists():
        return load_app_config(DEFAULT_CONFIG_PATH)
    return _build_fallback_config()


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _attach_audio_url(resp: TtsResponse, request: Request) -> TtsResponse:
    try:
        resp.audio_url_full = str(request.base_url).rstrip("/") + resp.audio_url
    except Exception:
        resp.audio_url_full = None
    return resp


CONFIG = load_runtime_config()
GATEWAY = TtsGateway(CONFIG)
OUTPUT_DIR = GATEWAY.output_dir

app = FastAPI(title="Voice Gateway", version="0.3.1")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return GATEWAY.health()


@app.get("/providers", response_model=list[ProviderInfo])
async def list_providers() -> list[ProviderInfo]:
    return GATEWAY.list_providers()


@app.get("/voices", response_model=list[VoicePresetInfo])
async def list_voices() -> list[VoicePresetInfo]:
    return GATEWAY.list_voice_presets()


@app.post("/v1/tts", response_model=TtsResponse)
async def synthesize_v1(req: StandardTtsRequest, request: Request) -> TtsResponse:
    try:
        resp = await GATEWAY.synthesize(req)
        return _attach_audio_url(resp, request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/tts/clone_upload", response_model=TtsResponse)
async def synthesize_clone_upload(
    request: Request,
    text: str = Form(...),
    reference_audio: UploadFile = File(...),
    provider: str | None = Form(default=None),
    format: str | None = Form(default=None),
    reference_text: str | None = Form(default=None),
    speed: float = Form(default=1.0),
    use_cache: str = Form(default="true"),
) -> TtsResponse:
    try:
        audio_bytes = await reference_audio.read()
        if not audio_bytes:
            raise ValueError("reference_audio 不能为空")
        req = StandardTtsRequest(
            text=text,
            provider=provider,
            mode="clone",
            speed=speed,
            format=format,
            use_cache=_to_bool(use_cache),
            reference_audio_base64=base64.b64encode(audio_bytes).decode("utf-8"),
            reference_text=reference_text,
        )
        resp = await GATEWAY.synthesize(req)
        return _attach_audio_url(resp, request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/tts", response_model=TtsResponse)
async def synthesize_legacy(req: LegacyTtsRequest, request: Request) -> TtsResponse:
    try:
        resp = await GATEWAY.synthesize(req.to_standard())
        return _attach_audio_url(resp, request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/audio/{file_name}")
async def get_audio(file_name: str) -> FileResponse:
    path = (OUTPUT_DIR / file_name).resolve()
    if not path.exists() or path.parent != OUTPUT_DIR:
        raise HTTPException(status_code=404, detail="audio not found")
    media_type = "audio/wav" if path.suffix == ".wav" else "audio/mpeg"
    return FileResponse(path, media_type=media_type)
