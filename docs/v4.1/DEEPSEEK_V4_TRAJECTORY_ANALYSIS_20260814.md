# DeepSeek V4 Pro：轨迹风格与 PTC 对照分析

**日期：** 2026-08-14

**范围：** Project2 V4.1b；9 份 DSH/OpenCode 原始导出

**复算数据：** [`../../evaluator/trajectory_evidence/`](../../evaluator/trajectory_evidence/README.md)

## 结论

V4 Pro 的高分不是“Linux 红利”或“官方 harness 红利”，而是与 DSH minimal 的完整
RL 对齐 scaffold 强相关。同一 Ubuntu 24.04、max 推理、相同任务提示词下，minimal 两跑
得到 **99/96**，standard 为 **91**，PTC 为 **92**。PTC 虽把标准模式全部能力映射为
单个 `run_code`，仍未恢复 minimal 的表现。

轨迹风格可以识别 scaffold 是否生效，但不能单独充当模型身份或能力证据。minimal 会把
Pro 和 Flash 都推向短块、`we`、`Good./Great./Excellent.` 首行和零阶段回复；Flash 的
风格同样剧烈变化，分数却保持 **92**。真正值得关注的是：Pro 的得分随接口从 91/92
跃升至 96/99，而 Flash 的能力基本不随接口改变。

## 样本与方法

解析脚本只统计完成态 assistant 消息，排除 DSH 流式 chunk，避免重复计算。OpenCode
只读取 assistant 的 `reasoning`、`text` 和 `tool` parts。原始导出保留在私有目录，公开
仓库只发布哈希、脚本和聚合结果，不发布完整思维链、绝对路径、system prompt 或命令输出。

| 模型/样本 | 配置 | 分数 | reasoning 块 | p50 字符 | `we` | `let me` | `I` | 阶段回复 | 工具调用 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Pro gray 1 | OpenCode | 99 | 46 | 285 | 4 | 9 | 137 | 24 | 129 |
| Pro gray 2 | OpenCode | 96 | 45 | 336 | 2 | 4 | 172 | 25 | 131 |
| Pro formal worst | OpenCode | 93 | 119 | 973 | 17 | 249 | 216 | 37 | 274 |
| Pro minimal 1 | DSH / WSL / max | 99 | 177 | 235 | 272 | 0 | 17 | 1 | 194 |
| Pro minimal 2 | DSH / WSL / max | 96 | 150 | 239 | 231 | 0 | 18 | 1 | 171 |
| Pro standard | DSH / WSL / max | 91 | 99 | 437 | 11 | 208 | 137 | 55 | 189 |
| Pro PTC | DSH / WSL / max | 92 | 94 | 550 | 16 | 194 | 237 | 33 | 164 外层 |
| Flash formal | OpenCode | 92 | 67 | 365 | 5 | 124 | 108 | 47 | 149 |
| Flash minimal | DSH / WSL / max | 92 | 173 | 128 | 209 | 0 | 9 | 1 | 178 |

词频是大小写不敏感的边界匹配；`I` 包含 `I'm`、`I'll` 等第一人称形式。不同 harness
的消息切分不完全一致，因此这些数字用于轨迹画像，不用于直接评价 token 效率。

## minimal 的轨迹指纹

minimal 的两次 Pro 运行使用相同 system prompt 哈希，只暴露 `bash` 与
`str_replace_editor`。两跑的共同特征非常稳定：

- `let me` 都为 **0**，`we` 分别为 **272/231**；
- reasoning 中位块只有 **235/239** 字符，但长尾仍可到数千字符；
- 分别有 **28/16** 个块以单独的 `Good.`、`Great.` 或 `Excellent.` 首行起头；
- 全程只有最终一次可见回复，过程推进都留在 reasoning 与工具调用中。

Web UI 只显示 `Good.` 并不代表模型只思考了一个词。原始 JSONL 证明它通常只是完整
reasoning 块的第一行，后面仍有诊断和操作计划。这个现象更像固定 scaffold 激活出的
话语策略，而不是推理被截断。

