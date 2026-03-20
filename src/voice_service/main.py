from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import FileResponse

from .config import AppConfig, AsrGatewayConfig, AsrProviderConfig, GatewayConfig, ProviderConfig, load_app_config
from .asr.gateway import AsrGateway
from .gateway import TtsGateway
from .models import (
    AsrProviderInfo,
    AsrResponse,
    LegacyTtsRequest,
    OpenAiSpeechRequest,
    ProviderInfo,
    StandardTtsRequest,
    TtsResponse,
    VoicePresetInfo,
)


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
        asr_gateway=AsrGatewayConfig(),
        asr_providers={
            "mock_asr": AsrProviderConfig(
                name="mock_asr",
                engine="mock_asr",
                supported_modes=["file", "stream"],
            )
        },
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
ASR_GATEWAY = AsrGateway(CONFIG)
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


@app.get("/v1/asr/providers", response_model=list[AsrProviderInfo])
async def list_asr_providers() -> list[AsrProviderInfo]:
    return ASR_GATEWAY.list_providers()


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


@app.post("/v1/audio/speech")
async def openai_speech(req: OpenAiSpeechRequest) -> FileResponse:
    try:
        std = StandardTtsRequest(
            text=req.input,
            provider=req.provider,
            mode="text",
            voice_id=req.voice,
            speed=req.speed,
            format=req.response_format,
            use_cache=req.use_cache,
        )
        resp = await GATEWAY.synthesize(std)
        path = Path(resp.audio_path).resolve()
        if not path.exists():
            raise HTTPException(status_code=404, detail="audio not found")
        media_type = "audio/wav" if path.suffix == ".wav" else "audio/mpeg"
        return FileResponse(path, media_type=media_type)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _normalize_audio_format(value: str | None, filename: str | None) -> str | None:
    if value:
        return value.strip().lower()
    if filename:
        suffix = Path(filename).suffix.lower().lstrip(".")
        if suffix in {"wav", "mp3"}:
            return suffix
    return None


