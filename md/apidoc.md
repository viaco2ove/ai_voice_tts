# Voice Gateway API 文档

## 概述

本服务对外提供统一语音生成接口，屏蔽不同语音引擎的调用差异。当前支持的能力由 YAML 配置文件控制，可接入 `cosyvoice_http`、`edge_tts`、`mock` 等 provider。

默认入口：`http://127.0.0.1:8000`


## 当前提供的接口 
  - GET /healthz                                                                                                                                                     
    返回服务健康与当前 provider 概览。                                                                                                                               
  - GET /providers                                                                                                                                                   
    返回已启用的 provider 列表、默认音色、支持模式。                                                                                                                 
  - GET /voices                                                                                                                                                      
    返回音色预设列表（来自 config/services.yaml）。                                                                                                                  
  - POST /v1/tts                                                                                                                                                     
    标准化文生语音接口。                                                                                                                                             
    支持 mode=text | clone | mix | prompt_voice。                                                                           
  - POST /v1/tts/clone_upload                                                                                                                                        
    上传参考音频进行克隆，无需手动转 base64。                                                                                                                        
    multipart/form-data，字段见 md/apidoc.md。                                                                                                                       
  - POST /v1/audio/speech                                                                                                                                            
    OpenAI 兼容接口，返回音频流，不返回 JSON。                                                                                                                       
    支持 response_format=wav|mp3。                                                                                                                                   
  - POST /tts                                                                                                                                                        
    旧接口兼容，字段和之前一致。                                                                                                                                     
  - GET /audio/{file_name}                                                                                                                                           
    下载生成的音频文件。                                                                                                                                             
    
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

当前默认配置下的预设音色：

- `default_female`：默认中文女声，provider=`cosyvoice_local`，支持 `text / clone / mix / prompt_voice`
- `default_male`：默认中文男声，provider=`cosyvoice_local`，支持 `text / clone / mix / prompt_voice`
- `edge_xiaoxiao`：Edge 晓晓，provider=`edge_online`，支持 `text / mix / prompt_voice`
- `edge_yunxi`：Edge 云希，provider=`edge_online`，支持 `text / mix / prompt_voice`

返回示例：

