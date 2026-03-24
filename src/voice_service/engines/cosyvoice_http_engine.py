from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .base import TtsEngine


class CosyVoiceHttpEngine(TtsEngine):
    """Call a local/remote CosyVoice-compatible HTTP endpoint."""

    INSTRUCT_TERM_MAP: tuple[tuple[str, str], ...] = (
        ("青年男性", "young adult male"),
        ("青年男", "young male"),
        ("男性", "male"),
        ("男声", "male voice"),
        ("男生", "young male"),
        ("青年女性", "young adult female"),
        ("青年女", "young female"),
        ("女性", "female"),
        ("女声", "female voice"),
        ("女生", "young female"),
        ("神话英雄", "mythic hero"),
        ("英雄", "heroic"),
        ("朝气", "energetic"),
        ("元气", "energetic"),
        ("自信", "confident"),
        ("有力", "powerful"),
        ("张扬", "flamboyant"),
        ("干练", "crisp and capable"),
        ("坚定", "determined"),
        ("沉稳", "steady"),
        ("稳重", "steady"),
        ("成熟", "mature"),
        ("磁性", "magnetic"),
        ("低沉", "deep"),
        ("温柔", "gentle"),
        ("治愈", "soothing"),
        ("温暖", "warm"),
        ("细腻", "delicate"),
        ("抒情", "lyrical"),
        ("故事", "storytelling"),
        ("讲述", "storytelling"),
        ("叙述", "narrative"),
        ("旁白", "narrative"),
        ("纪录片", "documentary narrator"),
        ("说明", "explanatory"),
        ("口播", "voice-over"),
        ("播报", "broadcast"),
        ("直播", "live host"),
        ("主持", "host-like"),
        ("活泼", "playful"),
        ("明快", "lively"),
        ("明亮", "bright"),
        ("爽朗", "cheerful"),
        ("洪亮", "resonant"),
        ("语速偏快", "fast-paced"),
        ("语速快", "fast-paced"),
        ("偏快", "fast-paced"),
    )

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
                prompt_text=prompt_text,
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
        instruct_api = self.options.get("instruct_api_url")
        if mode == "clone" and clone_api:
            return str(clone_api)
        if mode == "clone" and base_url.endswith("/tts"):
            return f"{base_url[:-4]}/clone"
        if mode == "prompt_voice" and instruct_api:
            return str(instruct_api)
        if mode == "prompt_voice" and base_url.endswith("/tts"):
            return f"{base_url[:-4]}/instruct"
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
        if api_url.endswith("/tts") or api_url.endswith("/clone") or api_url.endswith("/clone_eq") or api_url.endswith("/instruct"):
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
        prompt_text: str | None,
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
        if mode == "prompt_voice":
            payload["role"] = self._map_voice_id(voice_id)
            payload["prompt_text"] = self._compile_instruct_prompt(prompt_text or "", voice_id)
            return payload
        payload["role"] = self._map_voice_id(voice_id)
        return payload

    def _compile_instruct_prompt(self, prompt_text: str, voice_id: str) -> str:
        prompt_text = (prompt_text or "").strip()
        if not prompt_text:
            return ""

        # CosyVoice-300M-Instruct 对中文关键词串容易直接复读。这里改写成更接近
        # 官方示例的英文 persona 描述，降低把提示词本身读出来的概率。
        if not self._contains_cjk(prompt_text):
            return prompt_text

        traits: list[str] = []
        normalized = re.sub(r"\s+", "", prompt_text)
        for source, target in self.INSTRUCT_TERM_MAP:
            if source in normalized and target not in traits:
                traits.append(target)
        traits = self._dedupe_overlapping_traits(traits)

        fallback_role = self._english_role_hint(voice_id)
        if fallback_role and fallback_role not in traits and not self._traits_imply_gender(traits, fallback_role):
            traits.insert(0, fallback_role)

        if not traits:
            return f"{fallback_role}, natural, expressive." if fallback_role else "natural, expressive."

        return f"{', '.join(traits)}."

    def _contains_cjk(self, value: str) -> bool:
        return any("\u4e00" <= ch <= "\u9fff" for ch in value)

    def _english_role_hint(self, voice_id: str) -> str:
        normalized = voice_id.strip().lower()
        if "male" in normalized or normalized.endswith("男"):
            return "male voice"
        if "female" in normalized or normalized.endswith("女"):
            return "female voice"
        return ""

    def _traits_imply_gender(self, traits: list[str], fallback_role: str) -> bool:
        if fallback_role == "male voice":
            return any("male" in item for item in traits)
        if fallback_role == "female voice":
            return any("female" in item for item in traits)
        return False

    def _dedupe_overlapping_traits(self, traits: list[str]) -> list[str]:
        deduped = list(traits)
        if "young adult male" in deduped:
            deduped = [item for item in deduped if item not in {"young male", "male", "male voice"}]
            deduped.insert(0, "young adult male")
        elif "young male" in deduped:
            deduped = [item for item in deduped if item not in {"male", "male voice"}]
            deduped.insert(0, "young male")
        elif "male" in deduped and "male voice" in deduped:
            deduped = [item for item in deduped if item != "male voice"]

        if "young adult female" in deduped:
            deduped = [item for item in deduped if item not in {"young female", "female", "female voice"}]
            deduped.insert(0, "young adult female")
        elif "young female" in deduped:
            deduped = [item for item in deduped if item not in {"female", "female voice"}]
            deduped.insert(0, "young female")
        elif "female" in deduped and "female voice" in deduped:
            deduped = [item for item in deduped if item != "female voice"]
        return list(dict.fromkeys(deduped))

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
