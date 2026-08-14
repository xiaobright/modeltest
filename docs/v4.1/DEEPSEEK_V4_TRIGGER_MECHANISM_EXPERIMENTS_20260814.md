# DeepSeek V4 Pro / Flash 轨迹触发机制实验

**日期：** 2026-08-14

**范围：** Chat Completions 首轮微探针、DSH session 对照、Project2 完整评测

**复现材料：** [`../../evaluator/trigger_probe/`](../../evaluator/trigger_probe/README.md)

## 省流结论

1. **Flash 和 Pro 不能用同一个触发器解释。** Flash 的 `We need` 型轨迹主要跟随
   minimal software-engineer system persona；Pro 除了 system prompt，还明显受首轮
   API 可见工具目录影响。
2. **Pro 的关键变量是“第一次看见什么工具”，不是全程只能用两个工具。** 首轮以
   minimal prompt 和两工具建立轨迹，首个工具调用后恢复 Standard 25 工具，模型仍能
   正常使用完整目录，并在 Project2 连续得到 **98/99**。
3. **思维链措辞是轨迹指纹，不是能力证明。** Flash 换成 minimal 后风格巨变，完整任务
   仍是 92；Pro 的高分则同时满足轨迹锚定和正确交付。不能用单个 `Good`、`We` 或
   `Let me` 判断模型身份、路由或分数。
4. 现有结果支持“请求 scaffold 选择了不同的有效策略区域”，但不能区分同一 checkpoint
   的条件化行为、后训练形成的策略分支或服务端内容路由。

## 问题与方法

完整 Project2 运行价格较高，先用固定的仓库检查任务做单轮微探针，只改变一个请求因素：

- system persona；
- harness HTTP header；
- API 可见工具 schema 与工具子集；
- 将指导或工具目录放入 user message / tool result；
- 首轮两工具、次轮完整工具的动态晋升。

所有微探针都在第一个或前几个工具调用处停止。它们只用于辨认轨迹条件，不能代替完整
工程评测。最终因果链由两次完整 Project2 运行验证。

## 保守分类器

公开探针使用词法分类器：首行 `We need`、全文 `we` 且没有 `let me` 增加
`minimal-like` 分；首行或全文 `let me` 增加 `standard-like` 分；其余为 `ambiguous`。

`ambiguous` 不表示没有变化。例如晋升后的 Pro 常以 `Need ...` 开头且没有 `let me`，
词法分类器仍保守记为 ambiguous。报告同时查看开头模式、`let me`/`we` 计数、工具合法性
与完整任务评分，不把分类器标签当内部路由真值。

## Flash：system persona 是主导变量

固定同一微任务和两工具时：

| 改动 | 结果 |
|---|---|
| minimal persona，重复 3 次 | 3/3 `minimal-like`，均以 `We need` 起步 |
| 删除 DSH 专用 HTTP headers | `minimal-like` |
| 改名 `str_replace_editor` | `minimal-like` |
| persona 语义改写 | 2 次 `standard-like`、1 次 ambiguous |
| minimal system + Standard 25 工具 | `minimal-like` |
| Standard system + minimal 两工具 | 非 minimal |
| minimal system，Standard 指导移入 user | `minimal-like`，能合法调用 Standard 工具 |
| minimal system，PTC SDK 指导移入 user | `minimal-like`，能合法调用 `run_code` |

因此对 Flash，header 和精确字节串都不是必要条件；完整 Standard 工具目录也不是阻断项。
但在完整 Project2 上，OpenCode 与 DSH minimal 都是 **92**。这证明风格切换本身不是能力
提升的充分条件，也说明 Flash 对不同 harness 的能力泛化比 Pro 稳定。

## Pro：首轮工具目录会改变轨迹

同样的 minimal system 与微任务，在 Pro 上得到不同结果：

