# Codex 交叉审核意见

## 总裁决

有条件同意。

V4 的主方向是对的：继续用 V2 真实工程壳，不继承 V3.1 的总分 cap 结构；把 Ability 与 Ship 拆开；把 reason-code 降权；把 ESP static 与 real build 分家。这些改动正好对应 V2/V3.1 的真实失败模式。

## 必须修改（blocking）

- **不能让 Ship 成为唯一主排序**：F3e Ship≤89 有发布语义，但若 scoreboard 只按 Ship 讲故事，会把原 82 墙换成 89 墙。已建议改成 Release view + Ability view 双视图，同 gate 内按 Ability 排序。
- **reason-only 不能升级成 S-* blocker**：V3.1 里多次出现“已 deny、零泄漏、只是 reason 错”的样本。F3 行为分必须保留，只扣 F12；`S-no-actor` 只用于实际授权/泄漏。
- **score draft 必须有证据置信度**：历史 V2 重标注、build skipped、未实测的新 V4 item 不能被公式静默填 0 或满分，必须输出 `unscored_items` 和置信度。
- **冻结前必须做门槛聚集审计**：V3.1 的教训不是没有 cap，而是 cap 成了排序器。V4 freeze 前应模拟 Ship/Ability 分布，确认没有新单点门槛吞掉中上游差异。

## 建议修改（non-blocking）

- F4 voice bridge 的 oracle 应保持行为导向：核心是敏感 context 请求带显式 session，不是强制某个函数名或单一路由。
- F9 无工具链给 2–3 分可以保留，但 scoreboard 必须显式标 `build_skipped`，不要和真实 build pass 混读。
- `sketch_jan22a.ino` 默认保留可以接受；它是真实仓库噪声，也可能给 ESP 线索。若后续 ESP 过易，再单独移出可见包。
- V2 历史重标注只适合验证设计区分度，不应写成官方 V4 成绩。

## 同意的亮点

- V2 作为基底是正确选择：它比 V1 更适合强约束 debug，比 V3.1 更适合主榜。
- Family 预算比 V2 更清楚，尤其 F3/F6/F8/F9/F12 拆分能解释 82 档内部差异。
- 信任类 hard cap 保留得当：public 失败、改测试、构建造假、严重 overclaim 仍应重罚。
- item bank 的 “行为 oracle + allowed equivalents” 能缓解出题风格偏置。

## 对开放争议点的投票

| 争议 | 选择 | 理由 |
|------|------|------|
| F3e Ship 顶 89 / 取消 / 改值 | 保留 89，但必须双视图 | ambient 是发布阻断；但不能作为能力排序器 |
| 主榜排序 Ship 优先 vs Ability 优先 | 正式报告双视图 | Ship 讲风险，Ability 讲代码能力，二者缺一不可 |
| 无 IDF 时 F9 给 2–3 分是否公平 | 保留 | 环境不可用不该满分，也不该等同造假 |
| sketch_jan22a 保留 vs 移除 | 暂保留 | 真实噪声有价值；难度可后调 |
| 重复 CSV 幂等是否纳入 V4.0 | 暂不纳入 | 当前题量已经足够，幂等适合 V4.1 |
| Ability 是否允许人工 ±2 | 允许，但强制写理由 | 自动证据不能替代架构/报告审查 |

## 风险与可实施性

- 实施可行，建议按 PR-A 到 PR-E 分段，不要一次性改 seed、hidden、评分和榜单。
- 最大风险不是题太难，而是评分实现漂移：如果 reviewer_prompt 或 score_model 又把 cap 当主排序器，V4 会复刻 V3.1 的失败。
- 第二大风险是证据混用：V2 relabel、真实 V4 run、用户确认 build、build skipped 必须在 artifact 里机器可读地区分。

## 已直接修改

- 更新 `02_SCORING_SYSTEM.md`：双视图、Ship gate 语义、reason-only 与 behavior blocker 拆分。
- 更新 `05_EVALUATOR_PIPELINE.md`：证据置信度、`unscored_items`、scoreboard 双视图、发布前自测矩阵。
- 更新 `06_ANTI_BIAS_AND_AUTHORING.md`：新增门槛聚集审计。
- 更新 `07_MIGRATION_AND_COMPAT.md`：rollout checklist 与 PR 切分补齐。
