# Project2 V4 文档

**状态：** **V4.0 已转正并完整归档**（2026-07-11 / 归档 2026-07-18）  
**完整归档：** [`archives/v4_round_final_20260718/`](../../archives/v4_round_final_20260718/README.md)  
**正式成绩榜（历史）：** [`evaluator/reports/v4_scoreboard.md`](../../evaluator/reports/v4_scoreboard.md)  
**本轮报告：** [`evaluator/reports/v4_round_report.md`](../../evaluator/reports/v4_round_report.md)  
**冻结清单：** [`evaluator/reports/v4_freeze_manifest.md`](../../evaluator/reports/v4_freeze_manifest.md)  
**Gold：** [`archives/v4_gold/`](../../archives/v4_gold/README.md)  
**后续主线：** [`docs/v4.1/README.md`](../v4.1/README.md)

---

## 日常用这些

| 文件 | 用途 |
|------|------|
| [`CANDIDATE_PROMPT.md`](../../CANDIDATE_PROMPT.md) | 被测模型提示词 |
| [`REVIEWER_PROMPT.md`](../../REVIEWER_PROMPT.md) | 评审模型提示词 |
| [`IMPLEMENTATION_STATUS.md`](./IMPLEMENTATION_STATUS.md) | 状态与路径速查 |
| [`CURRENT_STATE_VS_ORIGINAL_DESIGN.md`](./CURRENT_STATE_VS_ORIGINAL_DESIGN.md) | 当前实现与初始设计的差异 |
| `evaluator/scoring/rubric.md` | 现行评分规则 |

## 原始设计归档

实施前的 `00`–`08` 设计序列、评分示例、capstone 备选、实施 handoff 和多模型交叉
评审已经无损归档到 [`archive/original_design/`](./archive/original_design/README.md)。

这些材料用于解释设计动机和决策过程，不再作为运行契约。遇到差异时以 freeze
manifest、rubric、item registry、evaluator 代码和正式结果为准。

## 一句话

> V4 = V2 工程壳 + Ability/Ship 双轨 + 细粒度题库；正式成绩见 scoreboard，不把历史 remap 当分。

## 远期方向

V5 / V5 HIL 尚未立项，短期不实施。原 V5 标准层的需求已由 V4.1b 覆盖；远期 V5
只保留高耦合 capstone，V5 HIL 复用同一提交做真机验证。想法、版本边界和开工门槛见
[`docs/V5_DESIGN_DIRECTION.md`](../V5_DESIGN_DIRECTION.md)。V4.1b 在此之前继续作为
正式稳定基线。
