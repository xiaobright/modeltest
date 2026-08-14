# DeepSeek V4 Pro 正式版：harness 对照分析

**日期：** 2026-08-14

**基准：** Project2 V4.1b（题面、测试与计分规则冻结）

**范围：** DeepSeek V4 Pro 灰测、正式版 OpenCode、DeepSeek Harness（DSH/Fable）以及
DeepSeek V4 Flash 对照

本文只解释本项目内观察到的工程维护表现，不把单项目分数外推为通用模型排名。

## 结论摘要

1. **V4 Pro 正式版具备灰测级能力上限。** DSH minimal + max 两跑为 99/96，均值
   97.5，与 7 月灰测 OpenCode 两跑 99/96 完全相同。
2. **正式版对 agent scaffold 高度敏感。** 同一正式模型在 OpenCode 四跑为
   91/96/91/93，均值 92.75；第四跑还出现约 400k 上下文和大量无效工具探索。
3. **该效应具有 Pro 特异性。** V4 Flash 在四个常规 harness 为 92-95，在 DSH
   standard（Windows）为 90、DSH minimal + max（WSL）为 92，没有获得相同提升。
4. **官方源码为“训练接口对齐”解释提供了直接证据。** minimal 的官方测试明确称其
   发送 “exact RL prompt and schemas”；它固定为一句完整 system prompt 和两个训练对齐
   工具，而不是 standard 的简单精简版。跑分因果仍需消融实验确认。
5. **没有证据证明灰测或正式服务代理了 Claude Fable 5。** 分数和失分指纹相似只能
   说明能力处于相近区间；DSH/Fable 的 harness 名称也不能作为后端身份依据。

## 结果矩阵

| 模型 / 跑法 | n | 单跑 Ability | worst | 均值 | 主要观察 |
|---|---:|---|---:|---:|---|
| V4 Pro 灰测 / OpenCode | 2 | 99, 96 | 96 | **97.5** | 发布前强路由或 checkpoint |
| V4 Pro 正式 / OpenCode | 4 | 91, 96, 91, 93 | 91 | **92.75** | 方差大；`high` 未带来提升 |
| V4 Pro 正式 / DSH minimal + max / WSL | 2 | 99, 96 | 96 | **97.5** | hidden 两跑均 44/45 |
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

### 本轮仍不是 prompt 单变量实验

Windows standard 会使用 `pwsh`，非 Windows standard 使用 `bash`；minimal 则始终使用
持久化 Bash。本次从 Windows standard 移到 WSL minimal，同时改变了 system prompt、工具
schema 与数量、shell、shell 持久性、文件系统 provider、sandbox、工作区说明注入、上下文
压缩和操作系统。因此现有各次分数差异不能归因于某一句 system prompt，也不能仅归因于
Windows 或 Linux。

结合源码与对照结果，当前最可能的影响顺序是：

1. RL 对齐的工具 schema；
2. 两工具带来的决策简化；
3. 工作区说明自动注入及潜在重复阅读；
4. 持久化 Bash 与 Linux 环境；
5. 上下文压缩和工具结果裁剪；
6. 各工具附带的 system prompt 指导；
7. `helpful software engineer assistant` 这句通用 persona。

前三项的先后仍是因果推断，不是消融实验结果；但官方把 minimal 称为 exact RL prompt
and schemas，已经显著加强“训练分布/agent scaffold 对齐”这一总解释。

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

### 1. Max 推理策略或服务路由不同

OpenCode 的 `high` 跑法仍为 91；DSH 使用的是 `max`。二者不能视为同一个档位。
DSH 还可能发送专用请求字段、system prompt 或路由元数据。没有原始请求 JSON、响应头
和服务端 route id 时，无法判断是否命中了不同 checkpoint 或 specialist。

### 2. 后训练与官方 agent scaffold 联合设计

