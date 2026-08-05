# Qwen3.7 Max 交叉审核意见

## 总裁决

**有条件同意。**

V4 的核心设计方向经 5 份已有交叉审核、3 轮实测数据（V1/V2/V3.1）和 V2 soft-cap 实验榜反复验证是正确的。Ship/Ability 双轨、F3/F12 拆分、F8/F9 分家、取消 F3e 数值顶、Ability 主序——这些收敛项我不再重复论证。

本审核的定位是**第 6 份独立视角**，重点攻击前 5 份审核未充分覆盖的 5 个实施层面问题，并对已收敛项做独立确认或提出微调。

---

## 必须修改（blocking）

### B1. assertion-level mapping 的 Python 实现方案需要具体化，当前设计停留在接口规格层

**问题**

GLM-5.2 B1 和 MiniMax-M3 B1 已正确识别了 `test_context_policy.py` 混合断言 behavior 和 reason 的问题，并提出了方案 A（拆分函数）和方案 B（单函数内分步）。`03_ITEM_BANK.md §0` 也已写入这两种方案。

但实际看 V2 代码（`test_context_policy.py` 第 25-119 行），5 个 test 函数使用标准 `unittest.TestCase` + `assertEqual`/`assertFalse`。要实现 assertion-level 报告，**不是改 test 函数就够的**——`run_hidden_tests.py` 也需要知道如何把 assertion-level 结果聚合成 item-level 结果。当前设计文档只定义了 `hidden_summary.json` 的输出格式（`05 §4.2`），但没有定义 `run_hidden_tests.py` 的**内部接口**。

具体缺失：

1. **方案 A 的 test discovery 问题**：拆分为 `*_behavior` 和 `*_reason` 后，test 函数数量从 5 翻倍到 10+。`run_hidden_tests.py` 当前用 `unittest.TestLoader().loadTestsFromTestCase()` 加载，自动发现所有 `test_*` 方法。这本身没问题，但 `item_registry.json` 需要知道哪些 test 方法属于同一个逻辑场景（例如 `test_unauthenticated_behavior` 和 `test_unauthenticated_reason` 都源自同一个 V2 test），才能正确聚合到 family 分。**`item_registry.json` 当前没有 `test_group` 或 `scenario_id` 字段来表达这种分组。**

2. **方案 B 的 assertion 捕获问题**：如果保留单一 test 函数但内部分步，需要用 `try/except AssertionError` 包裹每组断言。但 Python unittest 的 `self.assertEqual` 失败时直接抛 `AssertionError` 终止函数——要"分步收集"就必须把每组断言包在独立 try/except 中，然后把结果写到一个 side-channel（如 `self._item_results`）。这**不是标准 unittest 模式**，容易出 bug（例如某个 behavior 断言失败后，后续 reason 断言可能访问不存在的 key 导致 `KeyError` 而非 `AssertionError`）。

**修改建议**

1. **推荐方案 A**（拆分函数），因为它是标准 unittest 模式，不需要 hack。
2. `item_registry.json` 增加 `scenario_id` 字段：

```json
{
  "V4-F3-01": {
    "scenario_id": "unauthenticated_context",
    "assertion_keys": ["allowed", "target_patient", "memory_items", "sleep", "brief"],
    "test_method": "test_unauthenticated_context_behavior",
    ...
  },
  "V4-F12-01": {
    "scenario_id": "unauthenticated_context",
    "assertion_keys": ["reason"],
    "test_method": "test_unauthenticated_context_reason",
    ...
  }
}
```

3. `run_hidden_tests.py` 加载 registry，按 `test_method` 匹配 test 结果，按 `scenario_id` 聚合 family 分。不需要改 unittest 框架本身。
4. **PR-B 验收标准**补充：除了 GLM-5.2/MiniMax-M3 已写的 Grok-4.5/GPT-5.5 回归外，还需要验证 `item_registry.json` 的 `scenario_id` 分组正确——即同一个 scenario 的 behavior 和 reason test 结果能正确聚合。

### B2. F6 migration 的 broken seed fixture 规格缺失

**问题**

