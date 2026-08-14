# DeepSeek V4 Pro 正式版：harness 对照分析

**日期：** 2026-08-14

**基准：** Project2 V4.1b（题面、测试与计分规则冻结）

**范围：** DeepSeek V4 Pro 灰测、正式版 OpenCode、DeepSeek Harness（DSH/Fable）以及
DeepSeek V4 Flash 对照，以及 Fable 5、Opus 5、GPT-5.6-sol 顶端参照

本文只解释本项目内观察到的工程维护表现，不把单项目分数外推为通用模型排名。

## 结论摘要

1. **V4 Pro 正式版具备灰测级能力上限。** DSH minimal + max 两跑为 99/96；Windows
   上先以两工具启动、首个工具调用后恢复完整 Standard 目录的 `anchored-standard` 又连续
   得到 **98/99**。它们与灰测 99/96、Fable 5（98）、Opus 5（97）和 Sol（99/98）处于同一分数带。
2. **正式版对 agent scaffold 高度敏感。** 同一正式模型在 OpenCode 四跑为
   91/96/91/93，均值 92.75；第四跑还出现约 400k 上下文和大量无效工具探索。
3. **同环境三 preset 对照已排除 OS 和官方 harness 本身。** 同一 WSL/max 环境中，
   minimal 为 99/96，standard 为 91，PTC 为 92；Linux、DSH 或单一 `run_code` 入口
   都不足以解释高分。Windows 两阶段 98/99 又证明完整工具目录本身不是低分原因，关键在
   首次请求是否先进入 minimal 对齐的策略。
4. **官方源码为“训练接口对齐”解释提供了直接证据。** minimal 的官方测试明确称其
   发送 “exact RL prompt and schemas”；它固定为一句完整 system prompt 和两个训练对齐
   工具，而不是 standard 的简单精简版。跑分因果仍需消融实验确认。
5. **该效应具有 Pro 特异性。** V4 Flash 从 OpenCode 切到 minimal 后思维链风格彻底
   改变，Ability 仍为 92，说明 Flash 的工具策略泛化更稳。
6. **没有证据证明灰测或正式服务代理了 Claude Fable 5。** 分数和失分指纹相似只能
   说明能力处于相近区间；DSH/Fable 的 harness 名称也不能作为后端身份依据。

## 结果矩阵

| 模型 / 跑法 | n | 单跑 Ability | worst | 均值 | 主要观察 |
|---|---:|---|---:|---:|---|
| V4 Pro 灰测 / OpenCode | 2 | 99, 96 | 96 | **97.5** | 发布前强路由或 checkpoint |
| V4 Pro 正式 / OpenCode | 4 | 91, 96, 91, 93 | 91 | **92.75** | 方差大；`high` 未带来提升 |
| V4 Pro 正式 / DSH minimal + max / WSL | 2 | 99, 96 | 96 | **97.5** | hidden 两跑均 44/45 |
| V4 Pro 正式 / DSH standard + max / WSL | 1 | 91 | 91 | 91 | 与 Windows standard 同档 |
| V4 Pro 正式 / DSH PTC + max / WSL | 1 | 92 | 92 | 92 | `run_code` 未恢复 minimal 能力 |
| **V4 Pro 正式 / DSH anchored-standard + max / Windows** | **2** | **98, 99** | **98** | **98.5** | **首轮 2 工具，随后恢复 25 工具** |
| V4 Pro 正式 / WorkBuddy | 1 | 91 | 91 | 91 | 官方渠道仍为常规档 |
| Claude Fable 5 / max / 临时渠道 | 1 | 98 | 98 | 98 | 顶端参考；非主榜正式样本 |
| Claude Opus 5 / max / Claude Code | 1 | 97 | 97 | 97 | 顶端参考；非主榜正式样本 |
| GPT-5.6-sol / Codex high | 2 | 99, 98 | 98 | **98.5** | 正式主榜顶端参照 |
| V4 Flash / OC、Codex、Reasonix、WorkBuddy | 4 | 92, 93, 95, 93 | 92 | **93.25** | 跨 harness 稳定 |
| V4 Flash / DSH standard / Windows | 1 | 90 | 90 | 90 | 官方 harness 无增益 |
| V4 Flash / DSH minimal + max / WSL | 1 | 92 | 92 | 92 | 与 OpenCode 持平 |

