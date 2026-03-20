# Voice Gateway 启动说明

## 目标

通过一个 YAML 配置文件管理网关端口、provider、音色预设和上游服务启动方式，不再手敲长命令。

## 配置文件

默认配置文件：`config/services.yaml`

可配置内容：

- `gateway`: 网关监听地址、端口、输出目录、默认 provider
- `providers`: 各语音服务的引擎类型、默认音色、支持模式、上游启动方式
- `voice_presets`: 对外暴露的音色预设
- `style_presets`: 提示词到音色的映射规则
- `asr_gateway`: 语音识别默认 provider
- `asr_providers`: 语音识别引擎配置

本地 ASR 可选引擎：

- `local_whisper`（基于 `faster-whisper`，需要额外安装依赖与模型下载）

## 一键启动

```bash
cd /mnt/d/Users/viaco/tools/voice
./scripts/start_all.sh
```

指定配置文件：

```bash
./scripts/start_all.sh config/services.yaml
```

## 启动策略

`providers.<name>.startup` 支持三种等待方式：

- `none`: 不等待，适合纯云接口
- `sleep`: 启动后固定等待若干秒
- `tcp`: 轮询端口，直到上游服务可连通

当前 `cosyvoice_local` 的默认配置如下：

```yaml
startup:
  enabled: true
  command: /mnt/d/Users/viaco/PycharmProjects/CosyVoice/.venv/Scripts/python.exe api.py
  cwd: /mnt/d/Users/viaco/PycharmProjects/CosyVoice
  wait_strategy: sleep
  wait_seconds: 15
```

由于 CosyVoice 跑在 Windows 侧，WSL 下不再用 `tcp` 探测，而是改为 `sleep` 等待 15 秒。

## 常用验证

```bash
curl --noproxy '*' http://127.0.0.1:8000/healthz
curl --noproxy '*' http://127.0.0.1:8000/providers
curl --noproxy '*' http://127.0.0.1:8000/voices
```

标准接口测试：

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/v1/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"你好，这是标准化接口测试。","provider":"cosyvoice_local","mode":"text","voice_id":"default_female","format":"wav","use_cache":false}'
```

## 当前建议

- 本地 CosyVoice 走 `cosyvoice_local`
- 需要低成本云端兜底时走 `edge_online`
- 联调阶段保留 `mock_local`，用于检查调用链是否通畅

## WSL 注意事项

- CosyVoice 进程实际运行在 Windows Python 环境
- WSL 内直接探测 `127.0.0.1:9233` 不可靠
- 网关已经内置 Windows `curl.exe` 桥接，所以 `/v1/tts` 可正常调用 CosyVoice
- 一键启动脚本会自动跳过已在运行的 `api.py`，避免重复拉起