V4 的 F6 从 V2 的 8 分扩展到 10 分，新增了 F6c（ts 回填，2 分）和 F6e（混合排序，2 分），来源于 V3.1。`04_SEED_AND_PROMPT.md §2.2` 说注入"旧版 `care_events` 样例库"，但**没有指定旧表缺哪些列**。

V2 的 `test_db_migration.py` 只测了"旧表不崩"和"补列"两个维度。V4 新增的 F6c 要求 `ts` 从 `created_ts` 回填——这意味着 broken seed 的旧 `care_events` 表必须：
- 有 `created_ts` 列（否则无法回填）
- **没有** `ts` 列（否则不需要回填）
- 有至少一行旧数据（`created_ts` 有值）

如果 seed 的旧表缺 `created_ts`（而不是缺 `ts`），F6c 就无法测试。如果旧表同时缺两列，模型需要先补 `created_ts` 再补 `ts`，这比 V4 设计的预期更复杂。

**修改建议**

在 `04_SEED_AND_PROMPT.md §2.2` 的注入表中明确旧 `care_events` 表的 schema：

```text
旧表 schema（注入到 data/legacy_sample.db）：
- event_id TEXT PRIMARY KEY
- subject_id TEXT
- room TEXT
- bed TEXT
- event_type TEXT
- notes TEXT
- created_ts INTEGER  -- 有值，用于 ts 回填测试
-- 缺少：ts, severity, caregiver_id（V4 新增列）

旧数据：至少 2 行，created_ts 分别为不同时间戳
```

这样 F6a（不崩）、F6b（补列+数据保留）、F6c（ts 回填）、F6e（混合排序）都有明确的测试基础。

### B3. `run_hidden_tests.py` 的 current-working-directory 依赖可能导致 F4 voice bridge 测试误判

**问题**

F4 voice bridge 的 oracle（`03_ITEM_BANK.md §V4-F4-02`）要求 voice/worker 路径在请求敏感 context 前先获取显式 session。但 V2 的 hidden test 框架（`evaluator/tests/hidden/`）是在 evaluator 目录下运行的，通过 `import_gateway(tmp_path)` 加载候选代码。

如果模型的 voice 模块实现依赖于特定的工作目录、配置文件路径或环境变量（例如 `VOICE_SESSION_ID`），hidden test 的运行环境可能与模型开发时的环境不同，导致 F4 测试失败——不是因为模型没修，而是因为运行环境不匹配。

V2 的 `test_context_policy.py` 不受此影响，因为它只测 `build_chat_context_v3()` 这个纯函数。但 F4 需要测的是 voice/worker 模块的**调用链**，这涉及到模块间的 import 路径和运行时配置。

**修改建议**

1. `03_ITEM_BANK.md §V4-F4-02` 的 oracle 应明确：**hidden test 只检查 voice/worker 模块源码中是否存在显式 session 获取逻辑**（static analysis），或者**通过 mock session 注入来测试调用链**（dynamic test）。
2. 如果选择 dynamic test，`eval_helpers.py` 需要提供 `mock_voice_session()` 工具函数，让 hidden test 可以注入一个已知 session 并验证 voice 模块是否正确使用了它。
3. 如果选择 static analysis，需要定义检查规则（类似 F8 ESP static），并在 `03 §F4` 中标注 `oracle_type: "static"`。

推荐 **dynamic test + mock**，因为它更可靠且与 V4 的"行为 oracle"原则一致。

### B4. `score_model.py` 的 family 分计算逻辑需要防"部分分溢出"

**问题**

V4 的 12 个 family 中，F3（16 分，5 子项）、F5（12 分，6 子项）、F6（10 分，5 子项）都有多个可部分得分的子项。`02_SCORING_SYSTEM.md §9` 说"自动草稿 + 人工终裁"，但 `score_model.py` 的自动草稿如何计算部分分？

例如 F3a（未认证零泄漏，4 分）：如果模型堵了 HTTP 路径但漏了 `build_chat` 内部路径，`02 §3.2` 说"子项可部分得分"。但 hidden test 是二元的（pass/fail）——如果 `test_unauthenticated_context_behavior` 通过了，自动草稿会给 F3a 满分 4 分，即使实际上模型只堵了一半路径。