| API 可见工具 | 开头/分类 | 观察 |
|---|---|---|
| minimal `bash + editor` | `We need` / minimal-like | minimal 基线 |
| Standard 25 工具 | `The user wants ... Let me ...` / 非 minimal | persona 不足以压住完整目录 |
| Standard `bash` | `We need` / minimal-like | 单工具保留 |
| Standard `bash + read` | `We need` / minimal-like | 两工具保留 |
| Standard `bash + glob` | `The user wants ... Let me ...` / 非 minimal | `glob` 是已观测分界之一 |
| Standard `bash + edit` | `We need` / minimal-like | 不是“工具数 > 1”规则 |
| Standard `bash + write` | `We need` / minimal-like | 同上 |
| PTC `run_code` | `Let me` / standard-like | 单一入口也不会自动触发 |

把完整 Standard catalog 仅作为 user 内容或 tool result 文字提供，而 API 层仍只暴露 minimal
工具时，轨迹仍保持 `We/Need`；这说明影响来自模型实际可调用的 schema surface，不是看见
一段工具名称文本。`reasoning_effort=high` 也未让完整 Standard 目录恢复 minimal 风格。

这里不能推导出 `glob` 是秘密开关：它可能只是工具组合、描述、顺序或训练分布的代理变量。
更窄的 schema 字段消融尚未做，也没有必要继续为同一题烧钱。

## 决定性实验：动态工具晋升

两阶段微探针保持同一 session 与历史：

1. turn 1：minimal system，只暴露两工具，首块为 `We need`；
2. turn 2：恢复完整 Standard 25 工具，开头变为 `Need ...`，无持续 `Let me`，并合法调用
   `bash/read`；
3. turn 3：仍是完整目录，继续合法调用 `read`，没有回到 Standard 的高频 `Let me` 轨迹。

这给出了 `anchored-standard` 的实现：**先用训练对齐的窄工具面选择初始策略，第一次工具
调用后立即恢复完整能力。** 它不需要把 Standard 说明伪装成 system prompt 文件，也不需要
永远限制工具。

## 完整 Project2 验证

| 配置 | 环境 | Ability | 轨迹摘要 |
|---|---|---:|---|
| DSH standard / max | WSL | 91 | 99 reasoning blocks，`let me=208` |
| DSH PTC / max | WSL | 92 | Code Mode 未形成有效批处理 |
| DSH minimal / max | WSL | 99, 96 | minimal-like，高分但只有两工具 |
| DSH anchored-standard / max | Windows | **98, 99** | 355 blocks 合计仅 1 个 `let me`；完整 25 工具可用 |

两次 anchored-standard 使用同一题面，均值 98.5、worst 98。第二轮真实 ESP-IDF 编译
成功，安全边界也通过，只丢一个 context reason 语义字符串。它足以反驳“98 只是一次抽卡”
和“高分必须全程两工具”，但 **n=2 同题复现不能证明跨任务普适提升**。

## 已证明与未证明

现有证据支持：

- 正式 V4 Pro 在本题上确实具备接近灰测、Fable 5、Opus 5 与 Sol 分数带的可访问能力；
- Pro 的首轮 model-visible prompt + tool schema 会显著影响后续轨迹；
- 首轮锚定后可以恢复完整 Standard 工具，而不立刻丢失轨迹；
- Flash 与 Pro 的条件敏感性不同，不能从 Flash 探针直接外推 Pro。

现有证据不支持：

- 用措辞判定后端就是 Claude、Fable 或某个泄露 checkpoint；
- 声称存在一个确定的服务端“特殊路由标识”；
- 声称 `We need`、`Good` 或低阶段回复本身导致高分；
- 声称 98/99 会在其他仓库、任务长度或 provider 上稳定复现。

## 发布与证据边界

原始 JSON/session 含完整 reasoning、system prompt、工具结果、绝对路径和可能的环境信息，
仅本地保留。公开仓库提供：

- 原始文件 SHA-256，证明派生结论对应的本地证据未被替换；
- 不含 reasoning 原文的实验矩阵；
- 分类器和通用 Chat Completions 微探针；
- 完整运行的聚合轨迹统计与评审结果。

探针默认 dry-run；真实请求必须显式传 `--run`。不建议再对同一 Project2 追加付费重复，
下一次有价值的实验应是结构不同的新仓库，用于检验跨题泛化。
