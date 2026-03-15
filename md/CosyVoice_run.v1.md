# 当前已验证可用的启动方式

先进入项目并激活虚拟环境：

```bash
cd /mnt/d/Users/viaco/tools/voice
source .venv/bin/activate
```

## 方案 1：立即可用，真实语音

`edge_tts` 已验证可正常输出真人语音，不会再是 mock 的“嘟一声”。

启动：

```bash
TTS_ENGINE=edge_tts \
uvicorn src.voice_service.main:app --host 0.0.0.0 --port 8000
```

自检：

```bash
curl --noproxy '*' http://127.0.0.1:8000/healthz
```

应该返回：

```json
{"status":"ok","engine":"edge_tts"}
```

生成语音：

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"你好，现在已经切到真实语音引擎。","voice_id":"zh-CN-XiaoxiaoNeural","speed":1.0,"format":"mp3","use_cache":false}'
```

说明：

- `edge_tts` 当前使用 `mp3`
- 如果你没设置 `TTS_ENGINE`，默认还是 `mock`，输出会是蜂鸣音

## 方案 2：CosyVoice 本地模型

当前已验证可用。

先启动 Windows 侧 CosyVoice：

```bash
cd /mnt/d/Users/viaco/PycharmProjects/CosyVoice
/mnt/d/Users/viaco/PycharmProjects/CosyVoice/.venv/Scripts/python.exe api.py
```

再启动本项目网关：

```bash
TTS_ENGINE=cosyvoice_http \
COSYVOICE_API_URL=http://127.0.0.1:9233/tts \
uvicorn src.voice_service.main:app --host 0.0.0.0 --port 8000
```

自检：

```bash
curl --noproxy '*' http://127.0.0.1:8000/healthz
```

应该返回：

```json
{"status":"ok","engine":"cosyvoice_http"}
```

生成语音：

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"你好，这是通过voice_service转发到CosyVoice的最终测试。","voice_id":"default_female","speed":1.0,"format":"wav","use_cache":false}'
```

说明：

- 在 WSL 中直接访问 Windows 的 `127.0.0.1:9233` 可能不稳定
- 当前网关代码已经加入 Windows `curl.exe` 回退桥接，所以仍可正常调用本机 CosyVoice
- CosyVoice 返回的 wav 是 float32 编码，部分简单播放器或 Python 标准库 `wave` 会识别不了，这是格式兼容问题，不代表合成失败
