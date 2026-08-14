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
4. **当前证据支持“模型与官方 harness/推理策略强耦合”，但不能证明具体原因。**
   Max 路由、system prompt、工具协议、Linux 环境和发布后的后训练都可能参与。
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
工具 schema、上下文压缩和停止策略形成明显依赖。这能解释 Pro 在官方栈中很强、在通用
harness 中容易偏航，而不需要假设模型记住了本项目。

参考：<https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro>

### 3. minimal 与 Linux 工具链减少了控制干扰

DSH 跑法明确限制可见 workspace，禁止 subagent，并通过固定脚本调用 Linux ESP-IDF
v6.0。它消除了 Windows 正式第四跑里最昂贵的环境逆向路径。不过，Python hidden 的
稳定提升无法仅靠 ESP 工具链解释，因此环境不是唯一因素。

### 4. 发布期间发生额外后训练或蒸馏

“7 月灰测后针对 DSH minimal 继续后训练，导致通用 harness 泛化下降”是合理假设，
但现有证据无法验证时间线。灰测在 7 月已经能通过 OpenCode 得到 99/96，说明高能力并非
8 月才在 minimal 中出现。更保守的解释是：灰测命中了更强策略，正式通用路径未正确
激活，而 DSH minimal + max 恢复了与训练分布匹配的推理策略。

## 能说与不能说

可以说：

- 正式 V4 Pro 在官方对齐栈下可以复现灰测级成绩；
- V4 Pro 的可用能力比 V4 Flash 更依赖 harness；
- V4 Flash 峰值较低，但跨 harness 鲁棒性和单位成本更好；
- 正式 OpenCode 四跑的 91-96 是真实部署表现，不应被官方配置的高分覆盖。

不能据此说：

- DSH 单独贡献了全部 4.75 分均值差；
- 灰测就是 Claude Fable 5 或其他闭源模型代理；
- V4 Pro 在所有代码任务上都达到 Fable、Opus 或 Sol 水平；
- 已证明 DeepSeek 在 7 月至 8 月间专门对 minimal preset 过拟合。

## 对照限制与后续验证

当前不是严格单变量实验。OpenCode 到 DSH minimal 同时改变了 harness、preset、
推理档位、操作系统、命令后端和 ESP-IDF 工具链。V4 Flash 对照排除了“所有模型在
Linux minimal 都自然上涨”的粗解释，但还不能拆开 Pro 的具体增益来源。

若继续验证，最有价值的是在同一 Ubuntu 工作区、同一候选提示词和同一构建脚本上做：

1. DSH standard + max；
2. DSH minimal + 非 max；
3. OpenCode + 与 DSH 完全相同的官方 Max 请求参数；
4. 每格至少三次，并记录请求 JSON、实际 model id、route/request id、上下文峰值、
   工具调用次数和总耗时；
5. 再用第二个结构不同的工程任务复验，区分 scaffold 适配与单题过拟合。

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
