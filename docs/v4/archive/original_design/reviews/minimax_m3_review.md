# MiniMax-M3 交叉审核意见

## 总裁决

**有条件同意。**

V4 的核心方向经三轮数据和 4 份已有交叉审核反复验证是正确的：以 V2 工程壳为唯一基底，用 Ship/Ability 双轨 + 阻断标签替代 hard cap 主导排序，F3/F12 拆分解决「reason-only 误当安全失败」，F8/F9 分家防止 static marker 工程师刷分。这与 v2 soft-cap 实验榜（82 团实际摊到 81.2–88.0）和 v3.1 总分榜失败（前 9 名挤在 82.5–84.0）的教训完全吻合。

本审核在前 4 份审核（Codex / DeepSeek / Kimi K2.7 / GLM-5.2）已经收敛的 8 项 blocking 之上，重点审视**实施层面的具体落地风险**——尤其是 V2 现有 hidden test 代码、reference 契约、ESP static 检查器这三处与 V4 题库设计之间的具体差距，并补充 4 份审核未充分讨论的 4 个设计空白（端到端定义边界、frozen gold、回滚条件、运行时长预算）。以下 5 项 P0 解决后，V4 可以进入 PR-A 实施阶段；其余 P1/P2 排期即可。

---

## 必须修改（blocking）

### B1. F3/F12 拆分在 hidden test 层面目前根本无法落地

**问题**

V4 设计在 `02_SCORING_SYSTEM.md §3.4` 和 `03_ITEM_BANK.md §0` 明确要求：

> 已正确拒绝且零泄漏但 reason 错 → F3 行为分保留，只扣 F12。

但当前 V2 的 `evaluator/tests/hidden/test_context_policy.py` 在同一 test 函数中用 `assertEqual` 混合断言行为和 reason 字符串。以 `test_unauthenticated_context_does_not_leak_patient_data`（第 25–34 行）为例：

```python
self.assertFalse(ctx["policy"]["allowed"])                     # F3a 行为
self.assertEqual(ctx["policy"]["reason"], "not_authenticated") # F12 reason
self.assertEqual(ctx["target"]["patient"], {})                 # F3a 行为
```

整个文件 5 个 test 函数（`test_unauthenticated_context_does_not_leak_patient_data`、`test_patient_cannot_access_other_patient`、`test_expired_session_is_not_authenticated`、`test_session_without_actor_subject_is_not_authorized_for_patient`、`test_sensitive_target_context_requires_explicit_session`）都是同一结构。`run_hidden_tests.py` 只能按 test 函数粒度报告，reason 错即整 test 失败——**F3 行为分和 F12 永远会一起丢，F12 降权只是纸面**。

GLM-5.2 B1 已发现此问题并提出按 `assertion_keys` 拆分的方向；本审核进一步要求**写明 PR-B 的具体落地路径**，避免实施时停在「评分管线改造、hidden test 不动」的假落地状态。

**修改建议**

1. `test_context_policy.py` 重构为两类函数：
   - `*_behavior` 系列：只断言 `allowed` / `target.patient` / `target.assignment` / `modalities.memory.items` / `modalities.sleep` / `brief`
   - `*_reason` 系列：只断言 `policy.reason`
   - 或者保留单一 test 函数但内部分两步判定：先收集行为断言，输出 `items[V4-F3-XX]`；再收集 reason 断言，输出 `items[V4-F12-XX]`
2. `05_EVALUATOR_PIPELINE.md §4.2` 的 `hidden_summary.json` record 格式从「一个 test → 一个 item」改为「一个 test → 多个 item，每个 item 绑定 `assertion_keys`」
3. `run_hidden_tests.py` 实现支持按 assertion key 报告，需要新加一个回调钩子或在现有 unittest 框架上包一层 item-level 报告
4. `item_registry.json` 必须先实现（`05 §9` 已设计），hidden 跑完才能映射；不可反过来先写 hidden 再补 registry
5. 实施后必须用 V2 历史样本回归：
   - Grok-4.5 唯一失败是 `session_without_actor_subject` 的 reason code → V4 下 F3d 应满分、F12 扣 1–2 分
   - GPT-5.5 同样问题 → 同样回归
   - 这是断言级别 mapping 真的落地的唯一验收标准

