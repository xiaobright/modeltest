# V4 评测流水线与产物

## 1. 设计目标

在 V2 `run_full_eval.py` 基础上扩展为：

1. 证据更全（build、duration、churn、meta）  
2. 机器可汇总 Ability 草稿与 blockers  
3. 渠道可追溯  
4. 仍允许人工终裁  

本文件最初是实施规格；V4.0 已落地并冻结。日常运行以
`evaluator/run_full_eval.py`、`evaluator/scoring/` 和 freeze manifest 为准。

## 2. 目录职责（目标态）

```text
evaluator/
  make_broken_project.py          # 支持 v4 tag / seed
  run_full_eval.py                # 主编排
  run_hidden_tests.py             # item_id / blocker / family
  run_espidf_static_tests.py
  run_espidf_build.py             # Windows EIM 等
  run_espidf_wsl_build.ps1        # 可选保留
  run_espidf_windows_build.ps1
  scoring/
    rubric.md                     # V4 版
    reviewer_prompt.md            # V4 版
    score_model.py                # 新增：草稿分
    item_registry.json            # 新增：item_id → points/blocker
  tests/
    public/                       # evaluator 副本
    hidden/                       # 扩展 item
    espidf_static/
  tools/
    run_debug_probe.py            # evaluator 副本
  results/
    <timestamp>/
      summary.json
      meta.json
      blockers.json
      score_draft.json
      score_draft_confidence.json
      public.log
      debug_probe.log
      hidden.log
      hidden_summary.json
      espidf_static.log
      espidf_static_summary.json
      espidf_build.log            # 若执行
      espidf_build_evidence.json   # build 状态、归档 bin、size、SHA256
      espidf_build_artifacts/
      candidate_diff.patch
      candidate_status.txt
      candidate_log.txt
      pull_request_template.md
```

## 3. full eval 步骤顺序

```text
1. (可选) --reset → make_broken_project
2. evaluator public tests
3. evaluator debug probe
4. hidden tests → hidden_summary.json（含 items，按 assertion key 拆分）
5. espidf static
6. espidf build（正式 run 使用 `--include-espidf-build`）
7. collect git artifacts + duration/churn
8. copy PR template
9. write blockers.json + score_draft.json + score_draft_confidence.json + dimensions.json + summary.json
10. 提示人工：按 reviewer_prompt 写 reviews/<model>_<id>.md
```

**完整 V4 run 估时**（MiniMax-M3 S4）：约 15–25 分钟 / 模型。其中：

- public tests：< 1 分钟
- debug probe：< 1 分钟
- hidden tests（含 F3/F12 拆分后的多 assertion 判定）：5–10 分钟
- espidf static：< 2 分钟
- espidf build（如工具链可用）：5–10 分钟；不可用则跳过
- collect artifacts + 写 JSON：< 1 分钟

V4.0 的 5 个校准锚点已经完成并进入正式成绩榜。冻结后修改 scorer、rubric、
item registry 或关键 hidden tests 时，按 freeze manifest 重新执行 Gold gate，
并评估是否需要重跑锚点。

## 4. 关键 JSON 契约

### 4.1 `meta.json`

```json
{
  "model": "glm-5.2",
  "channel": "opencode-api",
  "harness": "opencode",
  "benchmark": "project2-v4",
  "seed_tag": "project2-v4-broken-seed",
  "operator": "human-id",
  "notes": "",
  "tool_interference": false
}
```

由操作者在跑前/跑后写入；full eval 可 `--meta path`。

**端到端定义边界（MiniMax-M3 S1）**——`model` / `channel` / `harness` 三者归一化规则：

| 场景 | 主榜处理 | 备注 |
|------|---------|------|
| 同 model + 同 channel + 不同 harness | **分行** | WorkBuddy vs Opencode/API 反映 harness 噪声，必须分行 |
| 同 model + 不同 channel | **分行** | API vs Volcengine 是同 harness 不同传输，必须分行 |
| 同 model + 同 harness + 同 channel 不同次跑 | **合并** | 取最近一次主榜 + N 次历史分布（`runs: [latest, prev1, prev2]`）作为参考；不重复占用主榜行 |

**典型映射示例**（V2 已存在的样本）：

- `model="glm-5.2", channel="opencode-api", harness="opencode"` → 1 行
- `model="glm-5.2", channel="volcengine", harness="opencode"` → 1 行（与上行不同 channel，分行）
- `model="glm-5.2", channel="workbuddy", harness="workbuddy"` → 1 行（与上行不同 channel + harness，分行）
- `model="kimi-k2.7", channel="opencode-api", harness="opencode"` 跑 2 次 → 1 行主榜 + `runs: [latest, prev1]`

不归一化会出现"GLM-5.2 是 95 / 89 / 88"的口径混乱，违反 G5「端到端分数定义」承诺。

---

### 4.2 `hidden_summary.json` 扩展

每条 record：

