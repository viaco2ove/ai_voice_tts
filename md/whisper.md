  1. 把 local_whisper 的部分结果改成“只返回新增文本”，避免重复输出
  2. 直接接入真正流式的 ASR（如 Vosk 或 Whisper.cpp streaming）
