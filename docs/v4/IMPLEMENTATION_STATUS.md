# V4 状态说明

**日期：** 2026-07-11（V4.0）；归档 2026-07-18  
**状态：** **V4.0 已转正并完整归档**；live 主线 **V4.1b**（见 `docs/v4.1/`）

## 正式产物

| 用途 | 路径 |
|------|------|
| 成绩榜 | `evaluator/reports/v4_scoreboard.md` |
| 本轮报告 | `evaluator/reports/v4_round_report.md` |
| 冻结清单 | `evaluator/reports/v4_freeze_manifest.md` |
| 单模型评审 | `evaluator/reviews/v4_*.md` |
| Gold | `archives/v4_gold/`（V4.0 build verify `20260711_222515`，100/A） |
| V4.0 完整归档 | `archives/v4_round_final_20260718/` |
| 现状与原始设计差异 | `docs/v4/CURRENT_STATE_VS_ORIGINAL_DESIGN.md` |
| 原始设计归档 | `docs/v4/archive/original_design/` |
| 候选提示词 | `CANDIDATE_PROMPT.md` |
| 评审提示词 | `REVIEWER_PROMPT.md`（流程）+ `evaluator/scoring/reviewer_prompt.md`（评分约束） |
| V2 历史 | `archives/second_round_v2_final_20260711/` |

## 已关闭事项

- 旧 Grok「96 remap」评审与对应误导性 V4 draft 已从 live 成绩体系移除  
- 正式 Grok 成绩以真 V4 重跑 `20260711_210538`（82/B）为准  
- 不再使用「锚定测试」作为对外表述；当前样本即为 V4 正式成绩  
- F11 模板误判已修复，7 个正式样本重算差值为 -1 至 +3  
- Gold 已直接对归档树完成真实 ESP-IDF build，证据随 result 固化  
- 5 个历史空 meta result 不改写，由 freeze manifest 提供 canonical meta  
- 可选项目外 allowlist handoff 仍保留脚本；**日常默认主空间** `workspace/project2_task`  

## 日常评测

```powershell
python evaluator\make_broken_project.py
python evaluator\run_full_eval.py workspace\project2_task `
  --model NAME --channel CH --harness H `
  --require-meta --include-espidf-build `
  --run-group-id GROUP --run-index 1 --thinking-level high
```

模型尽量只看见 `workspace/`；Gold、`evaluator/`、`docs/`、`archives/` 不对候选可见。  
外发隔离时再用 `prepare_candidate_handoff.py`。
