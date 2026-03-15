# CosyVoice 部署方案

## LM Studio 如何？
结论：可以配合使用，但不建议把 LM Studio 当作 TTS 主引擎。

- 适合 LM Studio 的部分：文案改写、分句、情感标签生成（如“平静”“兴奋”）。
- 不适合 LM Studio 的部分：语音克隆与高质量语音合成主链路。
- 原因：TTS/克隆依赖声学模型、说话人特征提取、vocoder 等音频推理流程，通常由专用 Python/PyTorch 项目提供。

推荐定位：
- `LM Studio` = 文本侧前处理
- `CosyVoice 服务` = 语音合成与克隆

## 更适合的方案是？

### 方案 A（推荐）：本地双服务
1. 文本服务：LM Studio（或 Ollama）
2. 语音服务：CosyVoice（Python API 或 HTTP API）
3. 编排层：一个轻量 API（FastAPI）串起来

处理流程：
1. 输入文本
2. 先调用 LM 做断句/风格标注
3. 再调用 CosyVoice 生成音频
4. 用 `text+voice+speed` 哈希做缓存，命中则直接返回

### 方案 B：纯本地最小可用（CPU 友好）
- 直接跑 CosyVoice 推理，不接 LM。
- 先做短句合成与缓存，验证音色与速度。

## 当前仓库支持
- `TTS_ENGINE=mock`：本地链路验证
- `TTS_ENGINE=edge_tts`：在线语音
- `TTS_ENGINE=cosyvoice_http`：对接本地 CosyVoice API

## 启动与联调
环境设置：
```bash
cd /mnt/d/users/viaco/tools/voice
source .venv_wsl/bin/activate
```

启动网关服务：
```bash
TTS_ENGINE=cosyvoice_http \
COSYVOICE_API_URL=http://127.0.0.1:9233/tts \
uvicorn src.voice_service.main:app --host 0.0.0.0 --port 8000
```

检查服务：
```bash
curl --noproxy '*' http://127.0.0.1:8000/healthz
```

合成请求（不带克隆）：
```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"你好，这是CosyVoice联调测试。","voice_id":"default_female","speed":1.0,"format":"wav"}'
```

说明：
- 你当前的 `CosyVoice/api.py` 默认端口是 `9233`，不是 `9880`。
- 首次启动 `api.py` 会下载较大模型，下载完成前接口不可用。

## 最小接口约定（示例）
- `POST /tts`
- 入参：`text`, `voice_id`, `speed`, `format`, `reference_audio_base64(可选)`
- 出参：`audio_path`

示例请求：
```json
{
  "text": "你好，欢迎使用本地语音合成。",
  "voice_id": "default_female",
  "speed": 1.0,
  "format": "wav"
}
```