这意味着 **自动草稿的 Ability 可能系统性偏高**，因为 hidden test 只能抓到"完全没做"，抓不到"做了一半"。人工终裁需要下调，但如果 reviewer 依赖自动草稿作为起点，偏差会被锚定。

**修改建议**

1. `score_draft.json` 中每个 family 的 `draft` 分必须标注 `confidence: "test_only" | "test_plus_review"`。
2. `score_draft_confidence.json` 增加 `overestimate_risk` 字段，列出哪些 family 的部分分可能被高估（基于 hidden test 覆盖率分析）。
3. `reviewer_prompt.md` V4 版增加一节"Partial Credit Audit"：reviewer 必须检查自动草稿中满分 family 是否真的满分，还是 hidden test 覆盖率不足导致的假满分。

### B5. V2→V4 relabel 表中 `review_inferred` 行的置信度应全部标为 `low`，而非部分标 `medium`

**问题**

`APPENDIX_SCORE_EXAMPLES.md` 的 relabel 表中，18 行有 4 行是 `review_inferred`（Composer 2.5、Minimax M3 Opencode、Gemini 3.5 Flash、Minimax M2.5）。MiniMax-M3 S8 建议加 `evidence_source` 列，并说"4 行置信度为 low"。

但实际看这 4 行的数据来源：Composer 2.5 的 V2 review 叙述了"context fallback and old DB migration keep it capped"，但没有结构化的 hidden test 失败列表。这意味着 F3e 扣 5 分、F6 扣 3-5 分、F4 扣 4 分都是**从叙述推断的**，不是从 hidden test 数据计算的。Ability≈83 的误差可能远超 ±3。

更严重的是：如果 V4 实施后用这 4 行做校准锚点（`07 §3.4` 的 5 锚点中包含"原 82 弱"），校准结果会被低置信度数据污染。

**修改建议**

1. relabel 表中 `review_inferred` 行的置信度**全部**标为 `low`，不得用于校准锚点。
2. `07 §3.4` 的 5 锚点选择标准增加：锚点必须有 `hidden_v2_remap` 或 `hidden_v4` 置信度，`review_inferred` 不得作为锚点。
3. 如果"原 82 弱"锚点没有结构化 hidden 数据（如 Composer 2.5），应替换为有结构化数据的样本（如 Minimax M3 WorkBuddy，有 27/34 hidden 数据）。

---

## 建议修改（non-blocking）

### S1. F3 权重从 V2 的 14 分增加到 V4 的 16+4=20 分，需要确认不会放大"单一卡点"效应

V2 rubric 中 "Session/context policy" = 14 分。V4 拆为 F3（16 分）+ F12（4 分）= 20 分。虽然内部分项更细（F3a/b/c/d/e），但 context policy 在总分中的权重实际增加了 43%（14→20）。

这意味着 context policy 仍然是 V4 中**权重最大的单一能力域**（超过 admin/auth 的 12 分、care_event 的 12 分、migration 的 10 分）。如果某个模型在 context policy 上全面失败（F3=0, F12=0），它在 Ability 上直接损失 20 分——这与 V2 的"82 墙"本质上是同一个问题，只是表达方式从 cap 变成了大权重扣分。

**建议**：不需要改分值（F3 的 5 个子项确实覆盖了关键安全场景），但在 `reviewer_prompt.md` V4 版中增加一条自检："F3 总分扣减是否超过 10 分？如果是，必须逐项说明哪些子项完全未实现，而非笼统说'context policy 失败'。"这能防止 reviewer 把 F3 当成新的"一刀切"扣分点。

### S2. PR-B 应增加"assertion-level mapping 验证"作为独立验收步骤

当前 `07_MIGRATION_AND_COMPAT.md §8` 的 PR-B 描述是"hidden 扩展（context 拆分、migration 多 case、mixed CSV、voice），并补 reason-only / ambient-only 夹具"。

