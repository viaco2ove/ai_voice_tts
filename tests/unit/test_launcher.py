from __future__ import annotations

import subprocess
from pathlib import Path

from src.voice_service.config import AppConfig, AsrGatewayConfig, GatewayConfig
from src.voice_service.launcher import VoiceServiceLauncher


class DummyProcess:
    def __init__(self) -> None:
        self.returncode = None

    def poll(self) -> None:
        return None

    def terminate(self) -> None:
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        self.returncode = 0
        return 0


def test_spawn_child_process_redirects_to_log_file(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(
        path=tmp_path / "config" / "services.yaml",
        gateway=GatewayConfig(),
        providers={},
        voice_presets=[],
        style_presets=[],
        asr_gateway=AsrGatewayConfig(),
        asr_providers={},
    )
    launcher = VoiceServiceLauncher(config)
    captured: dict[str, object] = {}

    def fake_popen(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return DummyProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    child = launcher._spawn_child_process(
        name="cosyvoice local",
        command="python api.py",
        cwd=str(tmp_path),
        extra_env={"TEST_ENV": "1"},
    )

    assert isinstance(child, DummyProcess)
    kwargs = captured["kwargs"]
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["stderr"] is subprocess.STDOUT
    assert kwargs["shell"] is True
    assert kwargs["text"] is True
    assert kwargs["env"]["TEST_ENV"] == "1"
    assert Path(kwargs["stdout"].name) == tmp_path / "logs" / "cosyvoice_local.log"
