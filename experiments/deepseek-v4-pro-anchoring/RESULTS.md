# Project2 3+1 结果

**独立复现者：** [@NineThoughts0521](https://github.com/NineThoughts0521)  
**统计边界：** 以下 runs 是第三方独立证据，不并入 `xiaobright/modeltest` 维护者原有 formal `n`、排名、worst、均值或样本索引。

本轮在同一 frozen Project2 V4.1b task `project2-v4-broken-seed`、同一 `CANDIDATE_PROMPT.md` 和同一 evaluator 下完成三枪 DSH 机制消融，并完成一枪经批准的 OpenCode exploratory replacement。模型为 DeepSeek V4 Pro，reasoning effort 为 `max`，价格按每枪运行时官方人民币单价记录，未使用峰谷价假设。

## 统一对比

| Harness/Preset | Ability | Ship | Class | Hidden | ESP static | F9 | reasoning_blocks | we | let_me | lets | visible replies | tool calls / distinct | miss/read/output/reasoning tokens | cost balance / usage | wall time |
|---|---:|---:|---|---|---|---|---:|---:|---:|---:|---:|---|---|---|---|
| DSH Anchored Standard | 96 | 96 | A | 44/45 | 9/9 | 3/6 skipped_env | 191 | 324 | 31 | 167 | 1 | 244 / 7 | 197,639 / 43,833,728 / 139,830 / 60,977 | ¥2.58 / ¥2.527740 | 35m41s |
| DSH Standard | 89 | 89 | B+ | 43/45 | 7/9 | 3/6 skipped_env | 88 | 25 | 149 | 2 | 41 | 166 / 7 | 154,935 / 24,029,312 / 115,229 / 39,156 | ¥1.64 / ¥1.756912 | 27m33s |
| DSH Minimal-Full | 85.5 | 85.5 | B+ | 42/45 | 6/9 | 3/6 skipped_env | 47 | 67 | 14 | 16 | 8 | 83 / 6 | 166,004 / 6,870,528 / 44,058 / 16,822 | ¥1.13 / ¥0.934123 | 11m45s |
| OpenCode 1.18.17 replacement | 93 | 93 | B+ | 43/45 | 8/9 | 3/6 skipped_env | 65 | 22 | 119 | 3 | 35 | 152 / 7 | 170,382 / 21,949,696 / 64,000 / 32,269 | ¥1.53 / ¥1.637502 | 21m33s |

Token 列依次为 `cache-miss input / cache-read input / non-reasoning output / reasoning output`；DSH 和 OpenCode usage 字段保留各自原生的互斥计数语义。`let_me` 为绝对数量。措辞指纹不作为能力指标。

首请求工具目录证据为：Anchored 首次仅有 `2` 个工具（`pwsh`、`read`），随后恢复完整 Standard 目录；Standard 从 request 1 起有 `25` 个工具；Minimal-Full 从 request 1 起有 `25` 个工具；OpenCode 从 request 1 起静态解析出 `12` 个工具且没有 anchoring transition。OpenCode 的目录证据来自静态 agent resolution，不是原始 HTTP wire capture。

## 结论

1. 当前环境复现了 Standard 到 Anchored 的正向 Project2 差异，Ability 从 `89` 升至 `96`，差值为 `+7`。这只是同一 frozen task 的单次观测，不构成统计显著性证据。
2. Standard 到 Minimal-Full 为 `-3.5` Ability，Minimal-Full 到 Anchored 为 `+10.5`。schema gate 证明 Anchored 与 Minimal-Full 的 system 和首请求非工具字段 hash 相等，transition 后的工具 schema 与 Standard 相等。这支持该任务上的 first-request catalog 关联，但 treatment 仍同时包含从窄目录恢复到完整目录的时序和状态转移，未单独隔离 transition 的每个实现细节。
3. OpenCode 得分为 `93`，位于 Standard 与 Anchored 之间，但它是 post-preregistered exploratory harness comparison，不进入任何 DSH mechanism ablation 结论。它在 system scaffold、权限/工具目录和 runtime 上均有差异，因此不能解释为纯 harness 因果效应。
4. 本阶段未运行外部 benchmark。Anchored 差异能否离开 Project2 延续，仍需后续单独通过 gate 的 DeepSWE pair 回答。Terminal-Bench 继续 deferred。

## OpenCode Replacement 边界

`P2-20260815-04-opencode` 永久登记为 `infrastructure_failed_partial_after_model_response`，不计分，账户费用 ¥0.24 计入总成本。其 export 包含 11 个 reasoning blocks 和 22 个 tool calls；event stream 在最终 pending tool 前记录了 23 个 completed tool events，因此两种计数均按各自来源语义保留。没有观察到 final stop，raw session/event evidence 继续 private。replacement `P2-20260815-04b-opencode-replacement` 在 frozen workspace reset 后只运行一次，使用 OpenCode `1.18.17` commit `02546dfc2e4515a4f90aaf9ceb3890df2ac2b479`、direct DeepSeek provider、`deepseek-v4-pro`、`--variant max` 和 `https://api.deepseek.com`；唯一主动改动是 detached/background 进程生命周期。

replacement 的 OpenCode exit 为 `0`，export exit 为 `0`，wall time 为 `1293.144s`，独立 balance window 为 ¥11.44 到 ¥9.91。evaluator 得到 `93/93/B+` 后未再运行，没有发生 result-based retry。

## 成本与时间

四个有效 run 的账户余额成本为 ¥6.88，token 复算成本为 ¥6.856277。保留的 partial 增加账户余额成本 ¥0.24、token 复算成本 ¥0.219027，因此总账户成本为 **¥7.12**，总 usage 复算成本为 **¥7.075304**。账户与 usage 的差异为 ¥0.044696，作为 reconciliation 信息保留，不静默归入任一 run。

四个 model run 合计消耗 5,791.667 秒 model wall time。计入已记录的环境准备、充值暂停、evaluator、artifact 生成和监视后，preregistered same-day wall clock 仍低于 12 小时硬上限。本阶段未运行 DeepSWE、Terminal-Bench、Docker/WSL2、optional real ESP-IDF build 或额外 paid smoke request。

## 证据与公开边界

`artifacts/comparison.json` 是 machine-readable aggregate，`artifacts/evidence-manifest.json` 记录 public artifact hash 和 private raw evidence hash。完整 DSH session JSONL、OpenCode session export/event streams、reasoning text、credentials 和私人路径只保存在已 ignore 的 `private/` 下。公开 artifact 仅保留 derived fingerprints、scores、token/time/cost aggregates、tool-catalog snapshots、evaluator result hashes 和 infrastructure events。

原始 evaluator output directory 继续作为本机 run product 保存。对比直接使用原 evaluator 的 Ability/Ship/Class、hidden result、ESP static result 和 F9 mode，没有修改题面、verifier 或 scoring。
