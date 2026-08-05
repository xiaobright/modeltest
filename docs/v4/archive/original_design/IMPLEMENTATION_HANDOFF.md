# V4 落地交接清单

**用途**：给后续实现者使用的冻结版执行顺序。  
**状态**：在 Codex / DeepSeek / Kimi K2.7 / GLM-5.2 / MiniMax-M3 / Qwen3.7 Max 六份审核后整理。  
**基底**：V2 当前主线；不得以 V3.1 目录树作为实施基底。

## 1. 已收敛决策

- 默认主榜按 **Ability 降序**；Ship/Class 是发布风险信息列，Release view 是第二视图。
- F3e ambient fallback **取消 Ship 数值天花板**；只扣 F3e 的 5 分并标 `S-ambient` + Class B+。
- reason-only 失败只进 F12 / `semantic_only`；已 deny 且零泄漏时不得生成 S-* behavior blocker。
- F9 无工具链固定给 3/6，必须标 `f9_mode: "skipped_env"`；不采用分母缩放。
- F1 不引入 git 时间戳自动扣分；时序异常只进 `score_draft_confidence.json` notes 或人工 review。
- V4.0 默认不加 capstone；若校准后 ≥3 个模型 Ability≥96 或 top3 Ability 极差<2，则 V4.1 必须从 `CAPSTONE_ITEM_IDEAS.md` 选 1 个 capstone。

## 2. P0 风险

| 风险 | 必须动作 |
|------|----------|
| F3/F12 拆分停在纸面 | PR-B1 必须先实现 assertion-level mapping、`scenario_id`、V2 样本回归 |
| Ship/Ability 实现漂移 | reviewer_prompt 与 scoreboard 默认 Ability 主序；违反则报告不完整 |
| F8 static 改写过宽/过紧 | 支持宏展开；uncertain 人工 final；用 V2 已知样本回归 |
| api_contracts 继续剧透 | PR-C 改第 49 行；用 V2 历史样本验证 F3e 通过/失败分布不突变 |
| 自动草稿偏高 | `score_draft_confidence.json` 必须有 `overestimate_risk` |

## 3. 实施顺序

### PR-A：评分管线骨架

目标：先让 V4 产物格式落地，不改 hidden 语义。

必须输出：

- `blockers.json`
- `score_draft.json`
- `score_draft_confidence.json`
- `summary.json` 新字段
- `item_registry.json` 框架

验收：

- 旧 V2 hidden 仍可跑。
- `score_draft_confidence.json` 含 `overestimate_risk`、`unscored_items` / 缺证说明。
- V2 seed 跑一次，score draft 与人工 review 差 < 5 分。

### PR-B1：F3/F12 assertion-level mapping

这是最关键 PR，不得与其它 hidden 扩展混做。

必须改：

- `evaluator/scoring/item_registry.json`
- `evaluator/tests/hidden/test_context_policy.py`
- `evaluator/run_hidden_tests.py`
- `evaluator/tests/hidden/eval_helpers.py`
- `evaluator/scoring/score_model.py`

推荐实现：

- 把 context policy 测试拆成 `*_behavior` 与 `*_reason` 两类 test 方法。
- `item_registry.json` 每个 item 写 `item_id`、`family`、`points`、`scenario_id`、`test_method`、`assertion_keys`、`semantic_only`、`blocker`。
- `run_hidden_tests.py` 仍用 `unittest` 自动发现，但结果映射必须走 registry。
- `hidden_summary.json` 的每条 record 可以含多个 items；同一 `scenario_id` 的 behavior/reason 能在 review 中还原。

验收：

- Grok-4.5 / GPT-5.5 这类 reason-only 失败样本：F3 行为分保留、F12 扣分、无 S-* behavior blocker。
- ambient-only 失败样本：F3e 扣 5 分、`S-ambient`、Class B+、无 Ship 数值顶。
- `scenario_id` 聚合正确：同一场景的 behavior/reason 不会被当成两个无关问题。

### PR-B2：其余 hidden / static 扩展

范围：

- F4 voice bridge
- F6 migration 多 case
- F7 mixed CSV
- F8 static 改写
- ambient-only / partial failure 夹具

验收：

- F8-07 支持字面量、宏定义和动态分配。
- `f8_07_status: "uncertain"` 时不自动给分也不自动扣分，由人工 final。
- Grok-4.5 8/8、DeepSeek Pro 5/8、LongCat 5/8 这三个 V2 static 已知点改写后不突变 ±1。

### PR-C：seed / prompt / probe

范围：

- 生成 `project2-v4-broken-seed`
- ONBOARDING 去剧透
- `reference/api_contracts.md` 第 49 行去剧透
- debug probe 增加症状级 warning
- legacy dirty DB 放 `data/legacy_sample.db`，不得污染 public TEMP DB

验收：

- broken seed public 绿。
- probe 给症状但不暴露完整解法。
- `api_contracts.md` 改写后，GLM-5.2 / Doubao / Grok-4.5 这类 V2 F3e 通过样本仍过，Kimi K2.7 / LongCat / Composer 这类 F3e 失败样本仍失败。

### PR-D：scoreboard / relabel / 校准

范围：

- `evaluator/reports/v4_scoreboard.md`
- Ability view 默认表
- Release view 第二表
- V2 relabel 附录
- 5 个锚点校准

验收：

- Ability 列在主榜排序中优先。
- 每行显示 Ship/Class/Blockers。
- relabel 行标 `evidence_source`，`review_inferred` 的样本置信度为 low。

### PR-E：冻结前审计

范围：

- 门槛聚集审计
- frozen gold 自测
- 回滚条件检查
- 关闭交叉审核意见

验收：

- frozen gold Ability/Ship ≥95，Class A。
- top3 Ability 极差不触发回滚条件。
- score draft 与人工 review 差在阈值内。

## 4. frozen gold 创建规则

- 优先用 V2 顶部样本（Grok-4.5；若 artifact 不完整则 GPT-5.5）作为基础。
- 人工补齐 V4 新增项：F4 voice bridge、F6 多台阶 migration、F7 mixed CSV、F8-07。
- 存放到 `archives/v4_gold/project2_task/`。
- 另建 `archives/v4_gold/README.md` 记录来源、补齐项、build log 和未验证硬件。
- 不得进入候选可见包。

## 5. 回滚条件

任一触发即冻结 V4 实施，回滚到 V2 seed 与 V2 rubric：

| 条件 | 触发标准 |
|------|----------|
| 自动草稿不可信 | 校准 5 锚点与人工分差 > ±5 |
| 新墙复发 | top3 Ability 极差 < 1 |
| F3/F12 拆分噪音大 | relabel 与重跑差 > ±3 |

回滚时保留 `docs/v4/` 作为设计档，不删除评审与历史记录。

## 6. 不要做

- 不要用 V3.1 workspace 作为实施基底。
- 不要把 Ship/Class 当默认主榜排序。
- 不要把 reason-only 失败升级成安全泄漏。
- 不要把 skipped ESP build 当满分。
- 不要把 capstone 塞进 V4.0 主分，除非校准触发条件成立且用户明确批准。
- 不要删除 archives、results、reviews 或历史报告。
