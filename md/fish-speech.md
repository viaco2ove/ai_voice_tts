Fish Speech S2 Pro
项目仓库：https://github.com/fishaudio/fish-speech

autodl 云端体验：
https://www.autodl.art/app/market/167

零样本和少样本TTS：输入 10 到 30 秒的语音样本以生成高质量的 TTS 输出
多语言和跨语言支持：只需将多语言文本复制并粘贴到输入框中——无需担心语言问题。目前支持英语、日语、韩语、中文、法语、德语、阿拉伯语和西班牙语。
无音素依赖：模型具有强大的泛化能力，不依赖音素进行 TTS。它可以处理任何语言脚本的文本
高准确性：在 Seed-TTS Eval 上实现约 0.4% 的低 CER（字符错误率）和约 0.8% 的 WER（词错误率)

语音控制

Fish Speech S2 官方说明使用的是自然语言标签，而不是固定的中文情感列表。

可直接在文本中插入类似 [laugh]、[whispers]、[super happy] 这样的标签，对局部语气和情绪进行细粒度控制。
也支持更自由的自然语言描述，例如 [whisper in small voice]、[professional broadcast tone]、[pitch up]，可以在词语或短句位置做更开放的表达控制。
官方当前强调的是“按需写描述”，而不是只依赖预设标签；如果效果不够明显，可以把描述写得更具体。