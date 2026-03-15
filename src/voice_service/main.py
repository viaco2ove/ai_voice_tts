from __future__ import annotations

import hashlib
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .engine_factory import build_engine


OUTPUT_DIR = Path(os.getenv("TTS_OUTPUT_DIR", "output_audio")).resolve()
ENGINE = build_engine()


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    voice_id: str = Field(default="default_female")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    format: str = Field(default="wav", pattern="^(wav|mp3)$")
    reference_audio_base64: str | None = None
    use_cache: bool = True


class TtsResponse(BaseModel):
    engine: str
    cache_hit: bool
    file_name: str
    audio_path: str


def _cache_key(req: TtsRequest) -> str:
    ref_hash = ""
    if req.reference_audio_base64:
        ref_hash = hashlib.sha256(req.reference_audio_base64.encode("utf-8")).hexdigest()[:12]

    normalized = "|".join(
        [
            req.text.strip(),
            req.voice_id.strip(),
            f"{req.speed:.2f}",
            req.format,
            ENGINE.name,
            ref_hash,
        ]
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


app = FastAPI(title="Local TTS Service", version="0.1.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "engine": ENGINE.name}


@app.post("/tts", response_model=TtsResponse)
async def tts(req: TtsRequest) -> TtsResponse:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    file_name = f"{_cache_key(req)}.{req.format}"
    output_path = OUTPUT_DIR / file_name

    if req.use_cache and output_path.exists():
        return TtsResponse(
            engine=ENGINE.name,
            cache_hit=True,
            file_name=file_name,
            audio_path=str(output_path),
        )

    try:
        await ENGINE.synthesize(
            text=req.text,
            voice_id=req.voice_id,
            speed=req.speed,
            output_path=output_path,
            audio_format=req.format,
            reference_audio_base64=req.reference_audio_base64,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TtsResponse(
        engine=ENGINE.name,
        cache_hit=False,
        file_name=file_name,
        audio_path=str(output_path),
    )


@app.get("/audio/{file_name}")
async def get_audio(file_name: str) -> FileResponse:
    path = (OUTPUT_DIR / file_name).resolve()
    if not path.exists() or path.parent != OUTPUT_DIR:
        raise HTTPException(status_code=404, detail="audio not found")
    media_type = "audio/wav" if path.suffix == ".wav" else "audio/mpeg"
    return FileResponse(path, media_type=media_type)
