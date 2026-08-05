# GLM-5.2 交叉审核意见

## 总裁决

**有条件同意。**

V4 的核心方向经过三轮测试数据验证是正确的：以 V2 工程壳为基底，用 Ship/Ability 双轨 + 阻断标签替代 hard cap 主导排序，F3/F12 拆分，F8/F9 分家。三份已有交叉审核（Codex/DeepSeek/Kimi K2.7）已收敛 5 个 blocking 项并在文档中落实。

本审核的重点不再是重复前三份审核已覆盖的设计层面争议，而是**深入到实施层面的具体问题**——尤其是 V2 现有 hidden test 代码与 V4 题库设计之间的落地差距。以下 5 个遗留问题解决后，V4 设计可以进入实施阶段。

---

## 必须修改（blocking）

### B1. V2 hidden test 断言混合 behavior 和 reason，F3/F12 拆分无法落地

**问题**

V4 设计在 `02_SCORING_SYSTEM.md §3.4` 和 `03_ITEM_BANK.md` 中明确要求：

> 已正确拒绝且零泄漏但 reason 错 → F3 行为分保留，只扣 F12。

但当前 V2 的 `evaluator/tests/hidden/test_context_policy.py` 在同一 test 函数中用 `assertEqual` 混合断言行为和 reason 字符串。以 `test_session_without_actor_subject_is_not_authorized_for_patient` 为例（第 81-95 行）：

```python
self.assertFalse(ctx["policy"]["allowed"])                          # F3d 行为
self.assertEqual(ctx["policy"]["reason"], "not_authorized_for_target")  # F12 reason
self.assertEqual(ctx["target"]["patient"], {})                      # F3d 行为
self.assertNotIn("Patient A likes quiet", str(ctx))                 # F3d 行为
```

`test_sensitive_target_context_requires_explicit_session`（第 97-119 行）、`test_unauthenticated_context_does_not_leak_patient_data`（第 25-34 行）、`test_expired_session_is_not_authenticated`（第 67-79 行）、`test_patient_cannot_access_other_patient`（第 52-65 行）均有同样结构。

当 reason 字符串错误时，整个 test 函数判为 `failed`，`run_hidden_tests.py` 只能报告"该 test 失败"，无法区分"行为通过/reason 失败"和"行为也失败"。这意味着 F3/F12 拆分在 hidden test 层面无法实现——除非 test runner 能按 assertion 粒度拆分报告。

**影响范围**

涉及 `test_context_policy.py` 全部 5 个测试函数，直接影响 F3a-F3e 和 F12-01/02/03 的独立计分。

**修改建议**

1. `05_EVALUATOR_PIPELINE.md §4.2` 的 `hidden_summary.json` record 格式从"一个 test → 一个 item"改为"一个 test → 多个 item，每个 item 绑定 assertion_keys"。
2. `05_EVALUATOR_PIPELINE.md §9` 的 `item_registry.json` 增加 `assertion_keys` 字段，指定该 item 对应 test 函数内的哪些断言组。
3. `run_hidden_tests.py` 实施时需要支持按 assertion key 拆分报告，而非只按 test 函数粒度。
4. `03_ITEM_BANK.md` 增加实施约束说明（见已直接修改的文档）。

### B2. F4 voice bridge 的 allowed_equivalents 有安全漏洞

**问题**

`03_ITEM_BANK.md` V4-F4-02 的 `allowed_equivalents` 写了：

> 本地 DB 直接查询若与经授权 context 等价且零泄漏

这个等价路径过宽。V3.1 评测中多个模型的 ambient fallback 本质上就是绕过了显式 session 检查。如果 V4 允许"本地 DB 直接查询"作为等价实现，模型可以绕过整个 session 授权机制直接 `SELECT * FROM care_events WHERE ...` 然后声称"等价零泄漏"。

**修改建议**

在 `03_ITEM_BANK.md` V4-F4-02 的 `allowed_equivalents` 中增加约束（已直接修改文档）：

- 本地 DB 直接查询仅允许在 voice/worker 模块内部，且必须存在显式 actor 校验步骤
- 纯粹的"有 DB 访问权就查"不算等价
- `VOICE_SESSION_ID` 必须对应一个经过验证的有效 session

### B3. api_contracts.md 第 49 行直接剧透 ambient fallback 解法

**问题**

`04_SEED_AND_PROMPT.md` 的去剧透清单提到了 ONBOARDING_TODO.md，但**遗漏了 `reference/api_contracts.md` 第 49 行**：

> 面向指定患者的敏感上下文必须携带显式有效 `session_id`。不能因为系统里存在最近一次 current session，就在缺少 `session_id` 的请求中自动放行患者数据。

这句话等于直接告诉模型 ambient fallback 的完整解法。V4 的设计意图是让模型自行推理出"需要显式 session_id"，而不是从契约文档中读到答案。

