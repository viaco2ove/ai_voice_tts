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

CosyVoice 网关命令是：

```bash
TTS_ENGINE=cosyvoice_http \
COSYVOICE_API_URL=http://127.0.0.1:9233/tts \
uvicorn src.voice_service.main:app --host 0.0.0.0 --port 8000
```

但前提是 `CosyVoice` 上游 `api.py` 已经真正启动并监听 `9233`。当前机器上这一步仍可能因为模型加载耗时较长而未就绪。