standard 和 PTC 则回到另一套稳定风格：大量 `let me`/`I`，reasoning 块更长，并向
用户发送正常的阶段性回复。它们的分数也回落到 **91/92**。因此风格变化与得分变化在
Pro 上同时发生，但还不能从相关性推出某个词本身造成了增益。

## PTC 为什么没有奏效

官方源码中的 PTC 是内置 `code` preset，不是第三方或非官方模式。它复制 standard 的
完整能力，只增加 `tool-presentation: mode: code`：模型在 wire 上只看到 `run_code`，
通过生成的 TypeScript SDK 调用原有工具。官方源码只明确把 minimal 的快照测试称为
“exact RL prompt and schemas”，没有对 PTC 作相同声明。

本次 PTC 轨迹显示：

| 指标 | 数值 |
|---|---:|
| 外层 `run_code` | 164 |
| 内层工具调用 | 187 |
| 缺少必填 `description` | 10 |
| `CODE_RUN_FAILED` | 3 |
| 0 / 1 / 2 / 3 / 4 个子调用的程序 | 13 / 122 / 24 / 3 / 2 |
| 含多工具语法的程序 | 30 |
| 使用 `Promise.all` | 0 |

122 个成功程序只执行一次子调用；真正组合多步操作的比例很低。3 次程序失败分别来自
未定义标识符和两处 TypeScript 语法错误。PTC 用时约 **25.95 分钟**，standard 约
**24.08 分钟**，也没有实测效率收益。它保留了 standard 的大控制面，又增加了一层
代码生成协议；对本轮 V4 Pro 来说，这层抽象没有形成有效批处理，反而引入新错误面。

## Flash 是关键反例

V4 Flash 从 OpenCode 切到 minimal 后，轨迹从 `let me=124`、`we=5` 变为
`let me=0`、`we=209`，阶段回复从 47 块降为 1 块，reasoning p50 从 365 降到
128 字符。尽管话语策略几乎完全改写，Ability 都是 **92**。

这说明：

- `we`、单独的 `Good.` 和少回复主要是 scaffold 指纹，不是高分充分条件；
- Flash 的后训练对工具呈现与提示词变化更稳，能力跨 harness 泛化较好；
- Pro 不是没有高能力，而是高能力的可访问性明显依赖训练分布内的接口。

## 灰测与“像 Claude”假设

两次灰测 Pro 主要使用 `I/I'm`，`let me` 很少，并以 **99/96** 完成；正式版最差体感
一跑则有 119 个 reasoning 块、`let me=249`、274 次工具调用和约 52 分钟耗时。同为
OpenCode，轨迹和交付质量都明显不同，这支持“灰测与正式通用路径的有效策略、checkpoint
或路由不同”。

但 `I'm` 风格像 Claude/Opus 不是后端身份鉴定。话语习惯会受 system prompt、工具 schema、
采样和后训练影响；没有服务端 route id、签名或可复验的模型特异行为，不能据此声称灰测
实际代理了 Claude、Fable 或其他闭源模型。更严谨的结论是：灰测确实表现出不同的有效
策略，而具体来源未知。

## 最终判断

本轮已经足够回答最初问题：V4 Pro 正式权重具备接近灰测的能力上限，但这个上限只在
官方 RL 对齐的 minimal 两工具 scaffold 下稳定出现；standard、PTC、OpenCode 和
WorkBuddy 展示的是更接近日常部署的 91–93 档能力。PTC 对照进一步排除了“只要官方
harness 或把工具合成一个入口就能变强”的解释。

因此不建议继续为同一题追加付费运行。更有价值的下一步不是再刷一枪，而是在未来有免费
额度时，用结构不同的第二个工程任务复验 minimal 与通用 harness 的差距，检验这是普遍的
接口依赖，还是 Project2 单题上的 scaffold 适配。