**影响范围**

`test_context_policy.py` 全部 5 个测试函数 + `run_hidden_tests.py` 整体 + `item_registry.json` + `scoring/score_model.py` 4 个文件。属于 PR-B 范围内最关键、最易拖延的子任务。

---

### B2. `reference/api_contracts.md` 第 49 行同时剧透了 F3e 的解法与参数名

**问题**

`workspace/reference/api_contracts.md` 第 49 行：

> 面向指定患者的敏感上下文必须携带显式有效 `session_id`。不能因为系统里存在最近一次 current session，就在缺少 `session_id` 的请求中自动放行患者数据。

这句话有三重剧透：

1. 直接告诉模型 ambient fallback 不合法
2. 直接命名 `session_id` 参数
3. 命名 "current session" 机制

V4 的设计意图是让模型自己推理出会话语义，而不是从契约里读到答案。GLM-5.2 B3 已提了改写，但 `04_SEED_AND_PROMPT.md §5.1` 当前改写版（"敏感上下文请求需携带可靠会话标识"）仍不够彻底——"需携带可靠会话标识"是另一种话术上的「带 session_id」。

**修改建议**

`04_SEED_AND_PROMPT.md §5.1` 改写后的版本应只描述"三要素决定授权"，不指向任何具体参数名或机制：

> 敏感上下文请求需满足授权条件；授权由会话、actor、target 三者关系决定；具体拒绝情形与契约见上节 `/api/v3/sessions` 与 `/api/v3/identity/gallery` 的失败响应。

改写后必须用 V2 历史样本回归：

- GLM-5.2 (95) / Doubao (86) / Grok-4.5 (96) 在 V2 都过 F3e → 改写后这三家若仍过、且 Kimi K2.7 / LongCat / Composer 等 V2 翻车样本继续翻车，才证明改写有效
- 不通过：任一家 V2 过的样本改写后反而挂、说明新文案有"反暗示"问题，需要回滚

---

### B3. F8-07 static 检查器改写有「宏展开」和「uncertain 时人工 final」两条护栏缺失

**问题**

`03_ITEM_BANK.md §F8-07` 当前 allowed_equivalents：

> 动态分配（`malloc`/`new`/`std::string`/`std::vector`）或显式足够大（>512B）的固定缓冲均视为正确；间接宏定义（如 `#define TOF_BUF_SIZE 256`）若 static 无法解析，留待 F9 build 暴露。

但 F9 的语义是「真实 ESP-IDF build 跑通」——若模型用了 `#define TOF_BUF_SIZE 256` 写小间接宏、且用户没有 IDF 环境，**F8-07 不会被 static 抓到、F9 也不会触发 build 失败**。结果是这道 1 分既不被扣、也不得分，audit 出来变成漏判。Mimo Flash v2 static 7/8 但 build 失败就是这个机制。

4 份审核都标注了 F8 改写风险，但只有 GLM-5.2 B5 提了"过宽/过紧"两面，没有写明"uncertain 时归谁"。

**修改建议**

在 `03_ITEM_BANK.md §F8-07` 实施约束中明确：

1. static 检查器对 `char buf[N]` 字面量：直接按 N ≤ 512 判 `E-contract`
2. 对 `char buf[TOF_BUF_SIZE]` / `#define N 256` 形态：必须用 clang `-E` 风格或简单正则展开宏；不能因为"static 看不到"就豁免
3. 仍无法解析时：`score_draft.json` 记 `f8_07_status: "uncertain"`，由人工 final 判定；不得自动记过、也不得自动扣分
4. 回归样本：Grok-4.5 8/8 / DeepSeek Pro 5/8 / LongCat 5/8 这三个 V2 已知点改写后分值不应突变 ±1 以上

---

### B4. F3e Ship 数值顶必须取消

**问题**

v2 soft-cap 实验榜已证明：仅 ambient fallback 一个失败点就把 8–10 个不同模型压到同一 82。V4 如果保留 `min(ship, 89)` 这个数值顶，**会把 82 墙平移成 89 墙**。Class B+ 已经准确表达了「不可 A 类发布」的语义。

**修改建议**