DSH 两次 V4 Pro 的 Python hidden 都只错 `V4-F12-04`：无 actor 场景返回
`not_authenticated`，而测试期待 `not_authorized_for_target`。ambient、鉴权、迁移、
CSV 归属、care event 和 voice 显式会话路径连续通过。

第二次 DSH 从 99 降至 96，差异来自 ESP 静态契约：`espressif__mqtt` 组件命名、
`esp_mqtt_client_enqueue` 与测试期待的 `publish` 标记，以及 `wifi_ssid` readiness。
真实 ESP-IDF v6.0 构建仍然成功，因此这 3 分主要反映静态契约符合度；其中
`wifi_ssid` 完整性检查仍可能是实际配置风险，不能一概视为误判。

### 与 Fable、Opus、Sol 的能力参照

Fable 5 单跑 **98**，Opus 5 单跑 **97**，GPT-5.6-sol 两跑 **99/98**。V4 Pro 的
灰测与正式 DSH minimal 都为 **99/96**：best 达到 Sol 的 99，均值 97.5 与 Fable 5
和 Opus 5 落在同一窄区间。更细看，Fable/Opus 都拿到 F3 隐私 16/16、F6 迁移 10/10
和 voice 满分，主要只在 ESP 静态契约丢 1–2 分；V4 Pro minimal 的 Python hidden 也
达到 44/45，首跑 ESP static 9/9 并真实编译通过。

所以，“V4 Pro 确实有 Fable/Opus/Sol 档的工程能力上限”在 **Project2 本题和已测配置**
内有直接分数支持。限制同样明确：Fable/Opus 各只有一次且来自临时渠道，Sol 是不同
harness，V4 Pro 在通用接口下仍只有 91–96。这里比较的是已观测交付结果，不是参数效率、
通用能力或服务端模型身份。

## 官方 harness 源码审计