但 assertion-level mapping 是 PR-B 中**最关键、最易拖延、最影响后续 PR** 的子任务。如果它被混在"hidden 扩展"里，可能被其他工作挤掉或草率完成。

**建议**：PR-B 拆为两个子步骤：
- **PR-B1**：`item_registry.json` + `test_context_policy.py` 拆分 + `run_hidden_tests.py` 适配 + V2 已知样本回归（Grok-4.5/GPT-5.5 reason-only 失败 → F3 满分 + F12 扣分）
- **PR-B2**：其余 hidden 扩展（F4 voice、F6 多 case、F7 混合 CSV）

PR-B1 必须先完成并通过回归验证，PR-B2 才能开始。

### S3. frozen gold 的创建方式需要明确

MiniMax-M3 S2 提出 `archives/v4_gold/project2_task/` 作为 ground truth，`07 §3.4` 已采纳。但没有说明 frozen gold 从哪来。

选项：
- **(a) 用户手动完成项目到 V4 spec**：最准确，但成本高（需要人类开发者完整修复 broken seed）
- **(b) 用 V2 最佳样本（Grok-4.5 或 GPT-5.5 的提交）作为 proxy**：成本低，但可能有不匹配 V4 新增 item 的 quirks
- **(c) 混合：用 V2 最佳样本 + 人工补齐 V4 新增项（F4 voice、F6 多 case、F7 混合 CSV）**

**建议**：采用选项 (c)。用 Grok-4.5 的 V2 提交作为基础（hidden 33/34，ESP static 8/8，build 通过），然后人工补齐 F4 voice bridge 和 F6 migration 多 case。这样 frozen gold 的 Ability 预期 ≥95，且与 V4 新增 item 对齐。

### S4. `eval_helpers.py` 需要 V4 适配

当前 `eval_helpers.py` 提供 `TempProjectTestMixin`、`import_gateway()`、`now_ms()` 等工具。V4 新增的 F4 voice bridge 和 F6 migration 多 case 可能需要新的 helper：

- `mock_voice_session()`：为 F4 测试注入已知 session
- `create_legacy_db()`：为 F6 测试创建旧 schema 数据库
- `import_voice_module()`：加载候选的 voice/worker 模块

**建议**：在 PR-B1 中同步更新 `eval_helpers.py`，确保新 hidden test 有可靠的测试基础设施。

### S5. V4 run 估时应区分"有 IDF 环境"和"无 IDF 环境"

`05 §3` 估时 15-25 分钟。但这个范围包含了 ESP build（5-10 分钟）。对于无 IDF 环境的实验室，实际估时是 10-15 分钟。

**建议**：`05 §3` 分两行：
- 有 IDF 环境：20-25 分钟（含 build）
- 无 IDF 环境：10-15 分钟（build 跳过）

校准阶段 5 锚点 × 1 轮 = 1.5-2 小时（不含人工 review）的估算不变。

---

## 同意的亮点

1. **V2 作为唯一基底**：3 轮数据证明 V1 测不同维度、V3.1 被 cap 绑架，V2 是最稳定的基线。
2. **Ship/Ability 双轨**：soft-cap 实验榜是铁证，82 团内部有 81.2-88.0 的巨大差距。
3. **F3/F12 拆分**：Grok-4.5 的 reason-only 失败案例是最有力的论据。
4. **F8/F9 分家**：Mimo Flash 和 Minimax M2.5 的 static 满分 + build 失败案例是反面教材。
5. **取消 F3e 数值顶**：5 份审核一致收敛，82 墙不能换成 89 墙。
6. **Ability 主序**：评测目标是工程完成度，Ship/Class 是发布参考。
7. **行为 oracle + allowed_equivalents**：反出题偏置的有效纪律。
8. **门槛聚集审计**：直接针对 V3.1 的病因。
9. **5 份已有审核的收敛效率高**：8 个 blocking 项在 5 轮审核中逐步落实，说明交叉审核流程有效。

---

## 对开放争议点的投票

