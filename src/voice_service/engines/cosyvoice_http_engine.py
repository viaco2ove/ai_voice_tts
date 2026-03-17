from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .base import TtsEngine


class CosyVoiceHttpEngine(TtsEngine):
    """Call a local/remote CosyVoice-compatible HTTP endpoint."""

    @property
    def name(self) -> str:
        return "cosyvoice_http"

    async def synthesize(
        self,
        *,
        text: str,
        voice_id: str,
        speed: float,
        output_path: Path,
        audio_format: str,
        mode: str = "text",
        reference_audio_base64: str | None = None,
        reference_text: str | None = None,
        prompt_text: str | None = None,
        mix_voices: list[dict[str, object]] | None = None,
    ) -> None:
        api_url = self._resolve_api_url(mode)
        timeout = float(self.options.get("timeout_seconds", os.getenv("COSYVOICE_TIMEOUT_SECONDS", "90")))
        protocol = self._resolve_protocol(api_url)

        payload: dict[str, object] = {
            "text": text,
            "voice_id": voice_id,
            "speed": speed,
            "format": audio_format,
            "reference_audio_base64": reference_audio_base64,
            "reference_text": reference_text,
            "prompt_text": prompt_text,
            "mix_voices": mix_voices or [],
        }
        if protocol == "form":
            payload = self._build_form_payload(
                text=text,
                voice_id=voice_id,
                speed=speed,
                mode=mode,
                reference_audio_base64=reference_audio_base64,
                reference_text=reference_text,
            )
        elif protocol == "openai_json":
            payload = {
                "model": "tts-1",
                "input": text,
                "voice": self._map_voice_id(voice_id),
                "speed": speed,
                "response_format": "wav",
            }

        body = await asyncio.to_thread(self._request, api_url, payload, timeout, protocol)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(body)

    def _resolve_api_url(self, mode: str) -> str:
        env_default = os.getenv("COSYVOICE_API_URL", "http://127.0.0.1:9233/tts")
        base_url = str(self.options.get("api_url", env_default))
        clone_api = self.options.get("clone_api_url")
        if mode == "clone" and clone_api:
            return str(clone_api)
        if mode == "clone" and base_url.endswith("/tts"):
            return f"{base_url[:-4]}/clone"
        return base_url

    def _request(
        self,
        api_url: str,
        payload: dict[str, object],
        timeout: float,
        protocol: str,
    ) -> bytes:
        if protocol == "form":
            data = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request(
                api_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
        else:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                api_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"CosyVoice HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            if self._should_try_windows_bridge(api_url):
                return self._request_via_windows_curl(api_url, payload, timeout, protocol)
            raise RuntimeError(f"CosyVoice request failed: {exc.reason}") from exc

        if "application/json" in content_type.lower():
            result = json.loads(raw.decode("utf-8"))
            if "audio_base64" in result:
                return base64.b64decode(result["audio_base64"])
            if "msg" in result:
                raise RuntimeError(f"CosyVoice response error: {result['msg']}")
            raise RuntimeError("CosyVoice JSON response missing 'audio_base64'")

        return raw

    def _should_try_windows_bridge(self, api_url: str) -> bool:
        if "microsoft" not in os.uname().release.lower():
            return False
        parsed = urlparse(api_url)
        return parsed.hostname in {"127.0.0.1", "localhost"}

    def _request_via_windows_curl(
        self,
        api_url: str,
        payload: dict[str, object],
        timeout: float,
        protocol: str,
    ) -> bytes:
        curl_exe = "/mnt/c/Windows/System32/curl.exe"
        if not Path(curl_exe).exists():
            raise RuntimeError("CosyVoice request failed: Windows curl.exe not found")

        cmd = [curl_exe, "-sS", "--fail", "--max-time", str(int(timeout)), "-X", "POST", api_url]
        if protocol == "form":
            cmd.extend(["-H", "Content-Type: application/x-www-form-urlencoded", "--data", urllib.parse.urlencode(payload)])
        else:
            cmd.extend(["-H", "Content-Type: application/json", "--data", json.dumps(payload, ensure_ascii=False)])

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"CosyVoice Windows bridge failed: {detail}")
        return result.stdout

    def _resolve_protocol(self, api_url: str) -> str:
        mode = str(self.options.get("request_mode", os.getenv("COSYVOICE_REQUEST_MODE", "auto"))).strip().lower()
        if mode in {"json", "form", "openai_json"}:
            return mode

        if api_url.endswith("/v1/audio/speech"):
            return "openai_json"
        if api_url.endswith("/tts") or api_url.endswith("/clone") or api_url.endswith("/clone_eq"):
            return "form"
        return "json"

    def _build_form_payload(
        self,
        *,
        text: str,
        voice_id: str,
        speed: float,
        mode: str,
        reference_audio_base64: str | None,
        reference_text: str | None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {"text": text, "speed": speed}
        if mode == "clone":
            if not reference_audio_base64:
                raise ValueError("clone 模式必须提供 reference_audio_base64")
            payload["reference_audio"] = reference_audio_base64
            payload["encode"] = "base64"
            if reference_text:
                payload["prompt_text"] = reference_text
            return payload
        payload["role"] = self._map_voice_id(voice_id)
        return payload

    def _map_voice_id(self, voice_id: str) -> str:
        custom = self.options.get("voice_mapping", {})
        if isinstance(custom, dict) and voice_id in custom:
            return str(custom[voice_id])

        mapping = {
            "default_female": "中文女",
            "default_male": "中文男",
            "cn_female": "中文女",
            "cn_male": "中文男",
            "jp_male": "日语男",
            "en_female": "英文女",
            "en_male": "英文男",
            "yue_female": "粤语女",
            "kr_female": "韩语女",
        }
        return mapping.get(voice_id.strip().lower(), voice_id or "中文女")
