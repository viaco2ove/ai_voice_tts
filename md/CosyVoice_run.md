# CosyVoice 接入与一键启动

## 当前方式

本仓库不再推荐手工敲长命令。CosyVoice 的接入参数已经收敛到 `config/services.yaml`。

默认 provider：`cosyvoice_local`

关键配置如下：

```yaml
providers:
  cosyvoice_local:
    engine: cosyvoice_http
    startup:
      enabled: true
      command: /mnt/d/Users/viaco/PycharmProjects/CosyVoice/.venv/Scripts/python.exe api.py
      cwd: /mnt/d/Users/viaco/PycharmProjects/CosyVoice
      wait_strategy: sleep
      wait_seconds: 15
    options:
      api_url: http://127.0.0.1:9233/tts
      clone_api_url: http://127.0.0.1:9233/clone
      request_mode: form
```

## 启动网关

```bash
cd /mnt/d/Users/viaco/tools/voice
./scripts/start_all.sh
```

当前默认已经启用自动拉起 `CosyVoice`，不需要再额外手工执行 `api.py`。

## 健康检查

```bash
curl --noproxy '*' http://127.0.0.1:8000/healthz
curl --noproxy '*' http://127.0.0.1:8000/providers
curl --noproxy '*' http://127.0.0.1:8000/voices
```

## 文生语音示例

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/v1/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"你好，这是通过统一网关调用 CosyVoice 的测试。","provider":"cosyvoice_local","mode":"text","voice_id":"default_female","speed":1.0,"format":"wav","use_cache":false}'
```

## 克隆音色示例

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/v1/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"这是克隆音色测试。","provider":"cosyvoice_local","mode":"clone","format":"wav","reference_audio_base64":"BASE64_AUDIO","reference_text":"参考音频文本","use_cache":false}'
```

## 提示词生成音色示例

```bash
curl --noproxy '*' -X POST http://127.0.0.1:8000/v1/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"请更温柔地读这句话。","mode":"prompt_voice","prompt_text":"温柔 治愈 故事","format":"wav","use_cache":false}'
```

## 说明

- `mix` 和 `prompt_voice` 已在网关层标准化
- 实际效果取决于底层 provider 是否支持对应能力
- 当前 CosyVoice 本地接入优先保证 `text` 和 `clone` 跑通
- WSL 下不直接依赖 `127.0.0.1:9233` 探测，网关已内置 Windows `curl.exe` 桥接
- 如需云端兜底，可在请求中把 `provider` 切到 `edge_online`