| 争议 | 选择 | 理由 |
|------|------|------|
| F3e Ship 顶 89 / 取消 / 改值 | **取消数值顶，仅 Class B+** | 5 份审核已收敛；Class 表达发布风险，Ability 扣 5 分拉开差距 |
| 主榜排序 Ship 优先 vs Ability 优先 | **Ability 降序为主榜** | 评测目标是工程完成度 |
| 无 IDF 时 F9 给 2–3 分是否公平 | **固定 3 分，不缩分母** | 分母缩放引入口径混乱，3/6 对排序影响 <0.5 分 |
| sketch_jan22a 保留 vs 移除 | **保留** | 真实仓库噪声；顶部模型不依赖它 |
| 重复 CSV 幂等是否纳入 V4.0 | **不纳入** | V4.0 题库已 40+ 项 |
| 是否加入高耦合 capstone | **V4.0 不加；≥3 人 Ability≥96 或 top3 极差<2 则 V4.1 必加** | 与 MiniMax S7 收敛 |
| Ability 是否允许人工 ±2 | **允许，强制写具体理由** | 自动证据不能替代架构审查 |
| F12=4 是否合理 | **合理** | 4 分让顶部有梯度但不决定中游 |
| F1 是否引入 git 时间戳自动扣分 | **不引入** | 时序不可信，降到 notes |
| assertion-level mapping 方案 A vs B | **方案 A（拆分函数）** | 标准 unittest 模式，不需要 hack |
| frozen gold 创建方式 | **选项 (c)：V2 最佳样本 + 人工补齐 V4 新增项** | 成本低且与 V4 item 对齐 |

---

## 风险与可实施性

### 高风险

1. **assertion-level mapping 的 Python 实现**（B1）。这是 5 份审核一致认定的最关键实施问题。本审核补充了 `scenario_id` 字段和 test discovery 的具体实现路径。如果 PR-B1 不做 regression 验证，F3/F12 拆分会停在纸面。

2. **F6 migration fixture 规格缺失**（B2）。如果 broken seed 的旧表 schema 不对，F6c（ts 回填）和 F6e（混合排序）无法测试，10 分变 6 分。

3. **评分实现漂移**（继承 5 份审核的一致风险）。reviewer_prompt 必须硬编码 Ability 主序 + 部分分审计。

### 中风险

4. **F4 voice bridge 测试环境不匹配**（B3）。hidden test 运行环境与模型开发环境不同，可能导致假失败。需要 mock session 注入。

5. **自动草稿系统性偏高**（B4）。hidden test 二元判定无法抓"做了一半"，部分分可能被高估。需要 `overestimate_risk` 字段。

6. **relabel 低置信度数据污染校准**（B5）。`review_inferred` 行不得作为校准锚点。

### 低风险

7. **PR-A→PR-E 切分合理**，但 PR-B 应拆为 B1（assertion-level）和 B2（其余扩展）。
8. **V2 relabel ±3 误差带诚实**，前提是 `review_inferred` 行标 `low` 且不用于校准。

---

## 检查清单逐项

### A. 目标一致性

| # | 检查项 | P/F/U |
|---|--------|-------|
| A1 | V4 是否清楚以 V2 为基底而非 V3.1 树？ | **P** |
| A2 | 是否明确解决 82 墙，而非用新 cap 换墙？ | **P** |
| A3 | 是否保留信任类重罚？ | **P** |
| A4 | 非目标是否足够（无硬件、不混 V1 分）？ | **P** |
| A5 | 成功标准是否可判定？ | **P** |

### B. 评分体系

| # | 检查项 | P/F/U |
|---|--------|-------|
| B1 | F1–F12 加总是否为 100？ | **P** |
| B2 | 仅 ambient 失败时，是否仍能在 Ability 上区分？ | **P** |
| B3 | F3e Ship≤89 是否可接受？ | **P**（已取消） |
| B4 | F12=4 是否合理？ | **P** |
| B5 | Hard cap 列表是否过宽/过窄？ | **P** |
| B6 | Release Class 是否与分数重复或互补清晰？ | **P** |
| B7 | 渠道强制列是否足够抑制工具噪声？ | **P** |
| B8 | 自动草稿 + 人工终裁职责是否清楚？ | **P**（B4 补充部分分审计） |
| B9 | 是否强制双视图？ | **P** |
| B10 | reason-only 是否只进 F12？ | **P**（实施需 B1 落地） |

