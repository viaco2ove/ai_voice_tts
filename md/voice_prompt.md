# 提示词音色规则说明

本文专门说明 `/v1/tts` 的 `mode=prompt_voice` 当前是怎么工作的。

先说结论：

- 现在不要把所有 provider 混为一谈
- `cosyvoice_local` 已经接入真实 `instruct`
- `edge_online` 仍然是规则打分式风格路由
- 所以“提示词音色”现在是分 provider 的，不再是统一的假实现
- 如果你理解的“提示词音色”是“把整段描述直接喂给真实 TTS 模型，让模型自己决定怎么说”，这个能力现在只在 `cosyvoice_local` 这条链路上成立

## 先把实话写明白

旧版本下，这个“提示词音色”对真实 provider 来说，本质上主要就是匹配和路由。
现在不是了，至少默认的 `cosyvoice_local` 链路已经接入了真实 instruct。

更准确地说：

- 它先在网关层解析 `prompt_text`
- 如果当前 provider 支持真实 prompt/instruct，就优先走真实能力
- 如果当前 provider 不支持，再退回到 `style_presets` / `voice_id` 路由

也就是说：

- `cosyvoice_local`：现在是“真实 instruct + 辅助选音色”
- `edge_online`：还是“网关先做规则匹配，再选音色”

如果你觉得这和 UI 上“提示词音色”这四个字的直觉不一致，这个判断在旧实现里是对的。
现在请按下面这句理解：

- `cosyvoice_local`：真提示控制
- `edge_online`：假提示控制，只有路由

## 各 provider 现在到底怎么处理 `prompt_text`

`cosyvoice_local`

- 现在会优先走真实的 CosyVoice `/instruct`
- 网关会把 `prompt_text` 透传给本地 CosyVoice
- 同时仍然会根据提示词推断更合适的基础音色，例如 `default_male` / `default_female`
- 所以对 `cosyvoice_local` 来说，`prompt_voice` 已经不是单纯假的匹配器了
- 默认不传 `provider` 时，当前项目就是走这条链路

`edge_online`

- 网关仍然会用 `prompt_text` 先做 style 匹配
- 但 `edge_tts` 本身不理解这段 `prompt_text`
- 真正生效的是最后选中的 `voice_id` 和语速
- 所以 `edge_online` 仍然不属于“真实提示控制”

一句最直接的话：

- 你要“模型真的吃提示词”，就用 `cosyvoice_local`
- 你要的是 `edge_online`，那它现在仍然只是根据提示词帮你挑 Edge 音色

`mock`

- 这是测试引擎
- 它会根据 `prompt_text` 做一些假的音调差异
- 这个行为仅用于本地调链路，不能代表真实 provider 的能力

## 它到底在做什么

当请求里带上：

```json
{
  "mode": "prompt_voice",
  "prompt_text": "青年男性，干练，自信，明亮，有力"
}
```

网关不会把整段 `prompt_text` 原样交给所有 TTS 模型做统一控制。

当前实际是：

- `cosyvoice_local`：会把 `prompt_text` 继续透传给 CosyVoice instruct
- `edge_online`：不会，仍然只在网关层用于匹配

它会先做“选风格 / 选音色方向”：

1. 先把文本标准化  
统一大小写，去掉常见标点和多余空白。

2. 先看能不能直接命中某个 style  
优先匹配 `style id`、`style label`、`prompt_keywords`。

3. 再做语义信号打分  
当前内置识别这些信号组：

- `male`
- `female`
- `gentle`
- `story`
- `steady`
- `bright`
- `broadcast`

4. 选分数最高的 style  
如果最高分大于 0，就使用这个 style 对应的 `provider` 和 `voice_id`。

但这里有一个关键前提：

- 当前 provider 如果已经支持真实 prompt/instruct，网关不会为了命中别的 style 就跨 provider 抢路由
- 所以默认 `cosyvoice_local` 不会因为 `bright_stream` 分数更高就跳到 `edge_online`

如果这个 style 绑定的是 `edge_online`，输出格式也会自动改成 `mp3`。  
这是因为 `edge_tts` 当前不支持 `wav`。

5. 如果没有 style 命中，再做兜底  
先尝试根据“男声 / 女声”这类明显性别信号推断音色。
如果还推断不出来，就按顺序回退：

- 使用请求里的 `voice_id`
- 使用请求里的 `provider` 默认音色
- 使用网关默认 provider 的默认音色

## 当前识别的主要信号词

下面这些词目前最容易起作用。

`male`

- 男声
- 男性
- 男生
- 青年男性
- 青年男
- 少年感
- 磁性男