`02_SCORING_SYSTEM.md §4.3` 默认门槛数值表更新为：

```diff
- | 过 F3a/b 但未过 F3e | min(ship, **89**)，Class 不得为 A |
+ | 过 F3a/b 但未过 F3e | **不设 Ship 数值上限**；Class 不得为 A，标记 B+ |
```

F3e 仅作 blocker 标签 + Class 表达，数值上 Ability 扣 5 分后其余 family 差异自然摊开。这是 3 份已有审核（DeepSeek B1 / Kimi B1 / GLM-5.2 投票）已收敛项，本审核完全同意。

---

### B5. 默认主榜必须明确为 Ability 降序，且写进 00 硬约束

**问题**

`02_SCORING_SYSTEM.md §2.1` 当前说「正式报告必须同时给两张视图」，但没有指定默认主排序。如果实施者或 report 工具默认按 Ship 排序，B4 取消数值顶的效果会被抵消——Ability 88 与 Ability 83 只要都带 `S-ambient` 就会贴在一起。

DeepSeek S1 / Kimi B2 / GLM-5.2 投票均已收敛到 Ability 优先，但只放在 review 投票里，没有写进 00 简报作为硬约束。

**修改建议**

1. `02_SCORING_SYSTEM.md §2.1` 主榜列定义写明：默认按 Ability 降序，同 Ability 按 Ship 降序
2. `00_DESIGN_BRIEF.md` 加一条 G8 目标或决策项：「官方主榜默认按 Ability 排序；Ship/Class 作为并列信息列；Release view 为按需生成的第二视图」
3. `evaluator/scoring/reviewer_prompt.md` V4 版硬编码此规则，并设自检问题「你的报告是否把 Ship 当主排序器？」

---

## 建议修改（non-blocking）

### S1. 端到端定义边界：model/channel/harness 归一化

`02 §2.1` 列了主榜字段 `channel/harness/model`，但没定义这三者如何归一化。V2 实际数据中：

- GLM-5.2 API (95) / GLM-5.2 Volcengine/Opencode (89) / GLM-5.2 WorkBuddy (88) 是同 model 不同 channel/harness
- 当前按 3 行报

建议在 `05_EVALUATOR_PIPELINE.md §4.1` 的 `meta.json` 中明确：

```text
同 model + 同 channel + 不同 harness → 分行（WorkBuddy vs Opencode/API 反映 harness 噪声）
同 model + 不同 channel → 分行（API vs Volcengine 是同 harness 不同传输）
同 model + 同 harness + 同 channel 不同次跑 → 合并为最近一次 + N 次历史分布（runs: [latest, prev1, prev2]）
```

不归一化会出现"GLM-5.2 95 还是 89 还是 88"的口径混乱。

### S2. 增加 frozen gold 锚点定义

`07_MIGRATION_AND_COMPAT.md §3.4` 提了校准重跑用 5 个锚点（顶部 / 近顶 / 原 82 强 / 原 82 弱 / 信任失败），但没说 frozen gold 是什么。V2 没有"已完成版项目"作为 ground truth。

建议在 `07 §3.4` 后补：

- `archives/v4_gold/project2_task/` 保留一份与 broken seed 对照的"已知完成版"，作为 Ability ≥ 95、Ship ≥ 95、Class A 的基准
- 这是 PR-A（评分管线）落地后的第一个自测夹具
- frozen gold 不进入公开候选包，仅供 evaluator 内部使用

### S3. 加 V4 回滚条件 3 条

V4 改动非常大（评分结构、hidden、seed、test runner、rubric 全部动）。如果上线后发现某个 family 分值系统性地偏，回滚条件是什么？

建议在 `07_MIGRATION_AND_COMPAT.md §7` 风险表后加：

- **回滚条件 1**：校准 5 锚点与人工分差 > ±5 分（说明自动草稿不可信）
- **回滚条件 2**：top3 Ability 极差 < 1（说明双视图或 Ability 主序未生效）
- **回滚条件 3**：F3/F12 拆分落地后，relabel 与重跑差 > ±3（说明 assertion-level mapping 噪音大）

任一条件触发即冻结 V4 实施、回滚到 V2 seed 与当前 V2 rubric（不是 V3.1）。

