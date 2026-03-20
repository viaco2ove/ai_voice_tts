from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import time
from pathlib import Path

import uvicorn

from .config import AppConfig, AsrProviderConfig, ProviderConfig, load_app_config


class VoiceServiceLauncher:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.children: list[subprocess.Popen[str]] = []

    def run(self) -> None:
        self._register_signals()
        self._start_upstreams()
        os.environ["VOICE_CONFIG_PATH"] = str(self.config.path)
        uvicorn.run(
            "src.voice_service.main:app",
            host=self.config.gateway.host,
            port=self.config.gateway.port,
            reload=False,
        )

    def _start_upstreams(self) -> None:
        for provider in self.config.providers.values():
            if not provider.enabled or not provider.startup.enabled or not provider.startup.command.strip():
                continue

            if self._is_provider_ready(provider) or self._has_matching_process(provider.startup.command):
                continue

            child = subprocess.Popen(
                provider.startup.command,
                cwd=provider.startup.cwd or None,
                env={**os.environ, **provider.startup.env},
                shell=True,
                text=True,
            )
            self.children.append(child)
            self._wait_until_ready(provider, child)

        for provider in self.config.asr_providers.values():
            if not provider.enabled or not provider.startup.enabled or not provider.startup.command.strip():
                continue

            if self._is_provider_ready(provider) or self._has_matching_process(provider.startup.command):
                continue

            child = subprocess.Popen(
                provider.startup.command,
                cwd=provider.startup.cwd or None,
                env={**os.environ, **provider.startup.env},
                shell=True,
                text=True,
            )
            self.children.append(child)
            self._wait_until_ready(provider, child)

    def _wait_until_ready(self, provider: ProviderConfig | AsrProviderConfig, child: subprocess.Popen[str]) -> None:
        strategy = provider.startup.wait_strategy.lower()
        if strategy == "none":
            return
        if strategy == "sleep":
            time.sleep(provider.startup.wait_seconds)
            if child.poll() is not None and child.returncode not in (0, None):
                raise RuntimeError(f"{provider.name} 启动后立即退出，exit={child.returncode}")
            return
        if strategy == "tcp" and provider.startup.tcp_port:
            deadline = time.time() + provider.startup.startup_timeout_seconds
            while time.time() < deadline:
                if self._is_tcp_open(provider.startup.tcp_host, int(provider.startup.tcp_port)):
                    return
                if child.poll() is not None and child.returncode not in (0, None):
                    raise RuntimeError(f"{provider.name} 启动失败，exit={child.returncode}")
                time.sleep(1.0)
            raise RuntimeError(f"{provider.name} 启动超时，端口未就绪: {provider.startup.tcp_host}:{provider.startup.tcp_port}")

    def _is_provider_ready(self, provider: ProviderConfig | AsrProviderConfig) -> bool:
        strategy = provider.startup.wait_strategy.lower()
        if strategy == "tcp" and provider.startup.tcp_port:
            return self._is_tcp_open(provider.startup.tcp_host, int(provider.startup.tcp_port))
        return False

    @staticmethod
    def _is_tcp_open(host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            return sock.connect_ex((host, port)) == 0

    @staticmethod
    def _has_matching_process(command: str) -> bool:
        marker = command.strip()
        if not marker:
            return False
        current_pid = os.getpid()
        result = subprocess.run(
            ["ps", "-eo", "pid=,args="],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False
        for line in result.stdout.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) != 2:
                continue
            try:
                pid = int(parts[0])
            except ValueError:
                continue
            if pid == current_pid:
                continue
            args = parts[1]
            if marker in args:
                return True
        return False

    def _register_signals(self) -> None:
        def _handle_signal(signum: int, _frame: object) -> None:
            self._shutdown_children()
            raise SystemExit(128 + signum)

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

    def _shutdown_children(self) -> None:
        for child in self.children:
            if child.poll() is None:
                child.terminate()
        for child in self.children:
            if child.poll() is None:
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description="One-click launcher for voice gateway and upstream services")
    parser.add_argument("--config", default="config/services.yaml", help="YAML config path")
    args = parser.parse_args()

    config = load_app_config(Path(args.config))
    launcher = VoiceServiceLauncher(config)
    launcher.run()


if __name__ == "__main__":
    main()
