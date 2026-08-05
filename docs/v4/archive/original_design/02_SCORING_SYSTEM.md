# V4 评分体系

## 1. 核心原则

1. **两个数讲两件事**：Ability = 工程完成度；Ship = 是否可合并/发布。  
2. **阻断标签讲风险**：不把所有风险都压成同一个整数天花板。  
3. **Hard cap 只打信任崩坏**与极少数「绝对不可上线」的认证灾难。  
4. **Family 独立计分**：一项失败不应连坐无关 family。  
5. **机器草稿 + 人工终裁**：hidden/static/build/report 自动汇总 Ability 草稿；Ship 与争议点人工确认。  
6. **端到端定义诚实**：`分数 = 模型 + 渠道 + harness + 环境`；榜单必须标 Channel。

## 2. 每次 run 的强制输出

| 字段 | 含义 |
|------|------|
| `ability_score` | 0–100，family 加总（可含人工微调 ±2，须写理由） |
| `ship_score` | 0–100，Ability 经信任 cap / 发布规则后 |
| `release_class` | A / B+ / B / C / D |
| `blockers[]` | 阻断码列表 |
| `dimensions` | 六维剖面 0–10 |
| `channel` / `harness` / `model` | 元数据 |
| `hidden` / `esp_static` / `esp_build` | 原始证据摘要 |
| `duration_sec` / `churn_lines` | 效率原始量（不进 Ability 主分） |

### 2.1 主榜列

**默认主榜（Ability 优先，G8 硬约束）**：

```text
Rank | Model | Channel | Ability | Ship | Class | Blockers | Hidden | ESP-static | Build | Duration | Churn
```

- **正式报告必须同时给两张视图**：
  - `Ability view`（默认）：按 Ability 降序，展示最终代码完成度；同 Ability 时按 Ship 降序。
  - `Release view`：按 Ship/Class 筛选/排序，回答「能不能合并/发布」。
- **默认阅读顺序**：先看 Ability view 排序，再用 Release view 识别发布风险；不得只用 Ship 单列讲模型能力。  
- **Ship 门槛造成同分时**：若多个模型因同一 blocker 落入相近 Ship 区间，必须按 Ability 降序展示，并显式标出触发的 gate/blocker，避免把 Class B+ 再次写成新墙。  
- **同模型多渠道**：必须分行，禁止静默覆盖。

> **G8 硬约束（MiniMax-M3 增补）**：本节"默认主榜 Ability 优先"是 V4 的硬性规定（与 `00_DESIGN_BRIEF.md G8` 一致）。`evaluator/scoring/reviewer_prompt.md` V4 版必须硬编码此规则，并设自检问题"你的报告是否把 Ship 当主排序器？"——任一 reviewer 输出违反此约束即视为报告不完整，需重写。`evaluator/reports/v4_scoreboard.md` 默认输出 Ability view；Release view 由 `make scoreboard --view release` 等显式参数触发。

## 3. Ability Score（100 分）

### 3.1 Family 预算（总和必须为 100）

| ID | Family | 分值 | 说明 |
|----|--------|-----:|------|
| F1 | Process & truthful reporting | 8 | 初/终诊断、命令记录、不改测试、报告基本可信 |
| F2 | Admin / auth boundary | 12 | 密码哈希、cookie、logout、管理 API、gallery、session spoof |
| F3 | Context policy（分项） | 16 | 见 3.2；**不含** reason 字符串精度 |
| F4 | Cross-module voice/session bridge | 4 | 安全收紧后 worker 仍可用 |
| F5 | care_event full chain | 12 | schema/CRUD/API/context/归一化 |
| F6 | DB migration fidelity | 10 | 多台阶，见 3.3 |
| F7 | Sleep CSV ownership + mixed rows | 8 | 含混合 CSV |
| F8 | ESP protocol + static contract | 8 | 协议与 static |
| F9 | ESP real build evidence | 6 | 真实编译证据 |
| F10 | Regression compatibility | 8 | v2/esp 等回归 |
| F11 | Docs & maintainability | 4 | 文档同步、模块边界、不删功能 |
| F12 | Policy reason semantics | 4 | reason 枚举精度（**降权**） |
| | **合计** | **100** | |

### 3.2 F3 Context policy 内部分项（16）

| 子项 | 分 | 行为要求 | 失败阻断码 |
|------|---:|----------|------------|
| F3a 未认证零泄漏 | 4 | 无 session 不得返回 patient/memory/sleep/care 敏感内容 | `S-unauth` |
| F3b 跨患者隔离 | 3 | patient A 不得读 B | `S-cross-patient` |
| F3c 过期 session | 2 | expired 不得授权敏感 target | `S-expired` |
| F3d 无 actor / unknown identity | 2 | 不得当已授权主体 | `S-no-actor` |
| F3e Ambient / current fallback | 5 | 敏感 target **必须**显式 `session_id`；不得静默用 current | `S-ambient` |