`female`

- 女声
- 女性
- 女生
- 少女
- 御姐
- 甜妹

`gentle`

- 温柔
- 治愈
- 柔和
- 轻柔
- 温暖
- 暖心
- 细腻
- 抒情

`story`

- 故事
- 讲述
- 叙述
- 娓娓道来
- 旁白

`steady`

- 沉稳
- 稳重
- 成熟
- 纪录片
- 说明
- 口播
- 专业
- 坚定
- 果决
- 磁性
- 低沉
- 干练

`bright`

- 活泼
- 明快
- 明亮
- 清亮
- 轻快
- 朝气
- 元气
- 年轻
- 青年
- 张扬
- 自信
- 热情
- 有力
- 爽朗

`broadcast`

- 播报
- 直播
- 主持
- 主播
- 口播

## 当前默认风格

当前默认配置里有 3 个风格路由：

`warm_story`

- 绑定音色：`cosyvoice_local / default_female`
- 适合：温柔讲述、故事感、治愈感
- 关键词：`温柔`、`治愈`、`讲述`、`故事`、`柔和`、`温暖`、`细腻`、`抒情`

`steady_male`

- 绑定音色：`cosyvoice_local / default_male`
- 适合：沉稳男声、纪录片、说明、专业口播
- 关键词：`沉稳`、`纪录片`、`说明`、`男声`、`男性`、`磁性`、`口播`、`坚定`、`干练`

`bright_stream`

- 绑定音色：`edge_online / zh-CN-XiaoxiaoNeural`
- 适合：明快播报、直播感、活力表达
- 关键词：`活泼`、`明快`、`播报`、`直播`、`明亮`、`自信`、`朝气`、`有力`、`爽朗`

## 你的提示词为什么以前容易出问题

比如这类提示词：

```text
一位干练明亮有力的青年男性，语调张扬自信，语速偏快，语调洪亮，充满活力与朝气，口吻坚定果决。
```

对人来说，它表达得很清楚：

- 男性
- 干练
- 自信
- 明亮
- 有力
- 朝气

但旧逻辑太依赖少量精确关键词，容易被“明亮 / 活力 / 朝气”带偏，错误路由到偏明快的女声风格，或者直接回退默认音色。

现在的规则已经加强：

- 会识别 `male`
- 会识别 `steady`
- 会识别 `bright`
- 会对“男提示词命中女风格”做扣分
- 默认 `cosyvoice_local` 还会继续把整段 `prompt_text` 交给 CosyVoice instruct

所以像上面这句，现在会优先路由到更接近“男声、干练、坚定”的风格，默认会落到：

```text
cosyvoice_local / default_male
```

而且这次不只是“路由到男声”，`prompt_text` 本身也会继续传给 CosyVoice instruct。

## 推荐怎么写提示词

最稳的写法不是一大段散文，而是 3 到 8 个高信号词。

推荐写法：

```text
青年男性，干练，自信，明亮，有力，朝气
```

或者：

```text
温柔，治愈，细腻，故事感，娓娓道来
```

或者：

```text
沉稳，男声，纪录片，专业，口播，坚定
```

不太推荐只写这种：

```text
我想要一种让我感觉非常舒服、同时带一点高级感、又像朋友一样自然聊天的声音
```

原因不是这句话“错”，而是它里面可被稳定识别的信号词太少，路由结果会更不稳定。

## 对前端的建议

如果前端是自由输入提示词，建议同时传 `provider`，必要时再传 `voice_id`。

例如：

```json
{
  "text": "你好，很高兴见到你。",
  "provider": "cosyvoice_local",
  "voice_id": "default_male",
  "mode": "prompt_voice",
  "prompt_text": "青年男性，干练，自信，明亮，有力，朝气",
  "format": "wav"
}
```

这样即使提示词没有命中任何 style，也不会直接失败，而且回退方向仍然可控。

另外，如果前端固定传了 `format=wav`，但提示词把请求路由到了 `edge_online`，网关会自动回退成 `mp3`，避免出现：

```text
edge_tts engine currently supports mp3 only
```

## 兜底行为

如果 `prompt_text` 没有命中任何 style，也没有足够的性别信号去推断音色，系统会继续回退，不会再因为“提示词没匹配到 style”直接报错。

回退顺序：

1. 请求里的 `voice_id`
2. 请求里的 `provider` 默认音色
3. 网关默认 provider 的默认音色

## 一条实用规则

如果你的目标是“控制声音方向”，就写关键信号词。  
如果你的目标是“控制具体台词内容”，就放在 `text` 里，不要期待 `prompt_text` 逐字理解整段文案。
