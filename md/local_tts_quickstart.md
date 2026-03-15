# 本地 TTS 最小服务快速启动

## 1. 安装依赖
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

可选（使用在线 edge-tts 引擎）：
```bash
pip install edge-tts
```

## 2. 启动服务
默认使用本地 `mock` 引擎（无需模型）：
```bash
uvicorn src.voice_service.main:app --host 0.0.0.0 --port 8000
```

切到 edge-tts：
```bash
TTS_ENGINE=edge_tts uvicorn src.voice_service.main:app --host 0.0.0.0 --port 8000
```

切到 CosyVoice HTTP（你本地已启动 CosyVoice API 时）：
```bash
TTS_ENGINE=cosyvoice_http \
COSYVOICE_API_URL=http://127.0.0.1:9233/tts \
uvicorn src.voice_service.main:app --host 0.0.0.0 --port 8000
```

说明：
- 你当前的 `CosyVoice/api.py` 默认是 `9233` 端口，不是 `9880`。
- 首次启动 `api.py` 会下载较大模型文件，未下载完成前接口不可用。

## 3. 调用接口
健康检查：
```bash
curl http://127.0.0.1:8000/healthz
```

生成语音（mock 默认输出 wav）：
```bash
curl -X POST http://127.0.0.1:8000/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"你好，这是本地测试语音。","voice_id":"default_female","speed":1.0,"format":"wav"}'
```

带参考音频（克隆场景，base64 字符串）：
```bash
curl -X POST http://127.0.0.1:8000/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"你好，这是克隆测试。","voice_id":"clone_001","speed":1.0,"format":"wav","reference_audio_base64":"<BASE64_AUDIO>"}'
```

返回字段 `audio_path` 指向本地文件，默认目录为 `output_audio/`。