```json
[
  {
    "id": "default_female",
    "label": "默认中文女声",
    "provider": "cosyvoice_local",
    "voice_id": "default_female",
    "modes": ["text", "clone", "mix", "prompt_voice"],
    "description": "默认中文女声，适合通用播报"
  },
  {
    "id": "default_male",
    "label": "默认中文男声",
    "provider": "cosyvoice_local",
    "voice_id": "default_male",
    "modes": ["text", "clone", "mix", "prompt_voice"],
    "description": "默认中文男声，适合说明类内容"
  }
]
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

### 6. OpenAI 兼容接口

```http
POST /v1/audio/speech
Content-Type: application/json
```

请求体示例：

```json
{
  "model": "tts-1",
  "input": "这是一段 OpenAI 兼容格式的测试。",
  "voice": "default_female",
  "speed": 1.0,
  "response_format": "wav",
  "provider": "cosyvoice_local"
}
```

该接口直接返回音频文件流，不返回 JSON。
`response_format` 当前支持 `wav` 或 `mp3`。

## 支持模式

### `mode=text`
普通文生语音。

### `mode=clone`
需要 `reference_audio_base64`，可选 `reference_text`。

补充规则：

- `clone` 只会落到支持克隆的 provider
- 如果前端误传了 `provider=edge_online`，或者带了 `edge_xiaoxiao / edge_yunxi` 这类不支持克隆的音色，网关会自动回退到支持 `clone` 的 provider，而不是直接返回 `400`
- 当前默认配置下，这个回退目标就是 `cosyvoice_local`

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
`prompt_voice` 现在按 provider 分策略，不能再把所有引擎理解成一套统一实现。

| provider | `prompt_text` 怎么处理 | 是否是真提示控制 | 备注 |
| --- | --- | --- | --- |
| `cosyvoice_local` | 网关先解析提示词，辅助选择更合适的基础音色；中文提示词会先编译成英文 persona，再送到 CosyVoice `/instruct` | 是 | 当前默认 provider |
| `edge_online` | 只在网关层做 style 匹配、选音色和格式兜底；`prompt_text` 不会传给 `edge_tts` | 否 | 最终只能靠 `voice_id` 生效 |

一句话说明：

- 默认不传 `provider` 时，会走 `gateway.default_provider=cosyvoice_local`
- 所以当前默认链路下，`prompt_voice` 已经是“真实 CosyVoice instruct + 网关辅助选基础音色”

解析顺序：

1. 先标准化 `prompt_text`  
统一大小写，去掉常见标点和多余空白。
2. 判断当前 provider 是否支持原生 prompt/instruct  
如果支持，优先保留在当前 provider 内部处理，不跨 provider 抢路由。
3. 在当前 provider 内做 style 命中和信号词打分  
优先级依次是 `style id`、`style label`、`prompt_keywords`、语义信号组。
4. 如果没有明确 style，再尝试性别推断  
例如从 `男声`、`女性`、`青年男性` 这类信号里，推断更合适的基础音色。
5. 如果仍然无法推断，按顺序回退  
`voice_id` -> 当前 `provider` 默认音色 -> 网关默认 provider 默认音色。

当前内置信号组示例：

- `male`：`男声`、`男性`、`男生`、`青年男性`
- `female`：`女声`、`女性`、`女生`、`御姐`
- `gentle`：`温柔`、`治愈`、`柔和`、`温暖`
- `story`：`故事`、`讲述`、`叙述`、`旁白`
- `steady`：`沉稳`、`纪录片`、`说明`、`口播`、`坚定`、`干练`
- `bright`：`活泼`、`明快`、`明亮`、`朝气`、`自信`、`有力`
- `broadcast`：`播报`、`直播`、`主持`、`主播`

补充规则：

- `cosyvoice_local` 即使命中了 style，最终也只会在 `cosyvoice_local` 内部选基础音色，不会因为别的 provider 分数更高就跳去 `edge_online`
- `edge_online` 没有原生 prompt 能力，所以仍然走“提示词选音色”的路由模式
- 如果最终落到 `edge_online`，网关会自动把输出格式切成 `mp3`，避免 `edge_tts engine currently supports mp3 only`
- `style_presets` 负责“选方向 / 选基础音色”，不会替代 `cosyvoice_local` 的真实 `/instruct`
- `cosyvoice_local` 为了避免模型把中文提示词本身读出来，不会原样透传中文关键词串；网关会先把它改写成更适合 CosyVoice-Instruct 的英文 persona 描述

使用建议：

- 想要“模型真的吃提示词”，优先用 `provider=cosyvoice_local`
- 想要稳定控制男声/女声底色，建议同时传 `provider`，必要时再显式传 `voice_id`
- `cosyvoice_local` 可以直接写自然语言描述；但如果你希望基础音色更稳定，仍建议带上高信号词，例如“男声 / 温柔 / 干练 / 明亮 / 播报 / 故事”
- `edge_online` 仍然不理解整段人设文案，只是根据提示词帮你选更接近的 Edge 音色

```json
{
  "text": "请用更温柔的故事感来读。",
  "mode": "prompt_voice",
  "prompt_text": "温柔 治愈 故事",
  "format": "wav"
}
```

像下面这种自由描述提示词：

```json
{
  "text": "你好，欢迎见到你。",
  "mode": "prompt_voice",
  "prompt_text": "一位干练明亮有力的青年男性，语调张扬自信，语速偏快，语调洪亮，充满活力与朝气，口吻坚定果决。"
}
```

在默认 `cosyvoice_local` 链路下，这段 `prompt_text` 不会直接原样送到模型。  
网关会先从中提取 `male / bright / steady` 相关信号，优先帮你选到更贴近“男声、干练、明亮”的基础音色，例如 `default_male`；随后再把中文提示词编译成英文 persona 描述，送到 CosyVoice `/instruct`。

如果你把同样的请求改成 `provider=edge_online`，那就不再是真实 instruct，而会退化成“根据关键词选择更接近的 Edge 音色”。

未命中 style 时的兜底示例：

```json
{
  "text": "请更自然一点。",
  "provider": "cosyvoice_local",
  "voice_id": "default_female",
  "mode": "prompt_voice",
  "prompt_text": "自然 亲切 日常对话",
  "format": "wav"
}
```

上面这类请求即使没有命中任何 `style_presets`，也会回退到 `cosyvoice_local/default_female` 继续合成，不再返回 `400`。

按 provider 看最终行为：

- `provider=cosyvoice_local`：中文 `prompt_text` 会先被编译成英文 persona，再传给 CosyVoice `/instruct`，`style_presets` 只负责辅助选基础音色
- `provider=edge_online`：`prompt_text` 不会传给 `edge_tts`，只用于路由和选音色

## 兼容旧接口

```http
POST /tts
```

兼容字段：`text`、`voice_id`、`speed`、`format`、`reference_audio_base64`、`reference_text`、`use_cache`。

## 音频下载

```http
GET /audio/{file_name}
```

## 语音识别接口

### 0. 查询 ASR provider 列表

```http
GET /v1/asr/providers
```

### 1. 文件识别

```http
POST /v1/asr
Content-Type: multipart/form-data
```

表单字段：

- `audio`: 音频文件
- `provider`: 可选，默认走 `asr_gateway.default_provider`
- `language`: 可选
- `prompt`: 可选
- `temperature`: 可选
- `format`: 可选，例如 `wav`、`mp3`

示例：

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/v1/asr \
  -F 'provider=mock_asr' \
  -F 'language=zh' \
  -F 'audio=@/abs/path/audio.wav'
```

