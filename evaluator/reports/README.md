# 评测报告索引

> ⛔ **项目已于 2026-07-23 正式冻结（V4.1b）。** 详见根目录 [`PROJECT_FROZEN.md`](../../PROJECT_FROZEN.md)。
> 评分面哈希冻结在先（2026-07-19，见 `v4.1b_freeze_manifest.md`）。以下清单只区分现行 / 历史，方便查阅，**不代表可重算历史成绩**。

阅读顺序（现行）：`FINAL_ASSESSMENT` → `ROUND_SUMMARY` → `v4.1b_scoreboard` → `v4.1_efficiency_board` → `v4.1b_freeze_manifest`。

## V4.1b（当前正式稳定基线 / 现行）

| 文件 | 说明 |
|------|------|
| [`v4.1b_scoreboard.md`](./v4.1b_scoreboard.md) | **现行成绩榜**：正式成绩、多跑区间与样本索引 |
| [`v4.1_efficiency_board.md`](./v4.1_efficiency_board.md) | 成本/时间副榜，不进入 Ability |
| [`v4.1b_freeze_manifest.md`](./v4.1b_freeze_manifest.md) | 规则文件与正式 summary 冻结哈希 |
| [`../../docs/v4.1/FINAL_ASSESSMENT_20260719.md`](../../docs/v4.1/FINAL_ASSESSMENT_20260719.md) | 使用阈值、局限与 V5 决策 |
| [`../../docs/v4.1/ROUND_SUMMARY_20260719.md`](../../docs/v4.1/ROUND_SUMMARY_20260719.md) | 轮次事实终稿 |

## V4.1a（历史过渡锚点，不重算）

| 文件 | 说明 |
|------|------|
| [`v4.1_scoreboard.md`](./v4.1_scoreboard.md) | V4.1a 历史成绩榜 |
| [`v4.1_freeze_manifest.md`](./v4.1_freeze_manifest.md) | V4.1a 冻结清单 |

## V4.0（历史冻结主轮）

| 文件 | 说明 |
|------|------|
| [`v4_scoreboard.md`](./v4_scoreboard.md) | V4.0 **正式成绩榜**（Ability-first） |
| [`v4_v2_comparison_final.md`](./v4_v2_comparison_final.md) | **最终分析**：V4 结果、V2 对照、成本与渠道结论 |
| [`v4_round_report.md`](./v4_round_report.md) | V4 本轮说明与结论 |
| [`v4_final_summary.md`](./v4_final_summary.md) | V4 轮次总结 |
| [`v4_freeze_manifest.md`](./v4_freeze_manifest.md) | V4.0 冻结清单 |
| [`v4_relabel_from_v2.md`](./v4_relabel_from_v2.md) | V4 相对 V2 的口径对齐说明 |
| `../reviews/v4_*.md` | 单模型评审 |

现行设计说明：`docs/v4/`、`docs/v4.1/`；候选/评审提示词：根 `CANDIDATE_PROMPT.md`、`REVIEWER_PROMPT.md`。Gold：`archives/v4_gold/`。

## 成本 / 效率专项台账

| 文件 | 说明 |
|------|------|
| [`gpt5.6_cost_analysis.md`](./gpt5.6_cost_analysis.md) | GPT-5.6 系列成本分析 |
| [`kimi_k3_cost_ledger.md`](./kimi_k3_cost_ledger.md) | Kimi K3 成本记账（含换号税） |

## V2 / V1 / V3.1（历史）

| 文件 / 归档 | 说明 |
|-------------|------|
| [`v2_scoreboard_current.md`](./v2_scoreboard_current.md) | V2 成绩榜（冻结对照） |
| [`second_round_v2_report.md`](./second_round_v2_report.md) | V2 长报告 |
| [`v2_soft_cap_experimental_scoreboard.md`](./v2_soft_cap_experimental_scoreboard.md) | V2 soft-cap 实验榜 |
| [`v2_soft_cap_fun_scoreboard_zh.md`](./v2_soft_cap_fun_scoreboard_zh.md) | V2 soft-cap 趣味榜（中文） |
| [`v1_v2_comparison_report.md`](./v1_v2_comparison_report.md) | V1 / V2 对照 |
| `archives/first_round_v1_20260612/` | V1 整轮 |
| `archives/second_round_v2_final_20260711/` | V2 完整 24 样本冻结 |
| `archives/third_round_v3.1_20260615/` | V3.1 |

## 保护

禁止批量删除 `evaluator/results`、`evaluator/reviews`、各 round 归档与 gold。见 [`../../archives/禁止删除_评测结果和归档.md`](../../archives/禁止删除_评测结果和归档.md)。
