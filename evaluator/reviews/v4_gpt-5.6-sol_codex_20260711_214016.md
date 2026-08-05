# V4 Review: GPT-5.6-sol @ Codex

## Meta
- result_id: `20260711_214016`
- harness: Codex
- tool_interference: no
- evidence_source: **`v4_rerun`**
- duration_note: 操作者记录 **约 26 分钟** 端到端（Grok/Composer 约 5 分钟量级）；不进 Ability，记入 efficiency
- 操作者备注: model = gpt-5.6-sol / channel = codex

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **44 / 45**（仅 1 fail）
  - **F12-04** reason-only：`not_authenticated` ≠ `not_authorized_for_target`（no_actor 场景）
  - **无** S-ambient / M-crash / trust 类 behavior blocker
- esp static: **9 / 9**
- esp build: 机器 `skipped_env`；**人工 real_pass**（`stdpro.bin` 980944B，mtime 2026-07-11 21:35；PR 记成功 + 首败 snprintf 修复）
- draft Ability / Ship / Class（机器）: **96.0 / 96.0 / A**（F9=3 低估）

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 全过 |
| F2 | 12 | **12** | auth 满分（含哈希/token 精确匹配） |
| F3 | 16 | **16** | **含 F3e ambient** 全过；无 current-session fallback |
| F4 | 4 | **4** | `fetch_current_gateway_session_id` / session/current |
| F5 | 12 | **12** | care 全链过 |
| F6 | 10 | **10** | 先 migrate 再 index；缺列/ts/幂等/混排全过 |
| F7 | 8 | **8** | first + mixed 过 |
| F8 | 8 | **8** | static 满分 |
| F9 | 3 | **6** | 真 bin + 诚实首败记录 |
| F10 | 8 | **8** | |
| F11 | 4 | **4** | PR 极完整，自测矩阵清楚 |
| F12 | 3 | **3** | 仅 no_actor reason：实现把缺 actor 并入 `session_is_authenticated` → `not_authenticated` |

**Ability：** 8+12+16+4+12+10+8+8+6+8+4+3 = **99**

## Final scores
- **Ability:** **99 / 100**
- **Ship:** **99 / 100**
- **Class:** **A**
- **Blockers (behavior only):** （无）
- **Semantic-only:** `V4-F12-04` — deny 正确、零泄漏；reason 枚举与契约差 1 分

## Dimensions（0–10）
- final_code: **10**
- security: **9.5**（仅 reason 精度）
- migration: **10**
- esp_deploy: **10**
- process_truth: **10**
- efficiency: **中**（约 26 min，明显慢于 Grok/Composer ~5 min；质量优先）

## Findings

### 做得好的
1. **真 V4 顶锚形态**：hidden 44/45，**无 S-ambient / M-crash / trust**，Class A 站得住。
2. **ambient 正确关闭**：`session_id` 缺失 → `session=None`，不 `get_current_session()`。
3. **迁移顺序正确**：补列/回填后再建 `INDEX(... ts)`，F6 满分（对照 Grok/GLM 的 M-crash）。
4. **voice / sleep / ESP** 全覆盖；PR 含中间失败与并行 `__pycache__` WinError 说明，过程可信。
5. 额外加固：明文密码升级、target/assignment mismatch reason、SQLite 锁处理等，超出最低过线。

### 主要缺口
1. **F12 仅余 1 分**：缺 `actor_subject_id` 时仍走 `not_authenticated`，契约要 `not_authorized_for_target`（与历史强模型同一细粒度坑）。
2. **墙钟偏慢**（~26 min）：不降 Ability；渠道/策略效率备注。

### PR/报告是否诚实
**是。** 初诊、中间 WinError、ESP 首败与成功产物均自洽；未 overclaim flash/实机。

## Recommendation
- **accept**（合并前可选：一行级 reason 映射即可冲 100）
- 一句话：本样本为 **V4 正式榜第一**——Ability 99 / Class A；「全过仅 reason」可达 96–99。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格泄漏
- [x] 未用 82 墙
- [x] channel=Codex / harness=codex；duration 已注

完整排名见 `evaluator/reports/v4_scoreboard.md`。
