# DeepSeek V4 Pro 首请求工具目录锚定：独立复现与 full-task 消融

**日期：** 2026-08-15 · **独立复现者：** [@NineThoughts0521](https://github.com/NineThoughts0521) · **上游目标：** `xiaobright/modeltest`

**统计边界：** 本报告是第三方独立证据；下列 runs 不并入维护者原有 formal `n`、主榜排名、worst、均值或样本索引。

## 摘要

在固定 Project2 V4.1b、DeepSeek V4 Pro、reasoning `max` 和 DSH `0.1.0-rc.6` 下，本轮依次运行 Anchored Standard、Standard 与新增的 Minimal-Full。三枪 Ability 分别为 **96、89、85.5**。同一次静态 schema gate 证明 Minimal-Full 与 Anchored 的 Minimal complete system condition 和首请求非工具字段相同，Minimal-Full 从 request 1 起暴露完整 25 项 Standard 工具，而 Anchored 首请求仅暴露 `pwsh/read`，首次 durable tool call 后恢复相同的完整目录。

这组单次观测 **supports** 首请求工具目录与 Project2 表现之间存在独立关联，并与维护者原有 Anchored Standard 高于 Standard 的方向 **consistent with**。它没有证明普适因果：每个条件只有一枪，全部使用同一题面，且 Anchored treatment 同时包含窄首请求与随后目录 transition 的时序。外部 benchmark 未在本阶段执行，因此跨任务迁移仍未得到验证。

## 与维护者结果的边界

维护者原报告中的 DSH Anchored Standard `98/99`、Minimal `99/96`、Standard `91` 和其他 DeepSeek 样本保持原统计口径。本轮 Anchored `96` 是 [@NineThoughts0521](https://github.com/NineThoughts0521) 在独立环境中的单次复现，不追加到原 `n=2`，也不改变 scoreboard 的 worst、均值或排名。

独立 Anchored 分数低于维护者两枪，但相对同一独立批次 Standard 的差值为 `+7`，方向与维护者原观察一致。该关系比跨操作者直接比较绝对分数更有信息量，但仍只适用于当前 frozen task 和运行条件。

## 固定条件

| 项目 | 固定值 |
|---|---|
| modeltest base | `04255b55f16c4439e538239fb9783070c4165081` |
| benchmark / task | `project2-v4.1b` / `project2-v4-broken-seed` |
| candidate prompt SHA-256 | `576103f9a5a7a619c0669674cf384a975b89390bb034c368a53a148251f2df84` |
| model / provider | `deepseek-v4-pro` / `deepseek-official` |
| reasoning | `max` |
| DSH | `0.1.0-rc.6` / source commit `47f943859bef60e4160492346772ded9b24f765a` |
| endpoint | `https://api.deepseek.com` |
| evaluator | 原 V4.1b public/debug/hidden/ESP static/scorer；未运行 optional real ESP-IDF build |
| execution | 串行、每枪前 reset、结果无关重跑禁止 |

正式顺序为 Anchored Standard、Standard、Minimal-Full。OpenCode comparison 只在三枪 DSH 完成后运行，并明确排除在 DSH mechanism ablation 之外。

## Project2 3+1 结果

| Harness / preset | Ability | Ship | Class | Hidden | ESP static | F9 | 账户成本 | model wall time |
|---|---:|---:|---|---|---|---|---:|---:|
| DSH Anchored Standard | **96** | 96 | A | 44/45 | 9/9 | 3/6 `skipped_env` | ¥2.58 | 35m41s |
| DSH Standard | **89** | 89 | B+ | 43/45 | 7/9 | 3/6 `skipped_env` | ¥1.64 | 27m33s |
| DSH Minimal-Full | **85.5** | 85.5 | B+ | 42/45 | 6/9 | 3/6 `skipped_env` | ¥1.13 | 11m45s |
| OpenCode 1.18.17 replacement | **93** | 93 | B+ | 43/45 | 8/9 | 3/6 `skipped_env` | ¥1.53 | 21m33s |

四个有效 run 的账户成本为 ¥6.88；保留但不计分的 OpenCode partial 另消耗 ¥0.24，因此本阶段总账户成本为 **¥7.12**。按每枪运行时官方人民币单价复算的总 usage 成本为 **¥7.075304**。详细 token、balance window 和复算差异见实验目录的 machine-readable aggregate。

## Minimal-Full 消融

Minimal-Full 复制 Anchored Standard 的 Minimal complete system condition、`complete: true`、`includeRuntimeContext: false` 与 Standard capability roster，仅移除 `tool-bootstrap`。零费用 mock gate 得到以下断言：

| 断言 | 结果 |
|---|---|
| Minimal-Full request 1 工具 schema = Standard request 1 | pass |
| Minimal-Full request 1 工具 schema = Anchored request 2 | pass |
| Minimal-Full system = Anchored system | pass |
| Minimal-Full 与 Anchored request 1 非工具字段相同 | pass |
| Anchored request 1 仅 `pwsh/read` | pass |
| Anchored request 2 恢复完整 25 项目录 | pass |

Standard 到 Minimal-Full 的 Ability 变化为 `-3.5`，Minimal-Full 到 Anchored 为 `+10.5`，Standard 到 Anchored 为 `+7`。在这一次任务上，Minimal complete scaffold 本身没有解释 Anchored 的提升；观察结果 **supports** first-request tool-schema anchoring 具有独立贡献的解释。

该 A/B 的模型可见首请求差异经过 hash gate 收窄到工具目录，但 treatment 不只是“工具数量”这个静态变量，还包括 Anchored 在首次 durable tool call 后发生的目录 transition 及其时序。当前证据没有进一步拆分工具名称、描述、顺序或 transition 边界，也没有提供多 seed 方差估计。

## Trajectory fingerprints

| Harness / preset | Ability | reasoning blocks | `we` | `let me` | `let's` | visible replies | tool calls |
|---|---:|---:|---:|---:|---:|---:|---:|
| DSH Anchored Standard | 96 | 191 | 324 | 31 | 167 | 1 | 244 |
| DSH Standard | 89 | 88 | 25 | 149 | 2 | 41 | 166 |
| DSH Minimal-Full | 85.5 | 47 | 67 | 14 | 16 | 8 | 83 |
| OpenCode replacement | 93 | 65 | 22 | 119 | 3 | 35 | 152 |

这些统计只作为行为指纹。Anchored 的 `we`/`let's` 增多、可见阶段回复减少，与维护者报告的 minimal-like 方向 consistent with；但本批次 Minimal-Full 也有较少 `let me` 而得分最低，进一步说明措辞风格不是能力指标，也不是因果证据。

## OpenCode partial 与 replacement

最初的 `P2-20260815-04-opencode` 在模型已响应且进程仍活动时受到外层 hosting tool session 中断。该 run 永久登记为 `infrastructure_failed_partial_after_model_response`，不计 benchmark score，不从中恢复继续执行，也不因结果重跑；¥0.24 计入总成本。private export 含 11 个 reasoning blocks 和 22 个 tool calls，event stream 记录 23 个 completed tool events 并留下 pending final tool，两种计数按来源分别保留。

经操作者明确批准后执行一次 `P2-20260815-04b-opencode-replacement`。replacement 固定 OpenCode `1.18.17` commit `02546dfc2e4515a4f90aaf9ceb3890df2ac2b479`、direct DeepSeek provider、`deepseek-v4-pro`、`--variant max`、官方 endpoint、同一 prompt/evaluator；只把进程改为 detached/background 生命周期。它以 exit `0` 完成并得到 `93/93/B+`，无论该结果高低都未再运行。该行只用于 exploratory harness comparison，不进入前三枪因果消融。

## 证据与隐私

公开目录包含 preregistration、run matrix、preset/config、schema gate、原 evaluator 派生结果、trajectory aggregate、token/time/cost aggregate、balance window hash、request tool-catalog snapshot、infrastructure event 和 SHA-256 manifest。完整 DSH session JSONL、OpenCode export/event stream、reasoning/CoT、credentials 与私人绝对路径保留在本地且由 Git ignore。

主要入口：

- [实验 README](../../experiments/deepseek-v4-pro-anchoring/README.md)
- [完整结果表](../../experiments/deepseek-v4-pro-anchoring/RESULTS.md)
- [machine-readable comparison](../../experiments/deepseek-v4-pro-anchoring/artifacts/comparison.json)
- [public/private evidence SHA-256 manifest](../../experiments/deepseek-v4-pro-anchoring/artifacts/evidence-manifest.json)
- [Minimal-Full preset](../../tools/deepseek-harness-presets/minimal-full/agent.cordis.yml)

## 限制

- 每个有效条件只有一枪，不能据此估计方差或统计显著性。
- 全部能力结果来自同一个 Project2 task；DeepSWE 与 Terminal-Bench 未运行，跨任务问题仍开放。
- 运行按预注册顺序串行执行，不能完全排除时间漂移、provider 负载或顺序效应。
- Project2 未运行 optional real ESP-IDF build，所有行 F9 均为 `3/6 skipped_env`。
- OpenCode 工具目录证据来自 pinned static agent resolution，不是 HTTP wire capture。
- balance delta 与 usage 复算保留各自语义，未把差异静默分配给任一请求。

因此，本轮最克制的结论是：**独立 Project2 结果 supports first-request tool-schema anchoring 具有额外贡献，并与维护者原 Anchored 优于 Standard 的方向 consistent with；它尚未证明该效应能跨任务、跨版本或跨 provider 普适复现。**
