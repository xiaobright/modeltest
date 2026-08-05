# V4 Review: GPT-5.6-luna @ Codex

## Meta
- result_id: `20260712_181517`
- harness: Codex
- tool_interference: **no**
- 操作者备注: GPT-5.6 系列旗舰对比：sol（99/A）、terra（96/A）、**luna（本次）**

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **44 / 45**（仅 1 fail）
  - **F12-04** reason-only：`not_authenticated` ≠ `not_authorized_for_target`
  - **无任何** behavior blocker（无 S-ambient / S-no-actor / M-crash / trust / E-contract）
- esp static: **9 / 9**
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **99.0 / 99.0 / A**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 全过 |
| F2 | 12 | **12** | auth 满分 |
| F3 | 16 | **16** | **满分：无 ambient，无 no-actor 放行** |
| F4 | 4 | **4** | voice bridge 正确接入 session API（优于 terra） |
| F5 | 12 | **12** | care 全链过 |
| F6 | 10 | **10** | 迁移满分（先 migrate 再 index） |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 8 | **8** | static 满分 |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实 |
| F12 | 3 | **3** | 同 sol 裁定：仅 reason 精度，不进 behavior blocker |

**Ability：** 8+12+16+4+12+10+8+8+6+8+4+3 = **99**

## Final scores
- **Ability:** **99 / 100**
- **Ship:** **99 / 100**（无 hard cap 触发）
- **Class:** **A**
- **Blockers (behavior only):** 无
- **Semantic-only notes:** `V4-F12-04` — deny 正确，reason 枚举 `not_authenticated` 而非 `not_authorized_for_target`

## Dimensions（0-10）
- final_code: **10.0**
- security: **9.7** — auth/no-actor/ambient/voice 全满分；仅 reason 精度
- migration: **10.0**
- esp_deploy: **10.0**
- process_truth: **10.0**

## Findings

### 做得好的
1. **44/45 hidden，零 behavior blocker**——与 sol 并列 V4 最佳。
2. **F3=16 满分**：ambient 正确关闭，无 any session fallback。
3. **F4=4 voice 正确**：`fetch_current_session_id()` 或 `/api/v3/session/current` 到位（优于 terra 的 0/4）。
4. **F6=10 迁移满分** + **F8=8 static 满分**。
5. GPT-5.6 系列三兄弟包揽总分前三。

### 主要缺口
1. **F12 reason 精度**：`not_authenticated` → `not_authorized_for_target`（与 sol 同款）。
2. 无其他缺口。

### GPT-5.6 三兄弟对比

| 模型 | Ability | Class | F4 voice | F12 reason | 差异 |
|:---|:------:|:-----:|:--------:|:---------:|:----|
| **sol** | **99** | A | ✅ 4/4 | ⚠️ 3/4 | 旗舰，满分 |
| **luna** | **99** | A | ✅ 4/4 | ⚠️ 3/4 | **与 sol 完全同分，并列第一** |
| **terra** | **95** | A | ❌ **0/4** | ⚠️ 3/4 | voice 未改，差 4 分 |

luna 与 sol 同分（99），F12 同一问题。两者差异仅在代码细节和 PR 风格，核心能力无实质区别。terra 作为次旗舰，voice 是唯一短板。

### 总榜排名（更新）

| 名次 | 模型 | 渠道 | Ability | Class |
|:--:|:---|:---:|:------:|:-----:|
| 1 | GPT-5.6-sol | Codex | **99** | A |
| 1 | **GPT-5.6-luna** | **Codex** | **99** | **A** |
| 3 | GPT-5.6-terra | Codex | **95** | A |
| 4 | HY-3 | WorkBuddy | 92 | B+ |
| 5 | Kimi-K2.7-Code | Qoder | 90 | B+ |

GPT-5.6 系列三兄弟包揽 **前三**（99/99/95），均为 **A 级**——验证了 GPT-5.6 系列在 V4 基准上的统治力。

## Recommendation
- **accept**
- 一句话：GPT-5.6-luna @ Codex 是 **「44/45 hidden、零 behavior blocker、F12 仅 reason 精度差 1 分，与 sol 并列 V4 榜首 99/A」** 的顶级样本。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格
- [x] 未用 82 墙
- [x] channel 写明
- [x] 同系列三兄弟对比

## 锚定校准模式
1. 机器 Ability 99 vs 终裁 99 — **差 0**。
2. 该样本适合标 **top**。
3. 无「误杀正确实现」迹象。
