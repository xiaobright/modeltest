# V4 Review: Composer-2.5 @ grok-cli

## Meta
- result_id: `20260711_182425`
- harness: grok-cli（Grok Build CLI / Composer 2.5）
- tool_interference: no
- evidence_source: **`v4_rerun`**（本 run 在 V4 seed + 完整 hidden 分项上产出 `score_draft`）
- 操作者备注: 工作区候选改动后由评审侧执行 `run_full_eval`；ESP 真机构建有同日 `stdpro.bin` 产物证据（见 Findings）

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: 失败 3 项（behavior + semantic）
  - **F3e** `test_sensitive_target_context_requires_explicit_session_behavior` → `allowed=True` 应 False → **`S-ambient`**
  - **F5-05** `test_care_event_context_integration` → 同源 ambient 路径连带失败
  - **F12-04** `test_session_without_actor_subject_reason` → reason-only（`not_authenticated` ≠ `not_authorized_for_target`）
  - 其余 context **behavior**（unauth / cross-patient / expired / no_actor deny）均过；staff 正例过
- esp static: **9 / 9**；`f8_09_status=pass`，`f8_07_status=pass`
- esp build: 机器草稿 `skipped_env`；**人工升为 real_pass**（`E:\esp\builds\modeltest\project2_task\esp32\testpro4\build\stdpro.bin`，约 983088 bytes，mtime 2026-07-11 18:23，与 PR 路径一致）
- draft Ability / Ship / Class（机器）: **89.0 / 89.0 / B+**（F9=3）

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 Process | 8 | **8** | process/PR 契约全过 |
| F2 Admin/auth | 12 | **12** | auth 8/8 |
| F3 Context behavior | 11 | **11** | 仅 F3e −5；F3a/b/c/d 与 staff 正例均过；**不**把 F12 并入 F3 |
| F4 Voice bridge | 4 | **4** | `fetch_current_session` 路径过 V4 独立 item |
| F5 care_event | 10 | **10** | CRUD/归一化/鉴权过；context 集成 −2（ambient 连带） |
| F6 Migration | 10 | **10** | F6a–e 五测全过（相对旧 V2 Composer 样本显著进步） |
| F7 Sleep CSV | 8 | **8** | 含 mixed rows 全过 |
| F8 ESP static | 8 | **8** | 9/9 静态含 buffer |
| F9 ESP build | 3 | **6** | 同日 bin 产物 + PR 首败点叙述一致，非 overclaim |
| F10 Regression | 8 | **8** | v2/esp 回归过 |
| F11 Docs | 4 | **4** | PR 充实，过程/ESP/风险齐全 |
| F12 Reason | 3 | **3** | 仅 no_actor reason 错；**不**升格 S-no-actor |

**Ability 加总：** 8+12+11+4+10+10+8+8+6+8+4+3 = **92**

## Final scores
- **Ability:** **92 / 100**
- **Ship:** **92 / 100**
- **Class:** **B+**
- **Blockers (behavior only):** `S-ambient`
- **Semantic-only notes (F12 等）:** `V4-F12-04` no_actor reason 精度

## Dimensions（0–10）
- final_code: **9.5**
- security: **7.5**（F3e 未收；其余 policy 强）
- migration: **10**
- esp_deploy: **10**
- process_truth: **10**
- efficiency: **高**（eval wall ≈17s 量级主测；用户侧体感「快」与旧 Composer 样本一致；不进 Ability）

## Findings

### 做得好的
1. **真正的 V4 主线完成度**：migration 全分项、sleep mixed、voice bridge、ESP static 9/9 + 真 bin，远强于旧 V2 Composer（当时 migration/ts 与 no_actor behavior 都挂）。
2. **Admin/auth 与 sleep 满分**，public + probe 干净。
3. **F4 做对了**：voice 显式 `fetch_current_session()`，收紧鉴权后 worker 路径仍可用。
4. **no_actor 行为已 deny**（相对旧 run「无 actor 仍 allowed」是质变）；仅剩 reason 枚举。
5. **PR 诚实**：写了 probe 初诊、ESP 首败（`ESP_EVENT_ANY_ID` / 残留 `print_device_config`）与未 flash 风险。

### 主要缺口
1. **`S-ambient`（主发布阻断）**：`build_chat_context_v3` 仍 `session_id` 空时 `get_current_session()` fallback（diff 可见），敏感 target 可被 ambient 会话授权 → Class 不能 A。
2. **care_event context 集成**随 ambient 失败（F5 −2），不是独立 CRUD 问题。
3. **F12 reason**：缺 actor → `not_authenticated`，契约要 `not_authorized_for_target`。
4. 机器 F9=3 在有 bin 时会低估 Ability（本终裁已 +3）。

### PR/报告是否诚实
**是。** public/probe 叙述与 log 一致；ESP 路径与磁盘 bin 时间戳吻合；未改测；未发现信任类 hard-cap 条件。

## Recommendation
- **revise**（相对合并：主线可合，**必须先关 ambient fallback** 再谈 Class A）
- 一句话：该样本是 V4「原 82 墙」校准的成功例——**Ability 92 拉开中游，Ship 同阶不压顶，Class B+ 只表达 S-ambient 发布风险**；相对正式 Grok-4.5 真 V4 重跑（82/B），它在迁移与 ESP 同样完整，主要剩 F3e+care context。

## Self-check
- [x] Ability-first — 主叙事 Ability 92，不以 Ship 单列排序
- [x] 未把 reason-only 当泄漏 — 仅 F12，无 S-no-actor
- [x] 未使用 82/89 墙 — S-ambient 无数值硬顶
- [x] channel 写明 — grok-cli / Composer 2.5


## vs 旧 V2 Composer（`20260709_195343`）

| 维度 | V2 旧 run | 本次 V4 run |
|------|-----------|-------------|
| Hidden 形态 | 30/34；no_actor **行为**挂；migration ts 挂；static 7/8 | F3e+care context+reason；migration/F4/static 满 |
| V2 正式分 | 82（privacy cap） | — |
| V4 Ability | relabel ≈83 | **92（v4_rerun）** |
| 主 blocker | S-ambient + M-crash 叙事 | **仅 S-ambient** |