**修改建议**

在 `04_SEED_AND_PROMPT.md §5` Reference 文档部分增加对 `api_contracts.md` 的具体改写指引（已直接修改文档）。

### B4. 脏库注入路径与 public 健康标准的冲突未明确

**问题**

V3.1 的 `V31_MODIFICATIONS.md §4` 将脏库直接放在 `workspace/project2_task/data/project2.db`。但 V4 `04_SEED_AND_PROMPT.md §2.4` 说 public 默认用干净 TEMP DB。如果 seed 里自带的脏库在默认 DB 路径上，public test 是否会读它取决于 `configure_env` 的实现细节——这是一个隐性风险。

**修改建议**

在 `04_SEED_AND_PROMPT.md §2.4` 明确脏库注入路径为 `data/legacy_sample.db`（非默认 DB 路径），与 public 的默认 DB 路径隔离（已直接修改文档）。

### B5. F8 static 检查器改写风险未在实施计划中标注

**问题**

三份已有审核都提到 V2 的 `test_espidf_static_contract.py` 是死板关键词匹配，需要按 `allowed_equivalents` 重写。但 `07_MIGRATION_AND_COMPAT.md §8` 的 PR 切分中没有标注这个风险。

static 检查器改写是最容易出错的实施环节：
- **过宽**：static 变好刷分，F8 虚高（V2 中 Mimo Flash/Minimax M2.5 的问题）
- **过紧**：误杀合理实现（如 `std::string`/`malloc` 动态分配）

**修改建议**

在 `07_MIGRATION_AND_COMPAT.md §8` PR-B 中增加风险标注和回归验证要求（已直接修改文档）。

---

## 建议修改（non-blocking）

### S1. V4.1 capstone 触发条件应补充 top3 极差条件

`00_DESIGN_BRIEF.md` G1 的 capstone 触发条件是"≥3 个模型 Ability≥96"。但 V2 数据中 GPT-5.5(97)/Grok-4.5(96)/GLM-5.2(95) 已接近边界。可能出现 2 个模型 96+ 但 top3 极差仅 1 分的情况——此时顶部同样拥挤但 capstone 不触发。

**建议**：补充"或 top3 Ability 极差<2"作为备选触发条件。

### S2. item_registry.json 应支持 oracle_type 细化

`05_EVALUATOR_PIPELINE.md §9` 要求 registry 声明 `oracle_type: behavior|static|report|build`。但对于 F3 context 测试，一个 test 函数内既有 behavior 断言又有 reason 断言，需要更细的 `oracle_type` 粒度——建议在 `assertion_keys` 层面标注每个 assertion 的 oracle_type，而非只在 item 层面。

### S3. V2→V4 重标注应标注 evidence 来源类型

`APPENDIX_SCORE_EXAMPLES.md` 的重标注表已经很好，但每行应增加 `evidence_source` 列区分：
- `hidden_v4`：V4 新增 item 实测
- `hidden_v2_remap`：V2 hidden 结果映射
- `review_inferred`：从 review 叙述推断

这有助于 `score_draft_confidence.json` 的置信度判定。

### S4. reviewer_prompt 应增加 F3/F12 拆分的评审指引

当前 `evaluator/scoring/reviewer_prompt.md` 是 V2 版本。V4 实施时需新增一节明确：

- reason-only 失败不得扣 F3 行为分
- 已正确拒绝且零泄漏但 reason 错 → F3 对应子项满分，只扣 F12
- 不得因 reason 字符串错误生成 S-* behavior blocker

DeepSeek 审核建议的"Hall of Shame: Common Review Errors"也应纳入。

---

## 同意的亮点

1. **V2 作为唯一基底是正确的**。V1 测不同维度（主动性），V3.1 被 cap 绑架。V2 的 24+ 模型验证是最稳定的基线。

2. **Ship/Ability 双轨是核心洞见**。V2 soft-cap 实验榜是铁证：同样 82 分下面藏着 81.2–88.0 的巨大差距。双轨把"能不能发布"和"做了多少工程"解耦。

3. **F3/F12 拆分解决了 V2 最不公平的扣分**。Grok-4.5 在 V2 中 hidden 33/34，唯一失败是 `session_without_actor_subject` 的 reason code——模型正确拒绝了且零泄漏，只因 reason 写成 `not_authenticated` 而非 `not_authorized_for_target` 就被扣到和"未认证泄漏"同级。这在 V4 下只扣 F12 的 4 分。

4. **F8/F9 分家防止 static marker 工程师刷分**。V2 中 Mimo Flash static 7/8 但真实 build 失败、Minimax M2.5 static 8/8 但 build 失败——这两个案例证明 static 满分 ≠ 构建可信。

5. **行为 oracle + allowed_equivalents** 是反出题偏置的有效纪律。把评分从"像不像参考实现"拉回到"输入→输出对不对"。