@app.post("/v1/asr", response_model=AsrResponse)
async def asr_file(
    audio: UploadFile = File(...),
    provider: str | None = Form(default=None),
    language: str | None = Form(default=None),
    prompt: str | None = Form(default=None),
    temperature: float | None = Form(default=None),
    format: str | None = Form(default=None),
) -> AsrResponse:
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise ValueError("audio 不能为空")
        audio_format = _normalize_audio_format(format, audio.filename)
        return await ASR_GATEWAY.transcribe(
            audio_bytes=audio_bytes,
            audio_format=audio_format,
            provider_name=provider,
            language=language,
            prompt=prompt,
            temperature=temperature,
            mode="file",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/audio/transcriptions")
async def openai_transcriptions(
    file: UploadFile = File(...),
    model: str | None = Form(default=None),
    language: str | None = Form(default=None),
    prompt: str | None = Form(default=None),
    response_format: str | None = Form(default=None),
    temperature: float | None = Form(default=None),
    provider: str | None = Form(default=None),
) -> dict[str, str]:
    del model, response_format
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise ValueError("file 不能为空")
        audio_format = _normalize_audio_format(None, file.filename)
        resp = await ASR_GATEWAY.transcribe(
            audio_bytes=audio_bytes,
            audio_format=audio_format,
            provider_name=provider,
            language=language,
            prompt=prompt,
            temperature=temperature,
            mode="file",
        )
        return {"text": resp.text}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.websocket("/v1/asr/stream")
async def asr_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    buffer = bytearray()
    last_partial_text = ""
    provider: str | None = None
    language: str | None = None
    prompt: str | None = None
    temperature: float | None = None
    audio_format: str | None = None
    partial_interval_ms = 1000
    min_chunk_bytes = 32000
    audio_bytes_per_second = 32000
    segment_seconds: float | None = None
    last_partial_size = 0
    last_partial_ts = 0.0

    while True:
        message = await websocket.receive()
        if "bytes" in message and message["bytes"] is not None:
            buffer.extend(message["bytes"])
            await websocket.send_json({"event": "ack", "bytes": len(message["bytes"])})
            if provider and ASR_GATEWAY.supports_stream(provider):
                now = time.time()
                if len(buffer) - last_partial_size >= min_chunk_bytes and now - last_partial_ts >= (partial_interval_ms / 1000.0):
                    try:
                        resp = await ASR_GATEWAY.transcribe(
                            audio_bytes=bytes(buffer),
                            audio_format=audio_format,
                            provider_name=provider,
                            language=language,
                            prompt=prompt,
                            temperature=temperature,
                            mode="stream",
                        )
                        data = resp.model_dump()
                        if data.get("text"):
                            current_text = str(data.get("text") or "")
                            if current_text.startswith(last_partial_text):
                                data["text"] = current_text[len(last_partial_text) :].lstrip()
                            last_partial_text = current_text
                        data["event"] = "partial"
                        data["is_final"] = False
                        await websocket.send_json(data)
                        last_partial_size = len(buffer)
                        last_partial_ts = now
                    except Exception as exc:
                        await websocket.send_json({"event": "error", "message": str(exc)})
            continue
        if "text" not in message or message["text"] is None:
            continue

        try:
            payload = json.loads(message["text"])
        except json.JSONDecodeError:
            await websocket.send_json({"event": "error", "message": "invalid json"})
            continue

        event = str(payload.get("event", "")).lower()
        if event == "start":
            provider = payload.get("provider")
            language = payload.get("language")
            prompt = payload.get("prompt")
            temperature = payload.get("temperature")
            audio_format = _normalize_audio_format(payload.get("format"), None)
            partial_interval_ms = int(payload.get("partial_interval_ms", partial_interval_ms))
            audio_bytes_per_second = int(payload.get("audio_bytes_per_second", audio_bytes_per_second))
            segment_seconds = payload.get("segment_seconds")
            if segment_seconds is not None:
                try:
                    segment_seconds = float(segment_seconds)
                except (TypeError, ValueError):
                    segment_seconds = None
            if segment_seconds and segment_seconds > 0:
                min_chunk_bytes = max(1, int(segment_seconds * audio_bytes_per_second))
            else:
                min_chunk_bytes = int(payload.get("min_chunk_bytes", min_chunk_bytes))
            await websocket.send_json({"event": "ready"})
            continue
        if event == "audio":
            audio_b64 = payload.get("audio_base64")
            if audio_b64:
                try:
                    chunk = base64.b64decode(audio_b64)
                except Exception:
                    await websocket.send_json({"event": "error", "message": "invalid base64"})
                    continue
                buffer.extend(chunk)
                await websocket.send_json({"event": "ack", "bytes": len(chunk)})
            continue
        if event == "end":
            try:
                resp = await ASR_GATEWAY.transcribe(
                    audio_bytes=bytes(buffer),
                    audio_format=audio_format,
                    provider_name=provider,
                    language=language,
                    prompt=prompt,
                    temperature=temperature,
                    mode="file",
                )
                data = resp.model_dump()
                data["event"] = "final"
                if last_partial_text and data.get("text"):
                    current_text = str(data.get("text") or "")
                    if current_text.startswith(last_partial_text):
                        data["text"] = current_text[len(last_partial_text) :].lstrip()
                await websocket.send_json(data)
            except Exception as exc:
                await websocket.send_json({"event": "error", "message": str(exc)})
            await websocket.close()
            return


@app.get("/audio/{file_name}")
async def get_audio(file_name: str) -> FileResponse:
    path = (OUTPUT_DIR / file_name).resolve()
    if not path.exists() or path.parent != OUTPUT_DIR:
        raise HTTPException(status_code=404, detail="audio not found")
    media_type = "audio/wav" if path.suffix == ".wav" else "audio/mpeg"
    return FileResponse(path, media_type=media_type)