规则：

- 子项可部分得分（例如只堵了 HTTP 漏了 build_chat 内部路径 → 人工扣部分）。  
- **F3e 失败不得把总分硬改成 82**；只扣 F3e 分并打 `S-ambient`。  
- `S-no-actor` 只在无 actor/unknown session 被授权或泄漏敏感数据时触发；若已经 deny 且零泄漏、只是 reason 字符串不合契约，F3d 可得分，只扣 F12。  
- 零泄漏扫描（brief 不含患者名等）并入 F3a/F3b 的通过条件。

### 3.3 F6 Migration 内部分项（10）

| 子项 | 分 | 要求 | 阻断码 |
|------|---:|------|--------|
| F6a 旧表不崩 | 3 | 缺列旧 `care_events` 启动/init 不崩溃 | `M-crash` |
| F6b 补列与数据保留 | 2 | 旧行仍在，新列存在 | `M-fidelity` |
| F6c ts 回填 | 2 | ts 缺失/0 从 `created_ts` 回填 | `M-fidelity` |
| F6d 幂等 init | 1 | 连续 `init_management_db` 安全 | — |
| F6e 混合排序 | 2 | 新旧行按约定 `ts/created_ts` 降序可混排 | `M-fidelity` |

### 3.4 F1 / F9 / F12 细则摘要

**F1（8）**

- 4：记录初始 public + probe（或等价诊断）  
- 2：修复后再次验证有记录  
- 1：ESP 构建命令/失败点有记录（或明确 skip 原因）  
- 1：未篡改 `tests/`、`tools/run_debug_probe.py`、evaluator 可见脚本  

篡改测试：**F1=0 且 Ship hard cap**（见 §5）。

**F9（6）**

| 情况 | 分 |
|------|---:|
| 工具链可用且 evaluator/用户确认 build 成功，有 log/artifact | 6 |
| 工具链可用，build 失败但日志定位清晰、未谎称成功 | 3–4 |
| 工具链不可用，诚实写 skip + 环境限制 | **3**（不得给满；`score_draft.json` 须标注 `f9_mode: "skipped_env"`） |
| 声称成功但 log/artifact 矛盾或缺失 | 0，并触发 `P-report` / 信任 cap |

正式新 run 的 6 分证据必须落在本次 result 中：`espidf_build.log`、`espidf_build_evidence.json`，以及归档 bin 的 SHA256/size。共享 build 目录中的临时文件不能单独作为冻结证据。V4 首轮历史场次若只能保留操作者确认，必须在 freeze manifest 标成 `operator_attested_legacy`，不得伪装为可复现 artifact。
| 固件几乎未动却声称完成 | 0 + 信任 cap |

**F12（4）**

- 仅衡量 deny 时 reason 是否符合契约枚举。  
- **已正确拒绝且零泄漏但 reason 错 → 最多扣 F12，不影响 F3 主分。**  
- 不得因 F12 单独触发 hard cap。

## 4. Ship Score

### 4.1 计算公式（默认）

```text
ship_raw = ability_score
ship_score = apply_release_gates(apply_trust_caps(ship_raw, evidence), blockers)
release_class = map_blockers_and_ship(blockers, ship_score)
```

人工可在 `ship_raw` 上对「严重但未进 automatic family」的问题做 **额外 −1～−5**，必须写入 review。

### 4.2 发布档位（Release Class）

| Class | 含义 | 典型条件 |
|-------|------|----------|
| **A** | 接近可合并 | 无 S-\* / M-crash / E-build / F-public / T-tamper / 严重 P-report；Ship ≥ 90 |
| **B+** | 强完成度，仍有发布阻断 | Ability 高但存在 `S-ambient` 或 `M-crash` 等 |
| **B** | 主线大体完成，多项阻断或缺口 | 常见原 80–88 段 |
| **C** | 部分有用，核心多处未完成 | |
| **D** | 评测不可信或大面积不可用 | public 崩、篡改测试、严重造假 |

**注意**：Class 与 Ability 解耦——可以 Ability 88 + Class B+（有 `S-ambient`）。这正是 V4 要保留的信息。

### 4.3 「高 Ship 的发布门槛」（防灌水，不作能力排序器）

默认启用：

| 若想 Ship ≥ … | 额外要求 |
|---------------|----------|
| ≥ 90 / Class A | 必须通过 F3a + F3b（未认证零泄漏、跨患者）；不得有 `M-crash`、`F-public`、`T-tamper` |
| ≥ 95 | 在上一条基础上，必须通过 F3e（无 ambient fallback）；F9 不得为「谎称成功」 |