### S4. V4 run 估时写入 05

`05_EVALUATOR_PIPELINE.md §3` 步骤顺序没有写完整 V4 run 的预估时长。按 V2 hidden 文件规模经验（8 个 test 文件、~30 个 test 函数），完整 hidden + static + build 跑一次约 5–15 分钟。V4 增 F4 voice bridge、F6 多 case、F7 混合 CSV 后估 15–25 分钟。仍可接受，但 7 份设计文档没写明。

建议 `05 §3` 加一句"完整 V4 run 估时 15–25 分钟，作为人工 review 排期依据"，并写明 V4 校准阶段 5 锚点 × 1 轮 = 1.5–2 小时。

### S5. F1 不引入 git 时间戳自动扣分（与 Kimi B3 一致）

`02 §3.4 F1` 当前 4 个子项，DeepSeek B3 建议加时序验证。**反对**——与 Kimi B3 一致：

- git 时间戳可被 `git commit --amend --date` 随意设置
- 大量模型在修复过程中不频繁 commit
- harness（Qoder / WorkBuddy）会压缩或重置上下文，commit 时间戳与本地 public 运行时间没有稳定对应关系

时序异常可降级到 `score_draft_confidence.json` 的 `notes` 或人工 review 提示，**不进 F1 oracle 自动扣分**。

### S6. F9 固定 3 分（不缩分母）

`02 §3.4 F9` 当前是 2–3 分区间。Kimi S1 / DeepSeek B2 / GLM-5.2 投票均已收敛到固定 3 分 + `f9_mode: "skipped_env"` 标记。

**同意**固定 3 分。**不同意**「分母缩小到 94」的替代方案：分母缩放在传播时引入"GLM-5.2 95 是 95/100 还是 95/94"的口径混乱，F9 满分 6、skip 给 3，差距仅 3 分，对 100 分 Ability 排序影响 < 0.5 分。

### S7. capstone 触发条件加 "top3 极差 < 2"

`00_DESIGN_BRIEF.md G1` 当前："若 V4.0 校准跑完成后 ≥ 3 个模型 Ability ≥ 96，则 V4.1 引入 1 个 capstone 防止顶部拥挤"。

仅这一条太松。可能出现 2 人 96、1 人 95 仍顶部拥挤但条件不触发。建议加：

> **或** V4.0 校准跑完成后 top3 Ability 极差 < 2，则 V4.1 必加 1 个 capstone。

### S8. relabel 表格加 evidence_source 列

`APPENDIX_SCORE_EXAMPLES.md` 的重标注表已很好，但每行应加 `evidence_source` 列区分：

- `hidden_v4`：V4 新增 item 实测
- `hidden_v2_remap`：V2 hidden 结果映射
- `review_inferred`：从 review 叙述推断

这有助于 `score_draft_confidence.json` 的置信度判定，也让 relabel 与重跑差一目了然。

### S9. reviewer_prompt V4 版加 "Hall of Shame"

`evaluator/scoring/reviewer_prompt.md` 当前是 V2 版本。V4 实施时需新增一节明确：

- reason-only 失败不得扣 F3 行为分
- 已正确拒绝且零泄漏但 reason 错 → F3 对应子项满分，只扣 F12
- 不得因 reason 字符串错误生成 S-* behavior blocker
- 「像不像参考实现」不作为扣分依据

具体内容可参考 DeepSeek S5 的常犯错误速查表。

---

## 同意的亮点

