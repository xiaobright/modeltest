# Project2 模型测评 — 正式冻结说明

**状态：** 正式冻结（事实冻结 / de facto frozen）；**已于 2026-09-10 停更封笔**
**冻结日期：** 2026-07-23
**停更日期：** 2026-09-10
**冻结基线：** V4.1b（`project2-v4.1b`）
**评分面冻结（在先）：** 2026-07-19，见 [`evaluator/reports/v4.1b_freeze_manifest.md`](./evaluator/reports/v4.1b_freeze_manifest.md)

> **2026-09-10 最终收尾：** V4.1b 的实测台账**就此停更**，不再追加任何模型观测。
> 原因是尺子已逐渐失去区分度——顶端 94–98 拥挤、剩余方差只来自语义/契约琐碎项、
> 成本塌到几毛钱甚至免费。V5 三次尝试均失败，且不再开发 V4.1c / V5 / V5 HIL。
> 完整说明见 [`docs/V5_ATTEMPTS_AND_RETIREMENT.md`](./docs/V5_ATTEMPTS_AND_RETIREMENT.md)。
> 本文下文 §1 中「仍可追加观测」的例外**同步关闭**。

本项目到此为止。V4.1b 已经完成了它唯一的目的——**在真实渠道、成本与可用额度约束下，为个人开发/选型提供一份参考台账**（非面向社区的公开 benchmark）。结论已经稳定，不再迭代、不启动 V5、不为区分 95–99 增加题目或改评分。

这个冻结是**主动设立的硬性边界**，用来防止项目继续膨胀成无止境的自我优化。它不是"没做完"，而是"到站了"。

---

## 1. 「冻结」具体指什么

**不再改动（硬性边界）：**

- 不改评分逻辑与规则面：`evaluator/scoring/score_model.py`、`rubric.md`、`reviewer_prompt.md`、`item_registry.json`，以及 `evaluator/tests/hidden/` 下的隐藏测试。这些已于 07-19 以 SHA-256 冻结。
- 不新增 / 删改评分族（F1–F12）、cascade 规则、Ship/Class 阈值或 trust cap。
- 不开发 V4.1c，不开发 V5；「新鲜度 / 显式 session / QEMU / HIL」等题源保持远期备忘，不进现行评测。
- 不用 V4.1b 规则重算 V4.0 / V4.1a 的历史正式成绩。

**曾经允许（唯一的例外，已于 2026-09-10 关闭）：**

- ~~当**真的有选型需要**时，对某个新模型跑一遍**现成**流程，并在 `v4.1b_scoreboard.md` 追加**一行**观测、在 `evaluator/reviews/` 放一份对应评审。~~
- **自 2026-09-10 起不再追加任何观测。** 原因见
  [`docs/V5_ATTEMPTS_AND_RETIREMENT.md`](./docs/V5_ATTEMPTS_AND_RETIREMENT.md)：尺子已失去区分度，
  继续追加只是在饱和区间里重复报数。

> **越界判断（一句话）：** 一旦你开始编辑 `score_model.py` / `item_registry.json` / `rubric.md`，或新开一个设计文档——就是越回去了，**停**。
>
> **测新模型的节制线：** 只有"真的要为某个选择去测"时才测，而不是"出了个新模型、手痒了"就测。别让"有模型就测"变成又一个需要不停填的数字面板。

## 2. 现行权威结果（看这些就够）

| 文件 | 用途 |
|---|---|
| [`evaluator/reports/v4.1b_scoreboard.md`](./evaluator/reports/v4.1b_scoreboard.md) | **现行成绩榜**：全部已测模型（20+ 渠道组合）、多跑区间与样本索引 |
| [`docs/v4.1/FINAL_ASSESSMENT_20260719.md`](./docs/v4.1/FINAL_ASSESSMENT_20260719.md) | 使用阈值、局限与 V5 决策 |
| [`docs/v4.1/ROUND_SUMMARY_20260719.md`](./docs/v4.1/ROUND_SUMMARY_20260719.md) | 轮次事实终稿 |
| [`evaluator/reports/v4.1_efficiency_board.md`](./evaluator/reports/v4.1_efficiency_board.md) | 成本/时间副榜（不进 Ability） |
| [`evaluator/reports/v4.1b_freeze_manifest.md`](./evaluator/reports/v4.1b_freeze_manifest.md) | 评分面与锚点 summary 的冻结哈希 |
| [`evaluator/reports/README.md`](./evaluator/reports/README.md) | **全部报告清单**（现行 / 历史分层） |

**核心结论（摘自 FINAL_ASSESSMENT）：**

- Ability ≥ 95 且无严重 Ship blocker = 当前日常项目的可靠完成档。
- Ability ≥ 90 = 可用执行档，需结合 Ship 与失败 family 决定是否需要强模型终审。
- 90 / 95 是**本项目、本题面、本工具环境**下的经验阈值，**不是跨项目通用认证**。
- 本轮最可靠的结论是"**尺子进步了**"，不是"所有模型都升级了"；harness/渠道差异是选型现实的一部分，已全部标注。

**最后一次追加观测：** DeepSeek-V4.1-Flash @ WorkBuddy（`20260910_122044`，98/98/B+），
2026-09-10 并入后**停更封笔**。（此前最后一次为 Claude-Sonnet-4.6 @ Antigravity
`20260723_171033`；其后 2026-07-23 至 2026-09-10 期间追加的观测见成绩榜。）

## 3. 与既有冻结 / 归档纪律的关系

- 07-19 的**评分面冻结**（`v4.1b_freeze_manifest.md`）继续有效；本文件是其上的**项目级收尾声明**。
- 历史归档与结果按 [`archives/禁止删除_评测结果和归档.md`](./archives/禁止删除_评测结果和归档.md) 保护：`archives/` 各 round、`evaluator/results/`、`evaluator/reviews/`、`v4_gold` **不得删除或搬动**。
- 2026-07-23 的首次冻结**只新增 / 整理说明文档**（本文件 + 报告索引 + 根 README 横幅），**未触碰**任何 result / review / 归档 / 评分文件。
- 2026-09-10 的停更同样**只新增 / 整理说明文档与成绩台账**（本文件 + [`docs/V5_ATTEMPTS_AND_RETIREMENT.md`](./docs/V5_ATTEMPTS_AND_RETIREMENT.md) + 根 README 横幅 + `v4.1b_scoreboard.md` 追加行），**未触碰**评分逻辑、隐藏测试与历史 result。

## 4. 将来若要测一个新模型（最小流程 · 已归档，仅供参考）

> **注意：** 以下流程自 2026-09-10 起**不再执行**。保留仅为了让成绩榜的证据链可复算。

```powershell
python evaluator\make_broken_project.py
# 模型只改 workspace\project2_task
python evaluator\run_full_eval.py workspace\project2_task `
  --model NAME --channel CH --harness H `
  --require-meta --include-espidf-build `
  --run-group-id GROUP --run-index 1 --thinking-level high
# 下一模型前再 make_broken_project
```

跑完：按 worst-of-n 规则在 `v4.1b_scoreboard.md` 加一行，写一份对应 `evaluator/reviews/` 评审。**其余一概不改。**

---

*V4.1b 完成了它该完成的事。项目安静地停在这里。*
