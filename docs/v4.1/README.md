# Project2 V4.1 文档

**状态：** **V4.1b 正式稳定基线**（反 ambient 连坐，2026-07-19 锚点闭环）；V4.1a 历史锚点保留  
**V4.0 冻结归档：** [`archives/v4_round_final_20260718/`](../../archives/v4_round_final_20260718/README.md)  
**Gold（业务树仍 V4.0）：** [`archives/v4_gold/`](../../archives/v4_gold/README.md)  
**4.1b 说明：** [`V4.1b_NOTES.md`](./V4.1b_NOTES.md)  
**本轮终稿（接续必读）：** [`ROUND_SUMMARY_20260719.md`](./ROUND_SUMMARY_20260719.md)
**最终评估：** [`FINAL_ASSESSMENT_20260719.md`](./FINAL_ASSESSMENT_20260719.md)
**阶段总结：** [`PROJECT2_PHASE_SUMMARY_20260804.md`](../PROJECT2_PHASE_SUMMARY_20260804.md)

---

## 一句话

> V4.1b = V4.1a + **ambient 只扣 F3-05** + F5-05 仅授权 care；不重算 4.0/4.1a；不做 V5 题。

## 日常用这些

| 文件 | 用途 |
|------|------|
| [`CANDIDATE_PROMPT.md`](../../CANDIDATE_PROMPT.md) | 被测模型提示词（任务面未改） |
| [`REVIEWER_PROMPT.md`](../../REVIEWER_PROMPT.md) | 评审流程 |
| [`DESIGN.md`](./DESIGN.md) | V4.1 设计摘要 |
| [`MULTI_RUN_PROTOCOL.md`](./MULTI_RUN_PROTOCOL.md) | 重复运行与榜单规则 |
| `evaluator/scoring/rubric.md` | 现行评分规则 |
| `evaluator/reports/v4.1b_scoreboard.md` | **现行** V4.1b 成绩榜 |
| `evaluator/reports/v4.1_scoreboard.md` | V4.1a 历史锚点（不重算） |
| `evaluator/reports/v4.1_efficiency_board.md` | 效率副榜（不进 Ability） |
| `evaluator/reports/v4.1b_freeze_manifest.md` | **现行 V4.1b 冻结清单** |
| [`FINAL_ASSESSMENT_20260719.md`](./FINAL_ASSESSMENT_20260719.md) | 使用阈值、版本结论与 V5 决策 |
| [`DEEPSEEK_V4_PRO_HARNESS_ANALYSIS_20260814.md`](./DEEPSEEK_V4_PRO_HARNESS_ANALYSIS_20260814.md) | V4 Pro 灰测、正式版与 DSH 三 preset 对照 |
| [`DEEPSEEK_V4_TRAJECTORY_ANALYSIS_20260814.md`](./DEEPSEEK_V4_TRAJECTORY_ANALYSIS_20260814.md) | 思维链风格、PTC 调用结构与统计方法 |
| [DEEPSEEK_V4_TRIGGER_MECHANISM_EXPERIMENTS_20260814.md](https://github.com/0liveiraaa/DeepseekCotexplorations/blob/main/contributions/xiaobright-deepseek-v4-harness/reports/DEEPSEEK_V4_TRIGGER_MECHANISM_EXPERIMENTS_20260814.md) | Pro / Flash system 与工具目录触发消融、两阶段验证（**已迁移至 DeepseekCotexplorations 研究仓库**，本仓库不再保留副本） |

## 与 V4.0 / V5 边界

| 层 | 处理 |
|----|------|
| V4.0 正式成绩 | 冻结在 `archives/v4_round_final_20260718/`，**禁止**用 V4.1 规则重算 |
| V4.1 变更 | evaluator 观测：F6 fixture、cascade 标注、multi-run meta |
| V5 | 新鲜度、session 抢占、QEMU/HIL — **不进** V4.1 |

## 当前使用解释

- Ability >=95 且无严重 Ship blocker：当前日常项目的可靠完成档。
- Ability >=90：可用执行档，结合 Ship/family 做终审。
- 90、95 是本项目经验阈值，不是跨项目通用认证。
- V4.1b 已满足当前选型需求；不再为区分 95-99 开发增量题。

## 评测命令（默认：主空间）

```powershell
python evaluator\make_broken_project.py
# 模型只改 workspace\project2_task
python evaluator\run_full_eval.py workspace\project2_task `
  --model NAME --channel CH --harness H `
  --require-meta --include-espidf-build `
  --run-group-id GROUP --run-index 1 `
  --thinking-level high
# 下一模型前再 make_broken_project
```

可选隔离投放：`python evaluator\prepare_candidate_handoff.py`（日常锚点不必用）。