1. **V2 作为唯一基底是正确选择**。V1 测的是不同维度（主动性），V3.1 被 cap 绑架。V2 的 24+ 模型验证是最稳定的基线。
2. **Ship/Ability 双轨是核心洞见**。V2 soft-cap 实验榜是铁证：同样 82 分下面藏着 81.2–88.0 的能力差异。
3. **F3/F12 拆分解决了 V2 最不公平的扣分**。Grok-4.5 在 V2 中 hidden 33/34，唯一失败是 reason code——模型正确拒绝了且零泄漏，只因 reason 写成 `not_authenticated` 而非 `not_authorized_for_target` 就被扣到和"未认证泄漏"同级。V4 下只扣 F12 的 4 分。
4. **F8/F9 分家防止 static marker 工程师刷分**。V2 中 Mimo Flash static 7/8 但真实 build 失败、Minimax M2.5 static 8/8 但 build 失败——这两个案例证明 static 满分 ≠ 构建可信。
5. **行为 oracle + allowed_equivalents** 是反出题偏置的有效纪律。
6. **信任类 hard cap 保留得当**。public 崩、改测试、构建造假、报告欺诈——这些在任何评测框架下都应重罚。
7. **item bank 的 12+ 低耦合中等权重点**（F3a/b/e, F4, F6a/c, F7-07/08, F8-07, F9, F2-03）有效避免了 V1 中 auth 连坐的失败模式。
8. **`score_draft_confidence.json` + `unscored_items`** 机制把"自动推断"和"人工确认"的边界显式化。
9. **门槛聚集审计**（06 §2.11）直接治疗 V3.1 的病因——cap 变成排序器。
10. **4 份已有交叉审核已收敛大部分 blocking 项**。Codex 提出双视图、DeepSeek 提出 F3e 取消数值顶、Kimi 提出 F1 不引入 git 时序扣分、GLM-5.2 提出 assertion-level mapping 与 api_contracts 剧透——这些 blocking 项已在前 4 份审核中落实。

---

## 对开放争议点的投票

| 争议 | 选择 | 理由 |
|------|------|------|
| F3e Ship 顶 89 / 取消 / 改值 | **取消数值顶，仅 Class B+** | 与 DeepSeek B1 / Kimi B1 收敛；Class 已表达发布风险，数值顶只会制造 89 墙 |
| 主榜排序 Ship 优先 vs Ability 优先 | **Ability 降序为主榜** | 与 DeepSeek S1 / Kimi B2 收敛；测的是工程完成度，Ship/Class 作发布参考 |
| 无 IDF 时 F9 给 2–3 分是否公平 | **固定 3 分，不采用分母缩放** | 3/6 = 50% 对 100 分 Ability 排序影响 < 0.5 分；分母缩放引入额外口径混乱 |
| sketch_jan22a 保留 vs 移除 | **暂保留** | 真实仓库噪声；顶部模型不依赖它，中等模型可获线索 |
| 重复 CSV 幂等是否纳入 V4.0 | **不纳入** | V4.0 题库已 40+ 项，幂等适合 V4.1 |
| 是否加入高耦合 capstone | **V4.0 不加；校准后 ≥3 人 Ability≥96 或 top3 极差<2 则 V4.1 必加** | 与 DeepSeek S4 收敛；加极差条件防 2 人 96+ 但顶部仍拥挤 |
| Ability 是否允许人工 ±2 | **允许，强制写具体理由** | 自动证据无法替代架构/报告审查；但禁止"感觉不对" |
| F12=4 是否合理 | **合理** | V2 中 Grok-4.5/GPT-5.5 仅差 reason 精度，4 分让顶部有梯度但不决定中游 |
| F1 是否引入 git 时间戳自动扣分 | **不引入** | 与 Kimi B3 收敛；时序不可信，降到 `score_draft_confidence.json` notes |

---

## 风险与可实施性

### 高风险

1. **F3/F12 拆分在 hidden test 层面的落地**（B1）。这是本审核发现的最关键实施问题——设计文档写了"行为与 reason 分开计分"，但现有 test 代码不支持按 assertion 拆分。如果 PR-B 只改评分管线不改 test runner，F3/F12 拆分会停留在纸面上。**缓解**：PR-B 必须同时改 `test_context_policy.py` + `run_hidden_tests.py` 支持按 assertion key 报告。

2. **F8 static 检查器改写**（B3）。前 4 份审核都提了，但都没有写明"uncertain 时归谁"。**缓解**：按 B3 写明「宏展开 + uncertain 记 notes 不自动判过」，用 V2 已知样本（Grok-4.5 8/8 vs DeepSeek Pro 5/8 vs LongCat 5/8）做回归验证。

3. **评分实现漂移**（继承前 4 份审核的一致风险）。如果 `score_model.py` 或 reviewer_prompt 在实际使用中又把 Ship gate 当主排序器，V4 复刻 V3.1。**缓解**：B5 写明默认 Ability 优先 + reviewer_prompt 硬编码 + 设自检问题。

