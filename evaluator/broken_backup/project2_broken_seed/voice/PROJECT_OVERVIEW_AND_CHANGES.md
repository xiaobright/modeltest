# Voice 项目总览与改动说明

本文档用于说明当前 voice 项目的结构、运行链路，以及最近完成的阶段2改动（本地 RKLLM 常驻 + 阻塞式整段问答 + 多轮记忆截断）。

## 1. 目录结构与职责

- [voice_assistant_integrated.py](voice_assistant_integrated.py)
  - 主程序入口。
  - 包含完整语音链路：录音/VAD、ASR、意图识别、天气查询、对话生成、TTS 播放。
  - 当前已接入本地 RKLLM 常驻模型（阶段2）。

- [voice_loop_talk.py](voice_loop_talk.py)
  - 轻量原型脚本。
  - 适合快速验证“录音 -> 识别 -> 简单意图 -> 播报”。

- [intent_tuner.py](intent_tuner.py)
  - 意图识别策略调参和评估脚本。
  - 用于测试关键词/正则/模糊分数阈值效果。

- [collect_results.py](collect_results.py)
  - 结果汇总脚本（将 JSON 指标汇总为 CSV）。

- [requirements.txt](requirements.txt)
  - voice 目录依赖清单。

## 2. 当前主流程（阻塞式整段处理）

主流程定义在 [voice_assistant_integrated.py](voice_assistant_integrated.py)。

1. 程序启动：
   - 加载 ASR 模型。
   - 加载本地 RKLLM 模型并常驻内存。
2. 录音阶段：
   - 使用 webrtcvad，检测到静音尾段后结束本轮录音。
3. 识别阶段：
   - 将整段 PCM 写入临时 WAV。
   - 使用 faster-whisper 对整段音频做 ASR。
4. 业务分流：
   - 先做意图识别（心率/睡眠/离床/睡姿/鼾声/聊天）。
   - 天气问题走天气分支。
   - 普通聊天走本地 RKLLM。
5. 回复阶段：
   - 等待模型完整回复（阻塞式，不流式）。
   - 将完整文本整段输入 TTS 播放。

## 3. 本次阶段2改动总结

以下改动均已落在 [voice_assistant_integrated.py](voice_assistant_integrated.py)：

1. 新增本地 RKLLM 配置
   - 增加了 RKLLM 路径和推理参数配置（支持环境变量覆盖）。

2. 启动即加载模型常驻
   - 程序启动后创建本地聊天引擎，模型常驻内存等待输入。
   - 空闲时不推理，只占内存，不持续占用算力。

3. 替换对话通路
   - chat 分支改为本地 RKLLM 阻塞式推理。
   - 失败时返回兜底回复，避免中断主循环。

4. 加入多轮会话记忆
   - 会话保留历史消息。
   - 新增历史截断逻辑，限制最近轮数，防止上下文无限增长。

5. 保持现有交互形态
   - 未引入流式推理。
   - 保留“VAD 截断后整段输入模型，整段输出给 TTS”的行为。

## 4. 关键配置项

在 [voice_assistant_integrated.py](voice_assistant_integrated.py) 中可通过环境变量覆盖：

- RKLLM_PROJECT_DIR
- RKLLM_SO_PATH
- RKLLM_MODEL_PATH
- RKLLM_MAX_NEW_TOKENS
- RKLLM_MAX_CONTEXT_LEN
- RKLLM_MAX_CHAT_TURNS
- QWEATHER_KEY

说明：若不配置 RKLLM_*，默认按 ../rkllm_py 目录推导 so 与模型路径。

## 5. 依赖关系说明

- 语音相关：faster-whisper、webrtcvad、sounddevice、soundfile
- 网络相关：requests（天气接口）
- 文字处理：pypinyin、rapidfuzz
- 本地大模型：来自上层目录 [../rkllm_py](../rkllm_py) 的 rkllm_sdk

## 6. 运行与联调建议

1. 启动前检查
   - so 与模型文件路径有效。
   - 麦克风输入可用。
   - TTS 可用（Piper 或 SAPI）。

2. 首轮日志观察
   - 是否出现“本地大模型已常驻内存，等待输入”。
   - 若初始化失败，先核对 RKLLM_SO_PATH 与 RKLLM_MODEL_PATH。

3. 功能回归建议
   - 心率/睡眠/离床/睡姿/鼾声意图分别口测 1 次。
   - 天气查询测试 1 次（有无城市记忆都测）。
   - 普通闲聊连续 5~10 轮，观察会话上下文是否稳定。

## 7. 下一步可选优化

- 将天气查询能力注册为工具调用，统一到模型侧决策。
- 增加推理耗时与加载耗时日志，便于性能排查。
- 把硬编码城市正则迁移为可配置列表。
- 视资源情况评估更小模型或更小 max_new_tokens。

---

维护说明：
若后续继续改造主流程，请优先更新本文档中的“第2节主流程”和“第3节改动总结”，确保团队对齐。