```json
{
  "test": "...",
  "items": [
    {
      "item_id": "V4-F3-04",
      "scenario_id": "session_without_actor_subject",
      "test_method": "test_session_without_actor_subject_behavior",
      "family": "F3",
      "status": "passed",
      "assertion_keys": ["allowed", "target_patient", "memory_items", "brief"],
      "points": 2,
      "message": "..."
    },
    {
      "item_id": "V4-F12-02",
      "scenario_id": "session_without_actor_subject",
      "test_method": "test_session_without_actor_subject_reason",
      "family": "F12",
      "status": "failed",
      "assertion_keys": ["reason"],
      "semantic_only": true,
      "points": 2,
      "message": "reason mismatch: got 'not_authenticated', expected 'not_authorized_for_target'"
    }
  ]
}
```

**assertion-level mapping 说明**：V4 要求 F3（行为）与 F12（reason）独立计分。一个逻辑场景可能拆成多个 `test_*` 方法（如 `test_session_without_actor_subject_behavior` 与 `test_session_without_actor_subject_reason`），也可能在一个函数内输出多组 item。`run_hidden_tests.py` 必须按 `item_id` / `assertion_keys` 拆分报告，而非只按 test 函数粒度。`semantic_only: true` 的 item 失败不得升级为 S-* behavior blocker。

**`scenario_id` 硬要求（Qwen3.7 Max B1）**：拆分 behavior/reason 后，`item_registry.json` 必须用 `scenario_id` 表达这些 item 属于同一个逻辑场景。`score_model.py` 聚合 family 分时按 `item_id` 计分，但 review/debug 输出必须能按 `scenario_id` 还原一组场景，避免拆分测试后丢失上下文。PR-B1 验收必须包含：同一个 `scenario_id` 下 behavior pass、reason fail 时，F3 得分保留、F12 扣分、`behavior_blockers` 不增加 S-*。

聚合：

```json
{
  "families": { "F3": {"passed": 3, "failed": 2, "points_earned_est": 11, "points_max": 16} },
  "blockers": ["S-ambient"],
  "items": []
}
```

**不再输出**「effective_cap: 82」作为唯一天花板；`ship_gates` 仅作发布风险提示（如 `f3e_failed → class_hint B+`），不得当作新的数值硬顶。

### 4.3 `blockers.json`

```json
{
  "auto": ["S-ambient", "M-fidelity"],
  "semantic_only": [],
  "behavior_blockers": ["S-ambient", "M-fidelity"],
  "manual": [],
  "final": ["S-ambient", "M-fidelity"]
}
```

### 4.4 `score_draft.json`

```json
{
  "ability_draft": 87.0,
  "family_draft": { "F1": 7, "F2": 12, "F3": 11, "...": 0 },
  "ship_cap_hints": { "trust_caps": [], "class_hint": "B+", "note": "F3e failed: no numeric Ship cap, Class B+" },
  "release_class_hint": "B+",
  "evidence_status": {
    "hidden_v4": "complete",
    "esp_build": "skipped|passed|failed",
    "relabel": false
  },
  "unscored_items": [],
  "notes": "auto only; human finalizes"
}
```

### 4.5 `summary.json` 顶层

在 V2 字段上增加：`meta`, `blockers`, `ability_draft`, `ship_cap_hints`, `duration_sec`, `churn`, `esp_build`, `evidence_status`。

### 4.6 `score_draft_confidence.json`

```json
{
  "confidence": "high|medium|low",
  "reasons": [],
  "overestimate_risk": [
    {
      "family": "F5",
      "risk": "hidden test only checks main CRUD path; partial auth/context integration may be overestimated",
      "review_required": true
    }
  ],
  "manual_review_required": true
}
```

规则：

- 真 V4 run 且 public/hidden/static/build/report 证据齐全 → 通常 `high`。
- 历史 V2 重标注、build 缺失、PR artifact 不完整、或新增 V4 item 未实测 → `medium|low`。
- `score_model.py` 不得用 0 或满分自动填补缺证 item；必须写入 `unscored_items` 并交给人工终裁。
- `overestimate_risk` 用来标出自动草稿可能系统性偏高的 family，尤其是 hidden 只覆盖 happy path、部分分需要人工审查、或 V2 relabel 只来自 review 叙述时。人工 reviewer 必须逐项确认这些风险，不得直接采用 `ability_draft`。

## 5. duration / churn

- **duration**：优先 `git log` 首末 commit 时间差；若无 commit，则 full eval 墙钟不代表模型工时——记 `duration_source: eval_wall|git|unknown`。  
- **churn**：`git diff --shortstat` 相对 `project2-v4-broken-seed`。  
- 二者 **不进入 Ability 公式**；仅效率剖面与研究用。

**注意**：F1（Process & truthful reporting）只检查 PR 内容与 diff/log 是否一致、是否篡改测试/探针，**不**把 git commit 时间戳与 public.log 时间戳的先后顺序作为自动扣分依据。时序异常可作为 `score_draft_confidence.json` 的提示或人工 review 线索，但不应引入高误报的自动惩罚。

## 6. ESP build 策略