DeepSeek V4 Pro 的公开模型卡描述了领域 specialist 培养和 unified on-policy
distillation。使用固定工具协议和 rollout 环境进行后训练，容易让模型对 system prompt、
工具 schema、上下文压缩和停止策略形成明显依赖。官方测试对 minimal 使用 “exact RL
prompt and schemas” 的措辞，为此提供了直接源码依据。这能解释 Pro 在官方栈中很强、在
通用 harness 中容易偏航，而不需要假设模型记住了本项目。

参考：<https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro>

### 3. minimal 与 Linux 工具链减少了控制干扰

DSH 跑法明确限制可见 workspace，禁止 subagent，并通过固定脚本调用 Linux ESP-IDF
v6.0。它消除了 Windows 正式第四跑里最昂贵的环境逆向路径；两工具 preset 也减少了工具
选择与状态管理负担。不过，Python hidden 的稳定提升无法仅靠 ESP 工具链解释，因此环境
和题面约束都不是唯一因素。

### 4. 发布期间发生额外后训练或蒸馏

“7 月灰测后针对 DSH minimal 继续后训练，导致通用 harness 泛化下降”是合理假设，
但现有证据无法验证时间线。灰测在 7 月已经能通过 OpenCode 得到 99/96，说明高能力并非
8 月才在 minimal 中出现。更保守的解释是：灰测命中了更强策略，正式通用路径未正确
激活，而 DSH minimal + max 恢复了与训练分布匹配的推理策略。

## 能说与不能说

可以说：

- 正式 V4 Pro 在官方对齐栈下可以复现灰测级成绩；
- 官方 minimal preset 明确复刻 RL prompt/schema，V4 Pro 的高分具有训练接口对齐特征；
- V4 Pro 的可用能力比 V4 Flash 更依赖 harness；
- V4 Flash 峰值较低，但跨 harness 鲁棒性和单位成本更好；
- 正式 OpenCode 四跑的 91-96 是真实部署表现，不应被官方配置的高分覆盖。

不能据此说：

- DSH 单独贡献了全部 4.75 分均值差；
- 极简模式的某一句 system prompt 单独造成了增益；
- 灰测就是 Claude Fable 5 或其他闭源模型代理；
- V4 Pro 在所有代码任务上都达到 Fable、Opus 或 Sol 水平；
- 已证明 DeepSeek 在 7 月至 8 月间专门对 minimal preset 过拟合。

## 对照限制与后续验证

当前不是严格单变量实验。OpenCode 到 DSH minimal 同时改变了 harness、preset、
推理档位、system prompt、工具 schema、操作系统、命令后端、文件系统/沙箱策略、上下文
管理和 ESP-IDF 工具链。V4 Flash 对照排除了“所有模型在 Linux minimal 都自然上涨”的
粗解释，但还不能拆开 Pro 的具体增益来源。

若继续验证，最有价值的是在同一 Ubuntu 工作区、同一候选提示词和同一构建脚本上做：

1. DSH standard + max；
2. DSH minimal + 非 max；
3. OpenCode + 与 DSH 完全相同的官方 Max 请求参数；
4. 每格至少三次，并记录请求 JSON、实际 model id、route/request id、上下文峰值、
   工具调用次数和总耗时；
5. 再用第二个结构不同的工程任务复验，区分 scaffold 适配与单题过拟合。

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
- Flash DSH：[20260813_214814 / standard/Windows / 90](../../evaluator/reviews/v4.1b_DeepSeek-V4-Flash_dsh-standard-win32_20260813_214814.md)、
  [20260814_102941 / minimal/WSL / 92](../../evaluator/reviews/v4.1b_DeepSeek-V4-Flash_dsh-minimal-wsl_20260814_102941.md)

每次运行的 `summary.json`、hidden/ESP 摘要、candidate diff、PR 文档与固件产物均位于
`evaluator/results/<result_id>/`，对应人工评审位于 `evaluator/reviews/`。