6. **门槛聚集审计**（06 §2.11）直接针对 V3.1 的病因——cap 变成排序器。应在冻结前强制执行。

7. **score_draft_confidence + unscored_items** 把自动推断和人工确认的边界显式化。

8. **三份已有交叉审核已收敛并落实**。Codex 提出双视图、DeepSeek 提出 F3e 取消数值顶、Kimi 提出 F1 不引入 git 时序扣分——这些 blocking 项已在文档中修改，说明交叉审核流程有效。

---

## 对开放争议点的投票

| 争议 | 选择 | 理由 |
|------|------|------|
| F3e Ship 顶 89 / 取消 / 改值 | **取消数值顶，仅 Class B+** | 已由 DeepSeek/Kimi 收敛；Class 已表达发布风险，数值顶只会制造 89 墙 |
| 主榜排序 Ship 优先 vs Ability 优先 | **Ability 降序为主榜** | 已由 Kimi 收敛；测的是工程完成度，Ship/Class 作发布参考 |
| 无 IDF 时 F9 给 2–3 分是否公平 | **固定 3 分，不采用分母缩放** | 3/6=50% 对排序影响 <1 分；分母缩放引入额外计算复杂度且改变 100 分语义 |
| sketch_jan22a 保留 vs 移除 | **保留** | 真实仓库噪声；顶部模型不依赖它，中等模型可获线索 |
| 重复 CSV 幂等是否纳入 V4.0 | **不纳入** | V4.0 题库已 40+ 项，幂等适合 V4.1 |
| 是否加入高耦合 capstone | **V4.0 不加；校准后 ≥3 人 Ability≥96 或 top3 极差<2 则 V4.1 必加** | 补充极差条件防止 2 人 96+ 但顶部仍拥挤 |
| Ability 是否允许人工 ±2 | **允许，强制写具体理由** | 架构/overclaim 无法全自动；但禁止"感觉不对" |
| F12=4 是否合理 | **合理，保留 4** | V2 中 Grok-4.5/GPT-5.5 仅差 reason 精度，4 分让顶部有梯度但不决定中游 |

---

## 风险与可实施性

### 高风险

1. **F3/F12 拆分在 hidden test 层面的落地**（B1）。这是本审核发现的最关键实施问题——设计文档写了"行为与 reason 分开计分"，但现有 test 代码不支持按 assertion 拆分。如果 PR-B 只改评分管线不改 test runner，F3/F12 拆分会停留在纸面上。缓解：PR-B 必须同时改 `run_hidden_tests.py` 支持按 assertion key 报告。

2. **F8 static 检查器改写**（B5）。三份审核都提到了，但实施工程量不小且容易过宽/过紧。缓解：改写后用 V2 已知样本（Grok-4.5 8/8 vs DeepSeek Pro 5/8）做回归验证。

3. **评分实现漂移**（继承前三份审核的一致风险）。如果 `score_model.py` 或 reviewer_prompt 在实际使用中又把 Ship gate 当主排序器，V4 复刻 V3.1。缓解：reviewer_prompt 硬编码"默认按 Ability 排序"并设自检问题。

### 中风险

4. **F4 voice bridge hidden 测试误杀等价实现**。如果模型直接查本地 DB 而非走 `/api/v3/context/chat`，F4 hidden 测试会失败但模型可能做了正确的事（B2 的约束需要精确实现）。缓解：hidden test 需要检测 voice 模块中是否存在显式 actor 校验步骤，而非只检测 API 调用路径。

5. **双视图在对外传播中坍缩为单数**。如果对外只说"GLM-5.2 V4 得分 88"而 88 是 Ship（Ability=89），会丢失设计意图。缓解：官方报告模板 Ability 列在 Ship 左侧且加粗。

### 低风险

6. **PR-A..PR-E 切分合理**。PR-A（评分管线）必须先落地，然后用旧 V2 seed 跑一次确认 score_draft 与人工差 <5 分再继续。

7. **V2 relabel 的 ±3 误差带诚实**，只要每行标 `[RELABEL, NOT RERUN]`。

---

## 检查清单逐项

### A. 目标一致性

| # | 检查项 | P/F/U |
|---|--------|-------|
| A1 | V4 是否清楚以 V2 为基底而非 V3.1 树？ | **P** |
| A2 | 是否明确解决 82 墙，而非用新 cap 换墙？ | **P**（双轨 + Ability 主序解决；F3e 数值顶已取消） |
| A3 | 是否保留信任类重罚？ | **P** |
| A4 | 非目标是否足够（无硬件、不混 V1 分）？ | **P** |
| A5 | 成功标准是否可判定？ | **P**（附录示例给出具体可验证场景） |

### B. 评分体系

