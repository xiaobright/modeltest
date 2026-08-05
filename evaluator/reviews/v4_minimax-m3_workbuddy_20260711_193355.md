# V4 Review: Minimax-M3 @ WorkBuddy

## Meta
- result_id: `20260711_193355`
- harness: WorkBuddy
- tool_interference: possible residual `.workbuddy` 目录（评测未依赖）；ESP 本轮有成功 bin，未见必须「完全权限」才能过的叙述主导叙事
- evidence_source: **`v4_rerun`**
- 操作者备注: model = Minimax M3 / channel = WorkBuddy

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **38 / 45** failed 7
  - **F3e** ambient → `S-ambient`
  - **F4** voice 未引用 `session/current` / `fetch_current_session` → `R-regression`
  - **F5-05** care context 连带 ambient
  - **F7** unscoped `first` 仍写错床（代码 `beds[-1]`）×3 相关测
  - **F12-04** reason-only
- esp static: **9 / 9**（含 lwip）
- esp build: 机器 `skipped_env`；**人工 real_pass** — PR 有完整 idf 日志；`stdpro.bin` mtime 2026-07-11 19:29（≈983KB）
- draft Ability / Ship / Class（机器）: **78.5 / 78.5 / B**（F9=3、F11=0.5 低估）

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 契约过 |
| F2 | 12 | **12** | auth 8/8 |
| F3 | 11 | **11** | 仅 F3e −5；其余 behavior 过 |
| F4 | 0 | **0** | voice 未接 current-session 拉取；probe warning 已提示，PR 却称「显式 session 已够」 |
| F5 | 10 | **10** | CRUD 过；context −2 |
| F6 | 10 | **10** | 迁移全分项过（明显强于 GLM-5.2@WB 同 channel） |
| F7 | 5 | **5** | `sleep_importer` 仍 `return [beds[-1]]`；first/mixed 相关 3 测失败 |
| F8 | 8 | **8** | static 满分 |
| F9 | 3 | **6** | 真编成功有产物 |
| F10 | 8 | **8** | 回归过 |
| F11 | 0.5 | **3** | PR 大体充实且 ESP 记录好；**扣 1**：明文写「first→首床」但代码仍末床，与行为冲突 |
| F12 | 3 | **3** | no_actor reason 仅 |

**Ability：** 8+12+11+0+10+10+5+8+6+8+3+3 = **84**

## Final scores
- **Ability:** **84 / 100**
- **Ship:** **84 / 100**
- **Class:** **B**
- **Blockers (behavior only):** `S-ambient`, `R-regression`
- **Semantic-only:** `V4-F12-04`

## Dimensions（0–10）
- final_code: **8.0**（auth/migration/ESP 强；sleep/voice 弱）
- security: **6.5**（ambient）
- migration: **10**
- esp_deploy: **10**
- process_truth: **7.5**（sleep first 叙述与 diff 冲突）
- efficiency: n/a

## Findings

### 做得好的
1. **F6 迁移满分** — 同 channel 上比 GLM-5.2 WorkBuddy（F6=0）干净一档。
2. **Admin/auth + ESP static + 真编译** 完整；CMake 含 `lwip`，模块化清晰。
3. public / probe 全过；PR 对 ESP-IDF v6 API 踩坑记录详细、可信。
4. no_actor **行为** deny，仅 reason 差。

### 主要缺口
1. **`S-ambient`**：`build_chat_context_v3` 仍 `get_current_session()` fallback。
2. **Sleep first 未修**：代码 `beds[-1]`，F7 −3；且 **PR 声称已写首床** → 报告诚实性问题。
3. **F4 voice bridge=0**：未引用 `/api/v3/session/current` 类路径。
4. care context 随 ambient 失败。
5. F12 reason 精度。

### PR/报告是否诚实
**大体诚实，有一处硬伤。** ESP 编译叙述与 bin 一致；但 **sleep `first` 策略自述与实现相反**，按 reviewer 规则记入 process 扣分（F11 3/4），不触发信任 hard cap（非改测/非假 build）。

## Recommendation
- **revise**
  - `beds[-1]` → `beds[0]`（一行级）
  - 关 ambient fallback
  - voice 增加 `fetch_current_session` / `session/current`
  - 修正 PR 中与代码不符的 sleep 描述
- 一句话：Minimax-M3@WorkBuddy 是 **「ESP+迁移能打、隐私 ambient 与 sleep 经典坑未收、voice 桥缺失」** 的 B 档；比同 channel GLM-5.2（81、M-crash）略强在迁移，弱在 sleep/F4。

## Self-check
- [x] Ability-first
- [x] reason-only 未当泄漏
- [x] 未用 82 墙
- [x] channel = WorkBuddy 写明