| 环境 | 行为 |
|------|------|
| 检测到 Windows EIM / 配置的 IDF | 默认跑 `run_espidf_build.py`，写 log+summary |
| 仅 WSL | 可跑 wsl 脚本 |
| 均无 | `esp_build.status = skipped`；F9 按「诚实 skip」档 |

正式 run 使用 `--include-espidf-build` 时，流水线必须将 build log、bin、SHA256、size 与 UTC mtime 写入本次 result；不得只引用会被下一次构建覆盖的共享路径。

`score_model` 不得把 skipped 当满分。

## 7. 渠道政策

1. 每次结果必须有 `channel`。  
2. 主榜可声明「主渠道」（例如 Opencode/API）；其它渠道进对照表。  
3. **禁止**把 WorkBuddy 样本静默写成模型天花板。  
4. 工具严重干扰时：`tool_interference: true`，文字说明；Ability 仍评最终代码，另附「过程可信度」注释。

## 8. 与人工 review 衔接

1. 自动产物齐套后，复制 `scoring/reviewer_prompt.md` 流程。  
2. Review 必须填 V4 字段（见 `02`）。  
3. 更新 `evaluator/reports/v4_scoreboard.md`（实施后新建）：Ship/Ability 双列。  
4. 历史 V2 不自动改写；见 `07`。
5. scoreboards 必须同时输出 `Release view` 与 `Ability view`；若只展示一个排序视图，视为报告不完整。

## 9. item_registry.json（示意）

```json
{
  "V4-F3-05": {
    "family": "F3",
    "scenario_id": "ambient_target_context",
    "test_method": "test_sensitive_target_context_requires_explicit_session_behavior",
    "points": 5,
    "blocker": "S-ambient",
    "test_id_substr": "sensitive_target_context_requires_explicit_session",
    "assertion_keys": ["allowed", "target_patient", "memory_items", "brief"],
    "oracle_type": "behavior"
  },
  "V4-F12-01": {
    "family": "F12",
    "points": 1,
    "test_id_substr": "unauthenticated_context_does_not_leak_patient_data",
    "assertion_keys": ["reason"],
    "oracle_type": "behavior",
    "semantic_only": true
  }
}
```

hidden 运行器加载 registry，避免硬编码散落。

Registry 中每个 item 必须声明：

- `oracle_type`: `behavior|static|report|build`
- `scenario_id`: 同一逻辑场景的 behavior / reason / regression item 必须共享该字段
- `test_method` 或稳定匹配字段：优先精确匹配 test 方法名，避免只靠模糊 substring
- `assertion_keys`: 该 item 对应 test 函数内的哪些断言组（如 `["allowed", "target_patient"]`）；一个 test 函数可映射多个 item
- `allowed_equivalents`
- `semantic_only`: reason/string 类 item 使用 `true`
- `ship_gate_hint`: 可为空；不得等同旧版 `effective_cap`

**实施顺序硬约束（MiniMax-M3 B1）**：

`item_registry.json` **必须**先于 hidden test 跑批实现并填好 F3/F12 相关条目。不可反过来先写 hidden test 再补 registry——否则会出现"hidden test 跑出来但不知道映射到哪个 item"的实施空档期。F3 5 个子项 + F12 3 个子项 = 8 个 item 必须先在 registry 登记，再改 `test_context_policy.py` 和 `run_hidden_tests.py`。

**PR-B1 附加要求（Qwen3.7 Max B1/S4）**：

- `item_registry.json` 必须包含 `scenario_id`，并覆盖所有 F3/F12 拆分场景。
- `run_hidden_tests.py` 仍可使用 `unittest` 自动发现；但结果映射必须以 registry 的 `test_method` / `scenario_id` 为准。
- `eval_helpers.py` 需同步适配 V4 hidden：至少提供稳定 session fixture、old schema fixture、voice/session mock helper，避免每个 hidden test 自己拼装脆弱状态。
- PR-B1 必须先于 PR-B2 完成；PR-B1 未通过 V2 已知样本回归前，不得开始新增 F4/F6/F7 扩展测试。

## 10. 兼容开关

实施初期可：

```text
--benchmark v2|v4
```

便于对照；稳定后默认 v4。

## 11. 安全

- full eval 不得把 `docs/v4` 或 hidden 路径打印进候选可见 log 的复制流程。  
- results 仅操作者可见。  

## 12. 发布前自测矩阵

冻结 V4 seed 前，至少保留以下夹具或已知提交用于管线自测：

| 夹具 | 期望 |
|------|------|
| broken seed | public 绿、probe 有症状、hidden/static 预期红 |
| fixed gold | Ability/Ship ≥95，Class A |
| ambient-only miss | Ability 高、Ship≈Ability、`S-ambient` + Class B+，不触发其它 hard cap |
| reason-only miss | F3 行为得分保留，只扣 F12，不产生 S-* behavior blocker |
| public regression | Ship≤68，Class D/C |
| report overclaim | `P-report`，Ship 信任 cap 生效 |

---

下一篇：[06_ANTI_BIAS_AND_AUTHORING.md](./06_ANTI_BIAS_AND_AUTHORING.md)