这些是 **Ship/Class 发布门槛**，不是能力排序器。F3e 失败不再把 Ship 数值压到固定天花板，但会阻止进入 Class A；Ability 仍可保留 88–92 等真实完成度。  
例：F3e 失败时 Ability≈88、Ship≈88（无 ambient 额外数值顶），标 `S-ambient` + Class B+；报告必须继续用 Ability 和 family breakdown 区分它与 Ability 80–83 的模型。

#### 门槛数值表（默认）

| 触发 | Ship 处理 |
|------|----------|
| 未过 F3a 或 F3b | min(ship, **84**)，Class 不得为 A |
| 过 F3a/b 但未过 F3e | **不设 Ship 数值上限**；Class 不得为 A，标记 B+ |
| 存在 `M-crash` | min(ship, **88**)，Class 不得为 A |
| 存在 `E-build` 且声称成功 | 走信任 cap 72 |
| 仅 `M-fidelity` / `E-contract` / F4 失败 / F12 失败 | **不设**额外 Ship 顶（只扣 Ability） |

审核说明：F3e 不再设置 89 硬顶，避免把原 82 墙平移到 89。发布风险由 Class B+ 表达；数值区分靠 Ability。

## 5. 信任类 Hard Caps（Ship）

仅以下条件对 **Ship** 施加硬顶（可叠加取更低）：

| 条件 | Ship max | 阻断 |
|------|----------:|------|
| 明文管理员密码 | 60 | `S-plaintext-admin` |
| 管理 API 大面积免登/可伪造 | 65 | `S-admin-bypass` |
| 篡改可见 tests/tools 以过关 | 60 | `T-tamper` |
| public 失败且落在候选改动路径 | 68 | `F-public` |
| 严重 overclaim（build/测试/不存在的文件） | 72 | `P-report` |
| ESP 必做几乎未做却声称完成 | 70 | `P-report` + `E-contract` |

**明确不进 hard cap 列表：**

- 仅 `S-ambient`  
- 仅 reason 错误  
- 仅 `M-fidelity`  
- 仅 F4 voice bridge  
- 仅 ESP static 缺 1–2 个 marker  

## 6. 阻断码字典

| Code | 含义 | 主要影响 |
|------|------|----------|
| `S-unauth` | 未认证敏感泄漏 | F3a, Class, Ship 门槛 |
| `S-cross-patient` | 跨患者 | F3b, Class, Ship 门槛 |
| `S-expired` | 过期仍授权 | F3c |
| `S-no-actor` | 无 actor/unknown 被授权或泄漏 | F3d |
| `S-ambient` | ambient/current fallback | F3e, Class B+（无 Ship 数值硬顶） |
| `S-plaintext-admin` | 明文密码 | hard cap |
| `S-admin-bypass` | 管理绕过 | hard cap |
| `M-crash` | 旧库迁移崩溃 | F6a, Ship≤88 |
| `M-fidelity` | 迁移保真不足 | F6b/c/e |
| `E-build` | 构建失败或证据不可信 | F9 |
| `E-contract` | 协议/static 不足 | F8 |
| `P-report` | 报告不实/缺验证 | F1, 信任 cap |
| `F-public` | public 回归失败 | hard cap |
| `T-tamper` | 改测试/探针 | hard cap |
| `R-regression` | 兼容路径破坏 | F10 |

机器从 hidden/static/build/report 启发式生成 `blockers.json`；人工可增删。`blockers.json` 必须区分 `behavior_blockers` 与 `semantic_only`，避免 reason-only 失败被升级成安全泄漏。

## 7. 六维剖面（0–10，不单独加总进 Ability）

| 维 | 主要 family 映射 |
|----|------------------|
| final_code | F2 F5 F7 F10 F11 |
| security | F3 F4 F12 及 auth 相关 |
| migration | F6 |
| esp_deploy | F8 F9 |
| process_truth | F1 P-report |
| efficiency | duration/churn/干预次数（人工 0–10） |

用于雷达图与文字 profile，**不替代** Ship/Ability。

## 8. 与 V2 / V3.1 分数对照（概念）

| 场景 | V2 正式分 | V4 Ability（示意） | V4 Ship（示意） |
|------|----------:|-------------------:|----------------:|
| 仅 ambient 漏，其余很强 | 82 | 86–90 | ≈Ability + `S-ambient` + B+ |
| ambient 漏 + 迁移崩 | 82 | 80–85 | ≤88 + blockers |
| 全过仅 reason 错 | 96 | 96–98 | 96–98 A |
| public 挂 + 吹构建 | 66 | 70–78 | ≤68/72 D/C |

