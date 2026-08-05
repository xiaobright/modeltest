# V4 Review: Grok-4.5 @ grok-cli

## Meta
- result_id: `20260711_210538`
- harness: grok-cli
- tool_interference: no
- evidence_source: **`v4_rerun`**（V4 seed + 当前 hidden 全套 + 当场 score_draft）
- 操作者备注: V4 正式场次（grok-cli）；meta 已写入 model/channel/harness

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **37 / 45**（fail 3 + err 5）
  - **F3e** ambient → `S-ambient`（`get_current_session` fallback 仍在）
  - **F5-05** care context 连带
  - **F12-04** reason-only：`not_authenticated` ≠ `not_authorized_for_target`
  - **F6 全 error**：legacy 上 `CREATE INDEX ... (ts)` 早于补列 → `no such column: ts` → `M-crash`
- esp static: **9 / 9**
- esp build: 机器 `skipped_env`；**人工 real_pass**（`stdpro.bin` ≈982864B，mtime 2026-07-11 21:04；PR 记成功）
- draft Ability / Ship / Class（机器）: **75.5 / 75.5 / B**（F9=3、F11=0.5 低估）

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 过 |
| F2 | 12 | **12** | auth 满分 |
| F3 | 11 | **11** | 仅 F3e −5；no_actor **行为** deny |
| F4 | 4 | **4** | voice `fetch_current_session` 过（V4 新项） |
| F5 | 10 | **10** | context −2 |
| F6 | 0 | **0** | INDEX(ts) 在 migrate 前；旧库 init 炸 |
| F7 | 8 | **8** | sleep first + mixed 过 |
| F8 | 8 | **8** | static 满分 |
| F9 | 3 | **6** | 真 bin + PR 成功 |
| F10 | 8 | **8** | |
| F11 | 0.5 | **4** | PR 充实；机器 placeholder 误判 |
| F12 | 3 | **3** | 与旧 run 同一 reason 错法 |

**Ability：** 8+12+11+4+10+0+8+8+6+8+4+3 = **82**

## Final scores
- **Ability:** **82 / 100**
- **Ship:** **82 / 100**（`M-crash` ≤88 未触顶；无信任 hard-cap）
- **Class:** **B**
- **Blockers (behavior only):** `S-ambient`, `M-crash`, `M-fidelity`
- **Semantic-only:** `V4-F12-04`（缺 actor → reason 仍走 `not_authenticated`）

## Dimensions（0–10）
- final_code: **8.5**
- security: **7.0**（auth 满分；ambient 未关）
- migration: **0**
- esp_deploy: **10**
- process_truth: **9.5**
- efficiency: 未计量（体感快）

## Findings

### 做得好的
1. **真 V4 主线多数过**：auth / sleep / voice bridge / ESP static+build / 回归齐全。
2. public + probe 干净；ESP 模块化（protocol / device_config / mqtt_payload / network_uplink）。
3. no_actor **行为**正确 deny（仅 reason 精度差）。
4. 相对同轮 mid 样本形态完整，非 trust_fail。

### 主要缺口
1. **`S-ambient`**：`build_chat_context_v3` 仍  
   `session = get_session(session_id) if session_id else get_current_session()`  
   → 敏感 target 可被 ambient 会话授权（**旧 V2 场次 Grok 曾关掉此项，本轮未关**）。
2. **`M-crash`**：`care_events.ensure_care_events_schema` 在旧表无 `ts` 时先 `CREATE INDEX ... ON care_events(ts DESC)`，再 `_ensure_column` → 与 GLM 同源顺序雷。
3. **F12**：actor 检查并进 `session_is_authenticated` → reason=`not_authenticated`（与旧 remap 场次同一语义问题）。

### PR/报告是否诚实
**是。** 初诊 6 FAIL、复测通过、ESP 路径与 bin 一致。

## Recommendation
- **revise**（关 ambient；迁移：先 ALTER 再 INDEX(ts)；reason 映射）
- 一句话：**真 V4 重跑把 remap 顶锚 96 拉回现实 82/B**——不是「尺子坏了」，是 V4 全项暴露 ambient+迁移；旧 96 只能当对照。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格 S-no-actor
- [x] 未用 82 墙压 Ship（Ability 恰 82 是扣分结果，不是 cap）
- [x] channel/harness 写明；evidence=`v4_rerun`


## 简要对照（V2 历史场次）

本场相对该模型早期 V2 结果：主线仍强，但 **ambient 未关** 且 **迁移 INDEX(ts) 顺序炸**，故 Ability 82/B；正式榜以本场为准。完整排名见 `evaluator/reports/v4_scoreboard.md`。