### 中风险

4. **F4 voice bridge hidden 测试误杀等价实现**。如果模型直接查本地 DB 而非走 `/api/v3/context/chat`，F4 hidden 测试会失败但模型可能做了正确的事（GLM-5.2 B2 的约束需要精确实现）。**缓解**：hidden test 检测 voice 模块中是否存在显式 actor 校验步骤，而非只检测 API 调用路径。

5. **双视图在对外传播中坍缩为单数**。如果对外只说"GLM-5.2 V4 得分 88"而 88 是 Ship（Ability=89），会丢失设计意图。**缓解**：官方报告模板 Ability 列在 Ship 左侧且加粗。

6. **`api_contracts.md` 改写的回归验证不充分**（B2）。**缓解**：B2 写明改写后必须用 V2 历史样本回归；不通过则回滚文案。

### 低风险

7. **PR-A..PR-E 切分合理**。PR-A（评分管线）必须先落地，然后用旧 V2 seed 跑一次确认 score_draft 与人工差 < 5 分再继续。

8. **V2 relabel 的 ±3 误差带诚实**，只要每行标 `[RELABEL, NOT RERUN]` + S8 evidence_source 列。

9. **V4 run 估时 15–25 分钟** 在大多数实验室可接受，**前提是** 5 锚点校准 + frozen gold 跑完共 1.5–2 小时的人工 review 排期到位。

---

## 检查清单逐项

### A. 目标一致性

| # | 检查项 | P/F/U |
|---|--------|-------|
| A1 | V4 是否清楚以 V2 为基底而非 V3.1 树？ | **P** |
| A2 | 是否明确解决 82 墙，而非用新 cap 换墙？ | **P**（双轨 + Ability 主序解决；F3e 数值顶已由 B4 取消） |
| A3 | 是否保留信任类重罚？ | **P** |
| A4 | 非目标是否足够（无硬件、不混 V1 分）？ | **P** |
| A5 | 成功标准是否可判定？ | **P**（附录示例给出具体可验证场景） |

### B. 评分体系

| # | 检查项 | P/F/U |
|---|--------|-------|
| B1 | F1–F12 加总是否为 100？ | **P** (8+12+16+4+12+10+8+8+6+8+4+4=100) |
| B2 | 仅 ambient 失败时，是否仍能在 Ability 上区分不同完成度模型？ | **P**（F3e 扣 5 分 + 其它 family 差异 ≥5 分区间） |
| B3 | F3e Ship≤89 是否可接受？ | **F** — B4 建议取消数值天花板 |
| B4 | F12=4 是否合理？ | **P** |
| B5 | Hard cap 列表是否过宽/过窄？ | **P**（信任崩坏场景覆盖完整，不含 S-ambient/M-fidelity/reason） |
| B6 | Release Class 是否与分数重复或互补清晰？ | **P** |
| B7 | 渠道强制列是否足够抑制工具噪声误解？ | **P**（但需 S1 端到端定义边界补强） |
| B8 | 自动草稿 + 人工终裁职责是否清楚？ | **P** |
| B9 | 是否强制同时展示 Release view 与 Ability view？ | **P**（B5 已补默认 Ability 优先） |
| B10 | reason-only 是否只进 F12 / semantic_only？ | **P**（设计已含；但实施需 hidden test 改写，见 B1） |

### C. 题库

| # | 检查项 | P/F/U |
|---|--------|-------|
| C1 | 是否 ≥12 个低耦合中等权重点？ | **P**（12+ 明确列出） |
| C2 | 每条高分值题是否行为 oracle 而非命名 cop？ | **P** |
| C3 | F3 与 F12 拆分是否避免「拒绝了仍当安全失败」？ | **P**（核心改进点；B1 落地路径已明） |
| C4 | F4 voice 是否会诱导恢复 ambient？ | **P**（probe warning-only + 禁止恢复 ambient；B2 的契约改写同样去剧透） |
| C5 | F6 多台阶是否可自动测？ | **P** |
| C6 | F7 混合 CSV 是否真实且可测？ | **P** |
| C7 | F8/F9 分家是否降低 static 刷分？ | **P**（B3 补宏展开与 uncertain 护栏） |
| C8 | 是否存在仍严重 GPT 口味的题？ | **U** — F12 reason 枚举仍有软偏置，但 4 分权重够低 |
| C9 | 题量是否导致评测过贵/过慢？ | **P**（S4 写明估时 15–25 分钟） |
| C10 | 是否应从 capstone 选 1-2 题进 V4.0？ | **P**（推迟到 V4.1，先看校准结果） |
| C11 | capstone 若加入能否避免连坐？ | **P** |