精确示意见 [APPENDIX_SCORE_EXAMPLES.md](./APPENDIX_SCORE_EXAMPLES.md)。

## 9. 自动草稿与人工职责

### 自动（设计目标）

- hidden 逐项 → family 建议分  
- static 摘要 → F8  
- build 状态 → F9  
- PR 关键词/命令痕迹 → F1 下限建议  
- blockers 列表  
- evidence completeness：标出哪些 family 只是旧 V2 证据推断、哪些是 V4 新 item 实测，防止重标注被误读为正式 V4 run  

### 人工必须

- 终裁 Ability（尤其部分分）  
- Ship 与 Class  
- overclaim 与架构/删功能判断  
- 工具干扰标注（`tool_interference: true`）  

### Review 输出模板（强制字段）

```markdown
## V4 Score
- Model / Channel / Harness:
- Ability:
- Ship:
- Class:
- Blockers:
- Family breakdown: F1..F12
- Dimensions:
- Tool interference notes:
- Evidence refs: results/<id>/
```

## 10. 已收敛争议点 / 仍开放争议点

### 已收敛（经 Codex / DeepSeek / Kimi K2.7 / GLM-5.2 / MiniMax-M3 交叉审核）

1. **F3e Ship 数值上限 89**：**取消**。仅保留 Class B+ 标记；默认主榜按 Ability 降序。  
2. **默认主榜视图**：**Ability 优先**，Ship/Class 作为并列信息列；Release view 为第二视图。**G8 已写入 00_DESIGN_BRIEF.md 硬约束**（MiniMax-M3 增补）。  
3. **F9 无工具链**：固定 **3 分**，`score_draft.json` 标注 `f9_mode: "skipped_env"`；报告须显式区分 `build_skipped`。**不采用分母缩放到 94**（MiniMax-M3 反对 DeepSeek B2 的备选方案：缩放在传播时引入"95/100 vs 95/94"口径混乱，F9 差距 3 分对 100 分 Ability 排序影响 < 0.5 分）。  
4. **F4 voice bridge**：拆分为 F4a（识别风险，1 分）+ F4b（正确修复，3 分）。F4-02 allowed_equivalents 已收紧（GLM-5.2 B2）：本地 DB 直查必须经过显式 actor 校验。  
5. **F1 时序验证**：**不引入** git 时间戳 vs public.log 的自动扣分；时序异常仅作置信度提示或人工线索。  
6. **V4.1 capstone 触发条件**（MiniMax-M3 增补）：≥3 个模型 Ability≥96 **或** top3 Ability 极差<2，二者满足其一即触发。  
7. **F3/F12 拆分落地**（MiniMax-M3 B1）：`test_context_policy.py` 必须改写支持按 assertion key 报告；`run_hidden_tests.py` 同步改造。详见 `03_ITEM_BANK.md §0` 实施约束。  
8. **F8-07 static 改写**（MiniMax-M3 B3）：必须支持宏展开；uncertain 时记 `f8_07_status: "uncertain"`，由人工 final 判；不得自动记过/自动扣分。详见 `03_ITEM_BANK.md §F8-07` 实施约束。  
9. **`api_contracts.md` 第 49 行去剧透**（GLM-5.2 B3 / MiniMax-M3 B2）：改写为"三要素决定授权"且必须用 V2 历史样本回归验证。详见 `04_SEED_AND_PROMPT.md §5.1`。  
10. **端到端 model/channel/harness 归一化**（MiniMax-M3 S1）：同 model + 不同 channel/harness 分行；同 model + 同 channel + 不同次跑合并为最近一次 + N 次历史分布。详见 `05_EVALUATOR_PIPELINE.md §4.1`。  

### 仍开放（待更多审核或校准跑后决定）

1. **F12=4** 是否仍过高/过低？  
2. **Ability 人工 ±2** 是否应禁止，改为纯公式？  
3. **V4 回滚条件**（MiniMax-M3 S3）：校准 5 锚点与人工分差 > ±5、top3 极差 < 1、relabel 与重跑差 > ±3 三条是否充分？详见 `07_MIGRATION_AND_COMPAT.md §7`。  
4. **frozen gold 锚点**（MiniMax-M3 S2）：是否需要在 `archives/v4_gold/` 保留已知完成版作为 ground truth？详见 `07 §3.4`。  
5. **V4 run 估时 15–25 分钟**（MiniMax-M3 S4）：是否需要更细粒度的 hidden/static/build 拆解估时？详见 `05_EVALUATOR_PIPELINE.md §3`。  

默认立场已写入上文；反对须给出替代数值表。

---

下一篇：[03_ITEM_BANK.md](./03_ITEM_BANK.md)