### C. 题库

| # | 检查项 | P/F/U |
|---|--------|-------|
| C1 | 是否 ≥12 个低耦合中等权重点？ | **P** |
| C2 | 高分值题是否行为 oracle？ | **P** |
| C3 | F3 与 F12 拆分是否避免误判？ | **P**（B1 落地路径已明） |
| C4 | F4 voice 是否会诱导恢复 ambient？ | **P**（B3 补充测试环境） |
| C5 | F6 多台阶是否可自动测？ | **P**（B2 补充 fixture 规格） |
| C6 | F7 混合 CSV 是否真实且可测？ | **P** |
| C7 | F8/F9 分家是否降低刷分？ | **P** |
| C8 | 是否存在 GPT 口味题？ | **U** — F12 有软偏置但 4 分够低 |
| C9 | 题量是否过贵/过慢？ | **P** |
| C10 | capstone 时机？ | **P**（V4.1 触发条件已定） |
| C11 | capstone 能否避免连坐？ | **P** |

### D. Seed / 提示

| # | 检查项 | P/F/U |
|---|--------|-------|
| D1 | public 绿 + hidden 红？ | **P** |
| D2 | 脏库策略避免 public 必红？ | **P** |
| D3 | ONBOARDING 去剧透？ | **P**（api_contracts 改写已收敛） |
| D4 | probe warning 不泄漏解法？ | **P** |
| D5 | PR 模板 vs answer.md？ | **P** |

### E. 流水线

| # | 检查项 | P/F/U |
|---|--------|-------|
| E1 | artifact 列表完整？ | **P** |
| E2 | blockers/score_draft 契约可实现？ | **P**（B1 补充 scenario_id） |
| E3 | build skipped 防白送分？ | **P** |
| E4 | PR 切分合理？ | **P**（S2 补充 PR-B 拆分） |
| E5 | confidence / unscored 区分？ | **P**（B5 补充 relabel 置信度） |

### F. 反偏置与历史

| # | 检查项 | P/F/U |
|---|--------|-------|
| F1 | 十一条纪律可执行？ | **P** |
| F2 | 跨模型试跑门禁？ | **P** |
| F3 | ±3 误差带诚实？ | **P** |
| F4 | 附录显示 82 团被拉开？ | **P** |
| F5 | 门槛聚集审计？ | **P** |

### G. 实施完整性（本审核新增）

| # | 检查项 | P/F/U |
|---|--------|-------|
| G1 | assertion-level mapping 有具体 Python 实现方案？ | **F** — B1 补充 scenario_id + 方案 A 推荐 |
| G2 | F6 broken seed fixture 有明确 schema？ | **F** — B2 补充旧表规格 |
| G3 | F4 voice test 环境匹配？ | **U** — B3 补充 mock session |
| G4 | 自动草稿部分分溢出防护？ | **F** — B4 补充 overestimate_risk |
| G5 | relabel 低置信度不污染校准？ | **F** — B5 补充锚点选择标准 |

---

## Blocking 项总结

| # | 项 | 优先级 | 状态 |
|---|-----|--------|------|
| B1 | assertion-level mapping 具体化（scenario_id + 方案 A + test discovery） | **P0** | 待修改 03/05 |
| B2 | F6 broken seed fixture schema 规格 | **P0** | 待修改 04 |
| B3 | F4 voice test 环境匹配（mock session） | **P1** | 待修改 03 |
| B4 | score_model.py 部分分溢出防护 | **P1** | 待修改 05 |
| B5 | relabel review_inferred 置信度全部标 low + 不得作锚点 | **P1** | 待修改 07/附录 |

B1/B2 为 P0（不解决则 PR-B1 无法起步）；B3/B4/B5 为 P1（不解决则校准结果不可信）。

---

*审核模型: Qwen3.7 Max | 渠道: Opencode/API | 日期: 2026-07-11*