| # | 检查项 | P/F/U |
|---|--------|-------|
| B1 | F1–F12 加总是否为 100？ | **P** (8+12+16+4+12+10+8+8+6+8+4+4=100) |
| B2 | 仅 ambient 失败时，是否仍能在 Ability 上区分不同完成度模型？ | **P**（F3e 扣 5 分 + 其它 family 差异 ≥5 分区间） |
| B3 | F3e Ship≤89 是否可接受？ | **P**（已取消数值顶，仅 Class B+） |
| B4 | F12=4 是否合理？ | **P** |
| B5 | Hard cap 列表是否过宽/过窄？ | **P** |
| B6 | Release Class 是否与分数重复或互补清晰？ | **P** |
| B7 | 渠道强制列是否足够抑制工具噪声误解？ | **P** |
| B8 | 自动草稿 + 人工终裁职责是否清楚？ | **P** |
| B9 | 是否强制同时展示 Release view 与 Ability view？ | **P** |
| B10 | reason-only 是否只进 F12 / semantic_only？ | **P**（设计已含；但实施需改 hidden test runner，见 B1） |

### C. 题库

| # | 检查项 | P/F/U |
|---|--------|-------|
| C1 | 是否 ≥12 个低耦合中等权重点？ | **P** |
| C2 | 每条高分值题是否行为 oracle 而非命名 cop？ | **P** |
| C3 | F3 与 F12 拆分是否避免「拒绝了仍当安全失败」？ | **P**（设计已含；实施需 assertion-level mapping 落地，见 B1） |
| C4 | F4 voice 是否会诱导恢复 ambient？ | **P**（probe warning-only + 禁止恢复 ambient；但 allowed_equivalents 需收紧，见 B2） |
| C5 | F6 多台阶是否可自动测？ | **P** |
| C6 | F7 混合 CSV 是否真实且可测？ | **P** |
| C7 | F8/F9 分家是否降低 static 刷分？ | **P** |
| C8 | 是否存在仍严重 GPT 口味的题？ | **U** — F12 reason 枚举仍有软偏置，但 4 分权重够低 |
| C9 | 题量是否导致评测过贵/过慢？ | **P** |
| C10 | 是否应从 capstone 选 1-2 题进 V4.0？ | **P**（推迟到 V4.1，先看校准结果） |
| C11 | capstone 若加入能否避免连坐？ | **P** |

### D. Seed / 提示

| # | 检查项 | P/F/U |
|---|--------|-------|
| D1 | public 绿 + hidden 红的 broken 标准是否成立？ | **P** |
| D2 | 脏库策略是否避免 public 必红？ | **P**（设计已含；但路径需明确隔离，见 B4） |
| D3 | ONBOARDING 去剧透是否足够？ | **F** — 遗漏 api_contracts.md 第 49 行剧透，见 B3 |
| D4 | probe warning 是否泄漏过多解法？ | **P** |
| D5 | 保留 PR 模板 vs answer.md 是否合理？ | **P** |

### E. 流水线

| # | 检查项 | P/F/U |
|---|--------|-------|
| E1 | artifact 列表是否完整可复盘？ | **P** |
| E2 | blockers/score_draft 契约是否可实现？ | **P**（但 hidden_summary 需支持 assertion-level，见 B1） |
| E3 | build skipped 是否被防白送分？ | **P** |
| E4 | 实施切分 PR-A..E 是否合理？ | **P**（PR-B 需标注 static 改写风险，见 B5） |
| E5 | score_draft_confidence / unscored_items 是否足以区分正式 V4 run 与历史 relabel？ | **P** |

### F. 反偏置与历史

| # | 检查项 | P/F/U |
|---|--------|-------|
| F1 | 十条纪律是否可执行？ | **P** |
| F2 | 跨模型试跑门禁是否必要/过重？ | **P** |
| F3 | 重标注误差带 ±3 是否诚实？ | **P** |
| F4 | 附录示例是否显示 82 团被拉开？ | **P**（Kimi K2.7 88 vs Composer 83 差距明确） |
| F5 | 冻结前是否要求门槛聚集审计？ | **P** |

---

## Blocking 项总结

| # | 项 | 优先级 | 状态 |
|---|-----|--------|------|
| B1 | hidden test 支持 assertion-level mapping（F3/F12 拆分落地） | **高** | 已修改 03/05 |
| B2 | F4 allowed_equivalents 收紧（防绕过 session 授权） | **高** | 已修改 03 |
| B3 | api_contracts.md 第 49 行去剧透 | **中** | 已修改 04 |
| B4 | 脏库注入路径与 public DB 隔离 | **中** | 已修改 04 |
| B5 | PR-B static 检查器改写风险标注 | **中** | 已修改 07 |

以上 5 项已直接修改对应 V4 设计文档。

---

*审核模型: GLM-5.2 | 渠道: Opencode/API | 日期: 2026-07-11*
