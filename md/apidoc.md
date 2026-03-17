# Voice Gateway API 文档

## 概述

本服务对外提供统一语音生成接口，屏蔽不同语音引擎的调用差异。当前支持的能力由 YAML 配置文件控制，可接入 `cosyvoice_http`、`edge_tts`、`mock` 等 provider。

默认入口：`http://127.0.0.1:8000`

## 核心接口

### 1. 健康检查

```http
GET /healthz
```

### 2. 查询 provider 列表

```http
GET /providers
```

### 3. 查询音色预设

```http
GET /voices
```

### 4. 标准文生语音接口

```http
POST /v1/tts
Content-Type: application/json
```

请求体示例：

```json
{
  "text": "你好，这是统一语音网关。",
  "provider": "cosyvoice_local",
  "mode": "text",
  "voice_id": "default_female",
  "speed": 1.0,
  "format": "wav",
  "use_cache": true
}
```

返回示例：

```json
{
  "provider": "cosyvoice_local",
  "engine": "cosyvoice_http",
  "mode": "text",
  "resolved_voice_id": "default_female",
  "cache_hit": false,
  "file_name": "xxxx.wav",
  "audio_path": "/abs/path/output_audio/xxxx.wav",
  "audio_url": "/audio/xxxx.wav",
  "audio_url_full": "http://127.0.0.1:8000/audio/xxxx.wav"
}
```

### 5. 克隆音色上传接口

```http
POST /v1/tts/clone_upload
Content-Type: multipart/form-data
```

表单字段：

- `text`: 要合成的文本
- `reference_audio`: 参考音频文件
- `reference_text`: 参考音频对应文本，可选
- `provider`: 可选，默认走配置中的默认 provider
- `format`: 可选，如 `wav`
- `speed`: 可选，默认 `1.0`
- `use_cache`: 可选，默认 `true`

示例：

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/v1/tts/clone_upload \
  -F 'text=这是上传参考音频后的克隆测试' \
  -F 'provider=cosyvoice_local' \
  -F 'format=wav' \
  -F 'reference_text=这是参考音频对应文本' \
  -F 'reference_audio=@/abs/path/reference.wav'
```

## 支持模式

### `mode=text`
普通文生语音。

### `mode=clone`
需要 `reference_audio_base64`，可选 `reference_text`。

```json
{
  "text": "用参考音频克隆这个声音。",
  "provider": "cosyvoice_local",
  "mode": "clone",
  "format": "wav",
  "reference_audio_base64": "BASE64_AUDIO",
  "reference_text": "参考音频对应文本"
}
```

### `mode=mix`
提供多个音色及权重。当前网关会按最大权重解析主音色，并把混合信息透传给后端引擎。

```json
{
  "text": "混合音色测试。",
  "provider": "cosyvoice_local",
  "mode": "mix",
  "mix_voices": [
    {"voice_id": "default_female", "weight": 0.7},
    {"voice_id": "default_male", "weight": 0.3}
  ],
  "format": "wav"
}
```

### `mode=prompt_voice`
通过提示词映射到配置中的 `style_presets`。

```json
{
  "text": "请用更温柔的故事感来读。",
  "mode": "prompt_voice",
  "prompt_text": "温柔 治愈 故事",
  "format": "wav"
}
```

## 兼容旧接口

```http
POST /tts
```

兼容字段：`text`、`voice_id`、`speed`、`format`、`reference_audio_base64`、`reference_text`、`use_cache`。

## 音频下载

```http
GET /audio/{file_name}
```

## 错误说明

- `400`: 参数不合法，或 provider 不支持当前模式
- `404`: 音频文件不存在

## 建议

- 生产环境优先走 `/v1/tts`
- 需要文件上传克隆时走 `/v1/tts/clone_upload`
- 所有 provider、音色、提示词风格都放在 `config/services.yaml` 统一管理
