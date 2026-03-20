# Voice Gateway
test
一个可配置的一体化语音网关，统一管理文生语音（TTS）与语音识别（ASR），支持一键启动、标准化接口与 OpenAI 兼容接口。

## 功能概览

- TTS 标准化接口 `/v1/tts`，支持 `text | clone | mix | prompt_voice`
- 上传参考音频克隆 `/v1/tts/clone_upload`
- OpenAI 兼容 TTS `/v1/audio/speech`
- ASR 文件识别 `/v1/asr`
- ASR 流式识别 `/v1/asr/stream`（WebSocket）
- OpenAI 兼容 ASR `/v1/audio/transcriptions`
- YAML 配置驱动，支持自动拉起上游服务

## 快速启动

```bash
cd /mnt/d/users/viaco/tools/voice
./scripts/start_all.sh
```

默认配置在 `config/services.yaml`，可切换 provider、端口、启动方式。

## 配置示例

`config/services.yaml` 中包含：

- `gateway`：网关监听与默认 provider
- `providers`：TTS provider 列表
- `asr_gateway` / `asr_providers`：ASR provider 列表
- `voice_presets` / `style_presets`：音色与提示词映射

## TTS 调用示例

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/v1/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"你好，这是标准化接口测试。","provider":"cosyvoice_local","mode":"text","voice_id":"default_female","format":"wav","use_cache":false}'
```

上传克隆音色：

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/v1/tts/clone_upload \
  -F 'text=这是上传参考音频后的克隆测试' \
  -F 'provider=cosyvoice_local' \
  -F 'format=wav' \
  -F 'reference_text=这是参考音频对应文本' \
  -F 'reference_audio=@/abs/path/reference.wav'
```

OpenAI 兼容 TTS：

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{"model":"tts-1","input":"这是一段 OpenAI 兼容格式的测试。","voice":"default_female","response_format":"wav"}' \
  --output out.wav
```

## ASR 调用示例

文件识别：

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/v1/asr \
  -F 'provider=mock_asr' \
  -F 'language=zh' \
  -F 'audio=@/abs/path/audio.wav'
```

OpenAI 兼容识别：

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/v1/audio/transcriptions \
  -F 'file=@/abs/path/audio.wav' \
  -F 'language=zh' \
  -F 'provider=local_whisper'
```

流式识别（WebSocket）：

- 连接：`ws://127.0.0.1:8000/v1/asr/stream`
- 协议：`start` → 多次 `audio` → `end`

```json
{"event":"start","provider":"local_whisper","language":"zh","format":"wav","segment_seconds":2.0}
{"event":"audio","audio_base64":"..."}
{"event":"end"}
```

## 本地 Whisper

`local_whisper` 由 `faster-whisper` 驱动，需要额外依赖与模型下载。

启用方式：

```yaml
asr_gateway:
  default_provider: local_whisper

asr_providers:
  local_whisper:
    engine: local_whisper
    enabled: true
```

## 文档

- 接口文档：`md/apidoc.md`
- 启动说明：`md/startup.md`
- CosyVoice 接入：`md/CosyVoice_run.md`

## 运行环境

- Python 3.10+
- 依赖见 `requirements.txt`
