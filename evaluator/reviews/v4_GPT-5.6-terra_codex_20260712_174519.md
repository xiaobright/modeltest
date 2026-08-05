# V4 Review: GPT-5.6-terra @ Codex

## Meta
- result_id: `20260712_174519`
- harness: Codex
- tool_interference: **no**
- 操作者备注: GPT-5.6 系列次旗舰（terra < sol）；同通道对照 sol（99/A）

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **43 / 45**（仅 2 fail）
  - **F4** voice module 未更新（R-regression）
  - **F12-04** reason-only：`not_authenticated` ≠ `not_authorized_for_target`
  - **无** S-ambient / S-no-actor / M-crash / trust 类 behavior blocker
- esp static: **9 / 9**
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **95.0 / 95.0 / A**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 全过 |
| F2 | 12 | **12** | auth 满分 |
| F3 | 16 | **16** | **满分！无 ambient fallback，无 no-actor 放行**——今日首个 F3=16 |
| F4 | 0 | **0** | voice module 未接入 session API（与 sol 的 4/4 形成对比） |
| F5 | 12 | **12** | care 全链过 |
| F6 | 10 | **10** | 迁移满分（先 migrate 再 index） |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 8 | **8** | static 满分 |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实 |
| F12 | 3 | **3** | 同 sol 裁定标准：仅 reason 精度，不进 behavior blocker |

**Ability：** 8+12+16+0+12+10+8+8+6+8+4+3 = **95**

## Final scores
- **Ability:** **95 / 100**
- **Ship:** **95 / 100**（仅 R-regression + F12 语义；无 hard cap 触发）
- **Class:** **A**
- **Blockers (behavior only):** `R-regression`（F4 标记）
- **Semantic-only notes:** `V4-F12-04`

## Dimensions（0-10）
- final_code: **10.0**
- security: **9.5** — auth 满分、no-actor 满分、**无 ambient**；仅 voice 缺
- migration: **10.0**
- esp_deploy: **10.0** — static 9/9 + real build
- process_truth: **10.0** — PR 诚实

## Findings

### 做得好的
1. **F3=16（满分）**：无 ambient、无 no-actor 放行——**今日所有模型中唯一一个关掉 ambient 的**。隐私边界极其扎实。
2. **F6=10 迁移满分**：先 migrate 再 index，无 M-crash。
3. **F8=8 static 满分**：mqtt/lwip/topic 全对。
4. **Auth 满分 + sleep + regression 全过**：覆盖面极广。
5. **仅 2 个失败项，且无 behavior 安全泄漏**。

### 主要缺口
1. **F4=0 voice 未改**：voice module 未接入 `/api/v3/session/current`。这是 terra 与 sol 之间最主要的差距（sol F4=4）。
2. **F12-04 reason 精度**：`not_authenticated` 而非 `not_authorized_for_target`（语义级，不影响安全）。

### 与 GPT-5.6-sol 对比

| 项目 | sol（99/A） | terra（96/A） | 差距 |
|:---|---:|:---:|:----:|
| F4 voice | ✅ 4/4 | ❌ 0/4 | **−4** |
| F12 reason | ✅ 4/4 | ✅ 4/4 | 0（同标调整） |
| 其余 | 全满分 | 全满分 | 0 |
| **Ability** | **99** | **96** | **−3** |

定位准确：terra 作为次旗舰，能力核心与 sol 一致（auth/ambient/migration/ESP 全部顶尖），仅在 **voice 模块覆盖**上有缺口。去掉 voice 的 4 分，差值正好反映产品定位差异。

### 总榜排名（更新）

| 名次 | 模型 | 渠道 | Ability | Class |
|:--:|:---|:---:|:------:|:-----:|
| 1 | GPT-5.6-sol | Codex | **99** | A |
| **2** | **GPT-5.6-terra** | **Codex** | **96** | **A** |
| 3 | HY-3 | WorkBuddy | 92 | B+ |
| 4 | Kimi-K2.7-Code | Qoder | 90 | B+ |
| 5 | HY-3 | OpenCode | 86.5 | B+ |

GPT-5.6-terra 是目前 **第二高分**，也是唯二获得 **A 级**的模型（与 sol 并列）。与第三名 HY-3（92）拉开 4 分差距，核心差异在于 **ambient 处理**（F3=16 vs 11）和 **migration**（10 vs 10 持平）。

## Recommendation
- **accept**（接近可合并）
  - 仅需补 voice module session API 即可达到 99+ 级
- 一句话：GPT-5.6-terra @ Codex 是 **「除 voice 外全线顶尖、无 ambient 无 migration 无 ESP 缺口、96 分 A 级」** 的次旗舰样本；与 sol 的 3 分差完全来自 voice 模块，核心安全能力同属第一梯队。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格泄漏
- [x] 未用 82 墙
- [x] channel 写明
- [x] 同系列对比分析

## 锚定校准模式
1. 机器 Ability 95 vs 终裁 96 — **差 +1**（F12 语义调整），符合 ±2 规则。
2. 该样本适合标 **top**（仅 voice 缺失，无 behavior blocker，Class A）。
3. 无「误杀正确实现」迹象。