### 2. 边说边识别（WebSocket）

```text
ws://127.0.0.1:8000/v1/asr/stream
```

消息协议（JSON）：

- `start`：初始化参数
- `audio`：传递 `audio_base64` 分片
- `end`：结束并返回最终结果

`start` 可选字段：

- `partial_interval_ms`: 服务器发送增量结果的最小时间间隔（默认 1000）
- `min_chunk_bytes`: 触发增量识别的最小累计字节数（默认 32000）
- `segment_seconds`: 按时间窗口触发增量识别（优先生效）
- `audio_bytes_per_second`: 估算音频字节率（默认 32000，用于 `segment_seconds` 计算）

示例：

```json
{"event":"start","provider":"mock_asr","language":"zh","format":"wav"}
{"event":"audio","audio_base64":"..."}
{"event":"end"}
```

返回示例（服务器推送）：

```json
{"event":"partial","provider":"mock_asr","engine":"mock_asr","text":"mock partial (32000 bytes)","language":"zh","segments":[],"is_final":false}
{"event":"final","provider":"mock_asr","engine":"mock_asr","text":"mock transcription","language":"zh","segments":[],"is_final":true}
```

说明：

- 默认实现会在收到 `end` 后返回最终结果
- 如果后端 ASR provider 支持流式识别并启用 `supports_stream`，会在接收音频时返回增量结果
- 本地 `local_whisper` 的增量结果是对当前缓存的重复解码，属于“近似流式”
- `vosk` 支持真正的流式增量识别（需要模型目录）

### 3. OpenAI 兼容识别接口

```http
POST /v1/audio/transcriptions
Content-Type: multipart/form-data
```

表单字段：

- `file`: 音频文件
- `model`: 可选，忽略
- `language`: 可选
- `prompt`: 可选
- `temperature`: 可选
- `provider`: 可选

示例：

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/v1/audio/transcriptions \
  -F 'file=@/abs/path/audio.wav' \
  -F 'language=zh' \
  -F 'provider=local_whisper'
```

返回示例：

```json
{"text":"识别结果文本"}
```

## 错误说明

- `400`: 参数不合法，或 provider 不支持当前模式
- `prompt_voice` 在当前版本下，提示词未命中 style 时会自动回退，不再因为“未匹配到 style_presets”单独报错
- `404`: 音频文件不存在

## 建议

- 生产环境优先走 `/v1/tts`
- 需要文件上传克隆时走 `/v1/tts/clone_upload`
- 所有 provider、音色、提示词风格都放在 `config/services.yaml` 统一管理
