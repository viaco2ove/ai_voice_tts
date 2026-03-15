# CosyVoice 运行记录

## 目标

让 `/mnt/d/Users/viaco/tools/voice` 的 `/tts` 接口真正调用本地 CosyVoice，而不是 `mock` 的蜂鸣音。

## 当前已验证可用

### 1. 启动 Windows 侧 CosyVoice

```bash
cd /mnt/d/Users/viaco/PycharmProjects/CosyVoice
/mnt/d/Users/viaco/PycharmProjects/CosyVoice/.venv/Scripts/python.exe api.py
```

说明：

- 监听地址是 `127.0.0.1:9233`
- 首次启动可能会下载 `wetext` 等附加资源，第一次推理会慢

### 2. 启动 voice 网关

```bash
cd /mnt/d/Users/viaco/tools/voice
source .venv/bin/activate
TTS_ENGINE=cosyvoice_http \
COSYVOICE_API_URL=http://127.0.0.1:9233/tts \
uvicorn src.voice_service.main:app --host 0.0.0.0 --port 8000
```

### 3. 健康检查

```bash
curl --noproxy '*' http://127.0.0.1:8000/healthz
```

应返回：

```json
{"status":"ok","engine":"cosyvoice_http"}
```

### 4. 生成语音

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"你好，这是通过voice_service转发到CosyVoice的最终测试。","voice_id":"default_female","speed":1.0,"format":"wav","use_cache":false}'
```

已实测成功生成：

```text
/mnt/d/Users/viaco/tools/voice/output_audio/ea0536682255e12dfee2d6ef.wav
```

## 这次修过的坑

- `voice_service` 默认引擎是 `mock`，如果不显式设置 `TTS_ENGINE`，输出只会是“嘟一声”
- `CosyVoice/api.py` 里 `load_onnx=False` 和当前安装版本不兼容，已修
- `CosyVoice` 的 yaml 加载链路和当前依赖版本不兼容，已改为 `yaml.FullLoader`
- WSL 里访问 Windows 的 `127.0.0.1:9233` 不稳定，`voice_service` 已加 Windows `curl.exe` 回退桥接

## 当前注意事项

- CosyVoice 返回的是 float32 wav，不是所有简单播放器都兼容
- 如果某些工具打不开 wav，不代表合成失败
- 要求最稳的兼容性时，可以后续再加一步自动转 PCM16

## 备用方案

如果 CosyVoice 临时不可用，可以先切到 `edge_tts`：

```bash
cd /mnt/d/Users/viaco/tools/voice
source .venv/bin/activate
TTS_ENGINE=edge_tts \
uvicorn src.voice_service.main:app --host 0.0.0.0 --port 8000
```

然后请求时改用 `mp3`：

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"你好，现在已经切到真实语音引擎。","voice_id":"zh-CN-XiaoxiaoNeural","speed":1.0,"format":"mp3","use_cache":false}'
```
