# V4 交叉审核清单（给其它 AI / 人类评审）

## 你的任务

阅读 `docs/v4/` 后，输出结构化意见：

```markdown
## 总裁决
同意 | 有条件同意 | 反对

## 必须修改（blocking）
- ...

## 建议修改（non-blocking）
- ...

## 同意的亮点
- ...

## 对开放争议点的投票
见下表

## 风险与可实施性
- ...
```

不要只写「整体不错」。**逐条对检查项给 Pass / Fail / Unsure。**

---

## A. 目标一致性

| # | 检查项 | P/F/U |
|---|--------|-------|
| A1 | V4 是否清楚以 V2 为基底而非 V3.1 树？ | |
| A2 | 是否明确解决 82 墙，而非用新 cap 换墙？ | |
| A3 | 是否保留信任类重罚（public/篡改/造假）？ | |
| A4 | 非目标是否足够（无硬件、不混 V1 分）？ | |
| A5 | 成功标准是否可判定？ | |

## B. 评分体系

| # | 检查项 | P/F/U |
|---|--------|-------|
| B1 | F1–F12 加总是否为 100？ | |
| B2 | 仅 ambient 失败时，是否仍能在 Ability 上区分不同完成度模型？ | |
| B3 | F3e Ship≤89 是否可接受？若否给替代 | |
| B4 | F12=4 是否合理？ | |
| B5 | Hard cap 列表是否过宽/过窄？ | |
| B6 | Release Class 是否与分数重复或互补清晰？ | |
| B7 | 渠道强制列是否足够抑制工具噪声误解？ | |
| B8 | 自动草稿 + 人工终裁职责是否清楚？ | |
| B9 | 是否强制同时展示 Release view 与 Ability view，避免 Ship gate 形成新墙？ | |
| B10 | reason-only 失败是否只进 F12 / semantic_only，而不会升级成 S-* 行为 blocker？ | |

## C. 题库

| # | 检查项 | P/F/U |
|---|--------|-------|
| C1 | 是否 ≥12 个低耦合中等权重点？ | |
| C2 | 每条高分值题是否行为 oracle 而非命名 cop？ | |
| C3 | F3 与 F12 拆分是否避免「拒绝了仍当安全失败」？ | |
| C4 | F4 voice 是否会诱导恢复 ambient？（设计是否防住） | |
| C5 | F6 多台阶是否可自动测？ | |
| C6 | F7 混合 CSV 是否真实且可测？ | |
| C7 | F8/F9 分家是否降低 static 刷分？ | |
| C8 | 是否存在仍严重 GPT 口味的题？指出 id | |
| C9 | 题量是否导致评测过贵/过慢？ | |
| C10 | 是否应该从 `CAPSTONE_ITEM_IDEAS.md` 选择 1–2 个高耦合上限题进入 V4.0/V4.1？ | |
| C11 | 若加入 capstone，是否能避免一个复杂链路失败连坐半张卷子？ | |

## D. Seed / 提示

| # | 检查项 | P/F/U |
|---|--------|-------|
| D1 | public 绿 + hidden 红 的 broken 标准是否成立？ | |
| D2 | 脏库策略是否避免 public 必红？ | |
| D3 | ONBOARDING 去剧透是否足够？ | |
| D4 | probe warning 是否泄漏过多解法？ | |
| D5 | 保留 PR 模板 vs answer.md 是否合理？ | |

## E. 流水线

| # | 检查项 | P/F/U |
|---|--------|-------|
| E1 | artifact 列表是否完整可复盘？ | |
| E2 | blockers/score_draft 契约是否可实现？ | |
| E3 | build skipped 是否被防白送分？ | |
| E4 | 实施切分 PR-A..D 是否合理？ | |
| E5 | score_draft_confidence / unscored_items 是否足以区分正式 V4 run 与历史 relabel？ | |

## F. 反偏置与历史

| # | 检查项 | P/F/U |
|---|--------|-------|
| F1 | 十条纪律是否可执行？ | |
| F2 | 跨模型试跑门禁是否必要/过重？ | |
| F3 | 重标注误差带 ±3 是否诚实？ | |
| F4 | 附录示例是否显示 82 团被拉开？ | |
| F5 | 冻结前是否要求门槛聚集审计，避免 V3.1 式 cap 换皮？ | |

## G. 开放争议投票

| 争议 | 你的选择 | 一句话理由 |
|------|----------|------------|
| F3e Ship 顶 89 / 取消 / 改值 | | |
| 主榜排序 Ship 优先 vs Ability 优先 | | |
| 无 IDF 时 F9 给 2–3 分是否公平 | | |
| sketch_jan22a 保留 vs 移除 | | |
| 重复 CSV 幂等是否纳入 V4.0 | | |
| 是否加入高耦合 capstone；若加入选哪个 | | |
| Ability 是否允许人工 ±2 | | |

---

## 审核时建议阅读的历史材料

- `evaluator/reports/v2_soft_cap_experimental_scoreboard.md`  
- `archives/.../FINAL_BENCHMARK_REPORT_V1_V2_V31.md`  
- `docs/v4/APPENDIX_SCORE_EXAMPLES.md`  

## 输出存放建议

请把意见写到（任选）：

- `docs/v4/reviews/<your_name>_review.md`（实施前可新建）  
- 或用户指定的对话/文档  

**Blocking 意见必须给出可替换方案**，避免只否决无建设。
