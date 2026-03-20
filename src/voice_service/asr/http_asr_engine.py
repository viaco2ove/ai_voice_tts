from __future__ import annotations

import asyncio
import base64
import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Any

from .base import AsrEngine, AsrResult


class HttpAsrEngine(AsrEngine):
    @property
    def name(self) -> str:
        return "asr_http"

    @property
    def supports_stream(self) -> bool:
        return bool(self.options.get("supports_stream", False))

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        audio_format: str | None,
        language: str | None,
        prompt: str | None,
        temperature: float | None,
        mode: str = "file",
    ) -> AsrResult:
        api_url = str(self.options.get("api_url", os.getenv("ASR_API_URL", "http://127.0.0.1:9000/asr")))
        timeout = float(self.options.get("timeout_seconds", os.getenv("ASR_TIMEOUT_SECONDS", "90")))
        request_mode = str(self.options.get("request_mode", os.getenv("ASR_REQUEST_MODE", "json"))).strip().lower()
        model = str(self.options.get("model", os.getenv("ASR_MODEL", "whisper-1")))

        if request_mode == "openai":
            body, content_type = _build_multipart_openai(
                audio_bytes=audio_bytes,
                audio_format=audio_format or "wav",
                model=model,
                language=language,
                prompt=prompt,
                temperature=temperature,
            )
        else:
            payload: dict[str, Any] = {
                "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
                "audio_format": audio_format or "wav",
                "language": language,
                "prompt": prompt,
                "temperature": temperature,
                "mode": mode,
            }
            body = json.dumps(payload).encode("utf-8")
            content_type = "application/json"

        request = urllib.request.Request(
            api_url,
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        raw = await asyncio.to_thread(_read_response, request, timeout)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("ASR HTTP response is not JSON") from exc

        text = str(data.get("text", ""))
        language = data.get("language")
        segments = data.get("segments") or []
        is_final = bool(data.get("is_final", mode != "stream"))
        return AsrResult(text=text, language=language, segments=segments, is_final=is_final)


def _read_response(request: urllib.request.Request, timeout: float) -> bytes:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ASR HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ASR request failed: {exc.reason}") from exc


def _build_multipart_openai(
    *,
    audio_bytes: bytes,
    audio_format: str,
    model: str,
    language: str | None,
    prompt: str | None,
    temperature: float | None,
) -> tuple[bytes, str]:
    boundary = f"----asrboundary{uuid.uuid4().hex}"
    parts: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.append(
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"{name}\"\r\n\r\n"
            f"{value}\r\n".encode("utf-8")
        )

    def add_file(name: str, filename: str, content_type: str, data: bytes) -> None:
        header = (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
        parts.append(header)
        parts.append(data)
        parts.append(b"\r\n")

    add_field("model", model)
    if language:
        add_field("language", language)
    if prompt:
        add_field("prompt", prompt)
    if temperature is not None:
        add_field("temperature", str(temperature))

    filename = f"audio.{audio_format}"
    content_type = "audio/wav" if audio_format == "wav" else "audio/mpeg"
    add_file("file", filename, content_type, audio_bytes)

    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)
    return body, f"multipart/form-data; boundary={boundary}"