### D. Seed / 提示

| # | 检查项 | P/F/U |
|---|--------|-------|
| D1 | public 绿 + hidden 红的 broken 标准是否成立？ | **P** |
| D2 | 脏库策略是否避免 public 必红？ | **P**（GLM-5.2 B4 已修；仍需 PR-C 加回归测试） |
| D3 | ONBOARDING 去剧透是否足够？ | **P**（但 B2 写明 `api_contracts.md` 第 49 行改写后必须 V2 历史样本回归） |
| D4 | probe warning 是否泄漏过多解法？ | **P** |
| D5 | 保留 PR 模板 vs answer.md 是否合理？ | **P** |

### E. 流水线

| # | 检查项 | P/F/U |
|---|--------|-------|
| E1 | artifact 列表是否完整可复盘？ | **P** |
| E2 | blockers/score_draft 契约是否可实现？ | **P**（但 hidden_summary 需支持 assertion-level，见 B1） |
| E3 | build skipped 是否被防白送分？ | **P**（S6 固定 3 分 + `f9_mode` 标记） |
| E4 | 实施切分 PR-A..E 是否合理？ | **P**（B1 标 PR-B 必须同步改 test runner；B3 标 PR-B 需回归样本） |
| E5 | score_draft_confidence / unscored_items 是否足以区分正式 V4 run 与历史 relabel？ | **P**（S8 补 evidence_source 列） |

### F. 反偏置与历史

| # | 检查项 | P/F/U |
|---|--------|-------|
| F1 | 十条纪律是否可执行？ | **P** |
| F2 | 跨模型试跑门禁是否必要/过重？ | **P** |
| F3 | 重标注误差带 ±3 是否诚实？ | **P** |
| F4 | 附录示例是否显示 82 团被拉开？ | **P**（Kimi K2.7 88 vs Composer 83 差距明确） |
| F5 | 冻结前是否要求门槛聚集审计？ | **P** |

### G. 设计完整性（4 份审核未充分讨论的）

| # | 检查项 | P/F/U |
|---|--------|-------|
| G1 | 端到端定义边界（model/channel/harness 归一化） | **U** — S1 建议补 `meta.json` 规则 |
| G2 | frozen gold 锚点定义 | **U** — S2 建议补 `archives/v4_gold/` |
| G3 | V4 回滚条件 | **U** — S3 建议补 3 条回滚条件 |
| G4 | V4 run 估时与人工 review 排期 | **U** — S4 建议补 15–25 分钟估时 |
| G5 | relabel evidence_source 字段 | **U** — S8 建议补 |

---

## Blocking 项总结

| # | 项 | 优先级 | 状态 |
|---|-----|--------|------|
| B1 | hidden test 支持 assertion-level mapping（F3/F12 拆分落地） | **P0 高** | 待修改 03/05 |
| B2 | `api_contracts.md` 第 49 行彻底去剧透 + V2 历史样本回归 | **P0 高** | 待修改 04 |
| B3 | F8-07 static 改写：宏展开 + uncertain 人工 final + 回归样本 | **P0 高** | 待修改 03 |
| B4 | 取消 F3e Ship 数值天花板（仅 Class B+） | **P0 中** | 与 DeepSeek/Kimi 收敛，待核对 02 |
| B5 | 默认主榜 Ability 优先写入 00 硬约束 | **P0 中** | 与 DeepSeek/Kimi 收敛，待修改 00/02 |

以上 5 项 P0 解决后，V4 设计可以进入 PR-A 实施阶段。

P1–P3 共 9 项建议修改见 S1–S9，已在前 4 份审核中部分收敛，本审核补强实施细节。

---

*审核模型: MiniMax-M3 | 日期: 2026-07-11*