以下结论基于 `deepseek-ai/deepseek-harness` 的固定提交
[`47f9438`](https://github.com/deepseek-ai/deepseek-harness/tree/47f943859bef60e4160492346772ded9b24f765a)，
避免把后续仓库改动误算进本次实验。

### minimal 是 RL 对齐 preset，不只是更短的 standard

[`minimal/agent.cordis.yml`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/apps/cli/config/agent-presets/minimal/agent.cordis.yml)
把完整 system prompt 固定为 `You are a helpful software engineer assistant.`，设置
`complete: true` 和 `includeRuntimeContext: false`，仅保留持久化 `bash` 与
`str_replace_editor`。它还使用本地文件系统 provider，没有 sandbox mode，也没有上下文
压缩组件。

更关键的证据来自官方
[`minimal-preset.snapshot.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/apps/web/tests/minimal-preset.snapshot.ts#L49)：
测试名称就是 `sends the exact RL prompt and schemas`，快照又确认请求中只有上述一句
prompt 和两个工具。这里的 “RL” 是仓库作者的明文定义，不是根据跑分反推的猜测。

[`system-prompt/src/index.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/packages/core/system-prompt/src/index.ts#L504)
进一步显示，标记为 `complete` 的 section 会成为唯一完整提示，runtime context 也可被
抑制。因此 minimal 会屏蔽 harness 身份、Web 运行提示、各工具指导、sandbox/approval
上下文以及后续注入的 prompt 文本。真正特殊的是整个 prompt/schema 分布，不太可能只是
那句泛化 persona 本身。

### standard 同时扩大了工具与控制面

[`standard/agent.cordis.yml`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/apps/cli/config/agent-presets/standard/agent.cordis.yml)
包含 26 个插件配置项。除 shell、读写编辑、搜索和图片工具外，还挂载后台任务、skills、
goals、plan mode、compaction、subagent、workflow、ask-user、todo 和 web search 等能力。
模型不只要解决工程问题，还要在约 25 个 Linux 工具中持续选择和管理状态；minimal 则
把决策面压缩为两个训练时 schema。

standard 还会以最多 65536 字节自动加载工作区说明。其
[`agent-instructions` 默认配置](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/packages/context/agent-instructions/src/config.ts#L11)
会发现 `AGENTS.md`、`CLAUDE.md` 及 local overlay。本项目题面又明确要求模型自行阅读
`AGENTS.md`，所以 standard 可能先自动接收一次、随后再手动读取一次；minimal 没有该插件，
只会按题面读取。这是解释重复阅读和上下文膨胀的一个具体机制。

standard 的
[`read` 工具提示](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/packages/fs/tool-fs/src/read.ts#L70)
要求不用 shell、改用带 `offset`/`limit` 的分段读取。在仓库级任务中，这可能诱发更多串行
读取。其 compaction 又会在工具结果超过 8192 字符时只保留 4096 字符开头和 1024 字符
结尾；ESP-IDF 的关键错误若位于中段，模型可能再次搜索或重跑构建。minimal 没有这套压缩。
这些机制与第四次 OpenCode 的偏航模式方向一致，但没有逐调用轨迹对照，不能断言它们就是
该次偏航的唯一原因。

### PTC 是 standard 的 Code Mode 呈现，不是 exact-RL preset

官方内置 `code` preset（界面名 PTC）声明“具备标准模式的全部能力”，其
`agent.cordis.yml` 与 standard 保持同一工具和控制面，只增加
`tool-presentation: mode: code`。模型在 wire 上只看到 `run_code`，再通过生成的
TypeScript SDK 调用原有工具。官方源码并未把 PTC 称为 exact RL 配置；这一措辞只出现
在 minimal 的快照测试中。

本次 PTC 有 164 次外层 `run_code` 和 187 次内层工具调用。122 个成功程序只包装一次
子调用，只有 29 个程序实际包含 2–4 个子调用，`Promise.all` 为 0；另有 10 次缺少必填
`description` 和 3 次 TypeScript 执行失败。PTC 用时约 25.95 分钟，standard 约 24.08
分钟，既未批量化主要操作，也未带来时间或分数收益。这说明单一工具入口不是 minimal
增益的充分条件。

### 同 WSL/max 对照关闭了主要混杂项

早期 Windows standard 与 WSL minimal 同时改变了多个变量，不能单独归因。现在已有同一
Ubuntu 24.04、同一候选提示词、同一 max 档位和构建脚本下的 standard 91、PTC 92 与
minimal 99/96。这个对照足以排除“Linux 自然涨分”和“官方 DSH 自然涨分”，也说明扩大
工具能力或套一层 Code Mode 不能替代 minimal。仍未拆开的变量是 minimal 内部的完整
prompt、两工具 schema、持久 shell、本地文件系统、无 compaction 等组合，不能把增益归于
某一句 system prompt。

### Windows 两阶段实验定位到首次请求

实验 preset `anchored-standard` 保留 minimal 的完整 system prompt，并让第一次请求只
暴露 `pwsh/read`；首个工具调用后，同一 session 的后续请求恢复 Standard 的 25 项工具。
导出日志中确实只有两次工具目录快照，分别为 2 项和 25 项，随后模型正常使用
`edit/glob/grep/pwsh/read/todo_write/write`，没有牺牲标准模式的实际能力。

第一轮首块 reasoning 以 `We need` 起步；工具目录扩展后的第一块出现全程唯一一次
`Let me`，之后不再出现。第二轮从头到尾 `let me=0`。两轮分别为 `we=179/165`、
`let's=88/98`，过程可见回复都只有最终 1 次，最终得到 **98/99**。相比之下，standard
为 `let me=208`、55 次阶段回复和 91 分。这个对照说明关键不是让整个任务永远停留在
两工具环境，而是用训练对齐的首次请求确定会话轨迹。

结合源码与对照结果，当前最可能的影响顺序是：

1. 首次请求中的 RL 对齐 prompt 与工具 schema；
2. 两工具启动带来的初始策略选择；
3. 工作区说明自动注入及潜在重复阅读；
4. 后续工具指导与目录扩展方式；
5. 上下文压缩和工具结果裁剪；
6. 各工具附带的 system prompt 指导；
7. `helpful software engineer assistant` 这句通用 persona。

前三项的先后仍是因果推断，不是逐项消融结果；但 standard/PTC 的同环境低分和官方
“exact RL prompt and schemas”措辞，已经显著加强“训练分布/agent scaffold 对齐”这一
总解释。两阶段 98/99 已把“必须全程保持两工具”与“必须使用 Linux/Bash”的解释显著降权。

## 对第四次 OpenCode 正式跑的重新定性

`20260813_203311` 的 93 分不是四次正式跑中的最低分，但它是执行效率最差的一次：

- 上下文峰值约 400k；
- 缓存命中累计约 6395 万 token；
- 约 45 分钟，费用约 $0.46；
- 多轮逆向 ESP-IDF 组件管理器、五次全量构建；
- 自建验证脚本又因 SQLite 句柄、时间戳和补丁问题反复修正。

因此它不能代表 V4 Pro 的能力上限，却能代表正式模型在非原生 scaffold 下的真实
产品风险：搜索范围失控、缺少停止条件、验证预算管理差。官方 harness 把成绩拉回
99/96，并不能消除这类部署鲁棒性问题。

## 最可能的解释

### 1. minimal 激活了不同的有效推理策略

OpenCode 的 `high` 跑法仍为 91，但 DSH standard/PTC 在 `max` 下也只有 91/92，所以
`max` 档位本身不是充分解释。minimal 的首次 prompt/schema 会激活训练分布内的工具策略；
两阶段实验显示这种策略能在后续完整工具目录下持续。它也可能伴随专用路由元数据。没有
服务端 route id 和 checkpoint 信息，仍无法区分“同一权重的策略激活”与“请求命中
specialist”；客户端证据能确认的是首次请求结构依赖。

### 2. 后训练与官方 agent scaffold 联合设计

DeepSeek V4 Pro 的公开模型卡描述了领域 specialist 培养和 unified on-policy
distillation。使用固定工具协议和 rollout 环境进行后训练，容易让模型对 system prompt、
工具 schema、上下文压缩和停止策略形成明显依赖。官方测试对 minimal 使用 “exact RL
prompt and schemas” 的措辞，为此提供了直接源码依据。这能解释 Pro 在官方栈中很强、在
通用 harness 中容易偏航，而不需要假设模型记住了本项目。

参考：<https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro>

### 3. minimal 减少了控制干扰，Linux 不是主因

DSH 跑法明确限制可见 workspace，禁止 subagent，并通过固定脚本调用 Linux ESP-IDF
v6.0。它消除了 Windows 正式第四跑里最昂贵的环境逆向路径；两工具 preset 也减少了工具
选择与状态管理负担。standard/PTC 在同一 Linux 环境仍为 91/92，排除了 Linux 本身；
Python hidden 的稳定提升也无法仅靠 ESP 工具链解释。

### 4. 发布期间发生额外后训练或蒸馏

“7 月灰测后针对 DSH minimal 继续后训练，导致通用 harness 泛化下降”是合理假设，
但现有证据无法验证时间线。灰测在 7 月已经能通过 OpenCode 得到 99/96，说明高能力并非
8 月才在 minimal 中出现。更保守的解释是：灰测命中了更强策略，正式通用路径未正确
激活，而 DSH minimal + max 恢复了与训练分布匹配的推理策略。

## 能说与不能说

可以说：

- 正式 V4 Pro 在 minimal 及两阶段锚定栈下可以复现灰测级成绩；
- 在 Project2 上，V4 Pro minimal/灰测的 99/96 与 Fable 5、Opus 5、Sol 同属顶端分数带；
- 官方 minimal preset 明确复刻 RL prompt/schema，V4 Pro 的高分具有训练接口对齐特征；
- standard/PTC 与 Windows 两阶段对照把增益进一步定位到首次请求的 minimal 组合，而非
  Linux、DSH、`run_code` 或全程限制工具数量；
- V4 Pro 的可用能力比 V4 Flash 更依赖 harness；
- V4 Flash 峰值较低，但跨 harness 鲁棒性和单位成本更好；
- 正式 OpenCode 四跑的 91-96 是真实部署表现，不应被官方配置的高分覆盖。

不能据此说：

- DSH 单独贡献了全部 4.75 分均值差；
- 极简模式的某一句 system prompt 单独造成了增益；
- 灰测就是 Claude Fable 5 或其他闭源模型代理；
- V4 Pro 在所有代码任务上都达到 Fable、Opus 或 Sol 水平；
- 已证明 DeepSeek 在 7 月至 8 月间专门对 minimal preset 过拟合。

## 对照限制与停止条件

当前仍未拆开首次 system prompt 与两工具 schema 各自的贡献。但同 WSL/max 的
standard/PTC 对照已关闭 OS、官方 harness 和推理档位三个主要混杂项；Windows 两阶段又
证明后续完整工具目录可以兼容高分轨迹；V4 Flash 则证明风格变化本身不等于 Ability 提升。
现有证据已经足够回答本轮关于正式 V4 Pro 的核心问题。

不建议继续在 Project2 上付费刷同配置。未来若有免费额度，真正有信息增量的实验只有：

1. 用结构不同的第二个工程任务复验 minimal 与 standard；
2. 或取得服务端 route/request id 后复验灰测与正式路径；
3. 若做消融，应在同一 DSH 版本中逐项替换 prompt、schema 和 compaction，而不是再换 harness。

目前最稳妥的总表述是：**V4 Pro 在官方 RL 对齐的两工具 scaffold 下接近灰测表现，但在
更宽的 agent 接口下明显退化，说明它具备较高能力上限，同时存在强接口依赖和较弱的工具
策略泛化。**

## 证据索引

- 灰测：[20260718_212524 / 99](../../evaluator/reviews/v4.1b_DeepSeek-V4-Pro_opencode_20260718_212524.md)、
  [20260719_095847 / 96](../../evaluator/reviews/v4.1b_DeepSeek-V4-Pro_opencode_20260719_095847.md)
- 正式 OpenCode：[20260813_005050 / 91](../../evaluator/reviews/v4.1b_DeepSeek-V4-Pro_opencode-formal_20260813_005050.md)、
  [20260813_012129 / 96](../../evaluator/reviews/v4.1b_DeepSeek-V4-Pro_opencode-formal_20260813_012129.md)、
  [20260813_102813 / 91](../../evaluator/reviews/v4.1b_DeepSeek-V4-Pro_opencode-formal-high_20260813_102813.md)、
  [20260813_203311 / 93](../../evaluator/reviews/v4.1b_DeepSeek-V4-Pro_opencode-formal_20260813_203311.md)
- 正式 DSH minimal + max：[20260813_230337 / 99](../../evaluator/reviews/v4.1b_DeepSeek-V4-Pro_dsh-minimal-wsl_20260813_230337.md)、
  [20260814_095712 / 96](../../evaluator/reviews/v4.1b_DeepSeek-V4-Pro_dsh-minimal-wsl_20260814_095712.md)
- 正式 DSH 对照：[standard/WSL / 91](../../evaluator/reviews/v4.1b_DeepSeek-V4-Pro_dsh-standard-wsl_20260814_133328.md)、
  [PTC/WSL / 92](../../evaluator/reviews/v4.1b_DeepSeek-V4-Pro_dsh-ptc-wsl_20260814_140756.md)
- 正式 WorkBuddy：[20260814_124554 / 91](../../evaluator/reviews/v4.1b_DeepSeek-V4-Pro_workbuddy_20260814_124554.md)
- Flash DSH：[20260813_214814 / standard/Windows / 90](../../evaluator/reviews/v4.1b_DeepSeek-V4-Flash_dsh-standard-win32_20260813_214814.md)、
  [20260814_102941 / minimal/WSL / 92](../../evaluator/reviews/v4.1b_DeepSeek-V4-Flash_dsh-minimal-wsl_20260814_102941.md)
- 轨迹风格、PTC 调用结构和公开统计方法：
  [`DEEPSEEK_V4_TRAJECTORY_ANALYSIS_20260814.md`](./DEEPSEEK_V4_TRAJECTORY_ANALYSIS_20260814.md)
- 顶端参照：[Fable 5 / 98](../../evaluator/reviews/v4.1b_Claude-Fable-5_third-party_20260726_172943.md)、
  [Opus 5 / 97](../../evaluator/reviews/v4.1b_Claude-Opus-5_claude-code_20260726_200256.md)、
  [Sol run1 / 99](../../evaluator/reviews/v4.1b_GPT-5.6-sol_codex-high_20260718_201302.md)、
  [Sol run2 / 98](../../evaluator/reviews/v4.1b_GPT-5.6-sol_codex-high_20260719_102931.md)

每次运行的 `summary.json`、hidden/ESP 摘要、candidate diff、PR 文档与固件产物均位于
`evaluator/results/<result_id>/`，对应人工评审位于 `evaluator/reviews/`。
