# V4 Review: Kimi K2.7 Code @ Qoder

## Meta
- result_id: `20260712_155637`
- harness: Qoder
- tool_interference: **no**（本轮无 harness 摩擦，esp static 9/9 + build pass）
- 操作者备注: Qoder 通道首测；对比 OpenCode 通道各模型

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **41 / 45**（4 failed）
  - `S-ambient`：环境 session 未关（F3e −5）
  - F5 care context 连带（ambient）
  - `M-fidelity`：migration ts 未从 created_ts 回填（F6-03 −2）
  - `V4-F12-04` reason-only：`not_authenticated` ≠ `not_authorized_for_target`
- esp static: **9 / 9**（全过！mqtt/lwip/topic 全对）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **90.0 / 90.0 / B+**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 全过，PR 完整 |
| F2 | 12 | **12** | auth 全对 |
| F3 | 11 | **11** | 仅 F3e ambient −5；**no_actor behavior 正确拒绝**（优于 LongCat/Doubao） |
| F4 | 4 | **4** | voice bridge 正确接入 session API |
| F5 | 10 | **10** | context −2（ambient 连带） |
| F6 | 8 | **8** | F6-03 ts 未回填（−2, M-fidelity） |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 8 | **8** | **static 满分**：mqtt/lwip/topic 全对 |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实 |
| F12 | 3 | **3** | `not_authenticated` ≠ `not_authorized_for_target` |

**Ability：** 8+12+11+4+10+8+8+8+6+8+4+3 = **90**

## Final scores
- **Ability:** **90 / 100**
- **Ship:** **90 / 100**（M-fidelity ≤88 未触顶？实际 90 > 88，但 M-fidelity 不属于 M-crash 硬 cap——M-fidelity 只标 fidelity 不标 crash，不触 88 墙）
- **Class:** **B+**（S-ambient 存在，按规则 B+）
- **Blockers (behavior only):** `S-ambient`, `M-fidelity`
- **Semantic-only notes:** `V4-F12-04`

## Dimensions（0-10）
- final_code: **9.5**
- security: **8.3** — no_actor 正确、voice 正确；仅 ambient
- migration: **8.0** — ts 未回填
- esp_deploy: **10.0** — static 满分 + build real_pass
- process_truth: **10.0** — PR 诚实完整

## Findings

### 做得好的
1. **F8 static 满分**：mqtt/lwip/topic/protocol 全部合规，全通道仅次 HY-3@WorkBuddy（同为 8/8）。
2. **Auth 满分（F2=12）** + **Voice 正确（F4=4）** + **no_actor 正确拒绝**：安全能力扎实。
3. **Sleep / Regression / Process 全过**：覆盖面完整。
4. **PR 诚实完整**：无 P-report 问题。

### 主要缺口
1. **`S-ambient`（F3e −5）**：同多数模型。
2. **`M-fidelity`（F6-03）**：ts 未从 created_ts 回填（`0 not > 0`）。
3. **F12-04 reason 精度**：`not_authenticated` 而非 `not_authorized_for_target`。

### 同通道跨模型排名

| 排名 | 模型 | 通道 | Ability | Class | 关键缺项 |
|:--:|:---|:---:|:------:|:-----:|:--------|
| 1 | HY-3 | WorkBuddy | **92** | B+ | ambient + F6 migration error |
| **2** | **Kimi K2.7 Code** | **Qoder** | **90** | **B+** | **ambient + F6 ts backfill** |
| 3 | HY-3 | OpenCode | 86.5 | B+ | ambient + F8 mqtt 缺失 |
| 4 | GLM-5.2 | OpenCode | 82 | B | ambient + F6 crash |
| 4 | DeepSeek-V4-Pro | OpenCode | 82 | B | ambient + voice 未改 + migration |
| 6 | LongCat-2.0 | OpenCode | 81 | B | no_actor 放行 + voice 未改 |
| 6 | Doubao-Seed-2.0-Code | OpenCode | 81 | B | no_actor 放行 + voice 未改 |
| 7 | GLM-5.2 | Qoder | 81 | B | ambient + F6 crash |
| 7 | GLM-5.2 | WorkBuddy | 81 | B | ambient + F6 crash |

Kimi K2.7 Code @ Qoder 在目前所有已测模型中排名 **第二**，仅次于 HY-3@WorkBuddy（92）。其优势在于 **覆盖面全**（auth/voice/no_actor/sleep/ESP static/regression 全部正确），仅有 ambient 和 migration ts 回填两个缺口。

## Recommendation
- **revise**
  - 必改：关掉 ambient session fallback
  - 必改：F6 migration `ts` 回填逻辑
  - 建议：F12-04 reason 字符串
- 一句话：Kimi K2.7 Code @ Qoder 是 **「覆盖面全、仅 ambient + ts 回填两个缺口、90 分 B+ 档」** 的强模型；在所有已测样本中排第二，与 HY-3@WorkBuddy（92）同级。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格
- [x] 未用 82 墙压 Ship（Ship=90）
- [x] channel/tool_interference 写明
- [x] 全模型排名对比

## 锚定校准模式
1. 机器 Ability 90 vs 终裁 90 — **差 0**。
2. 该样本适合标 **strong_mid**（接近 top，仅两个 soft blocker）。
3. 无「误杀正确实现」迹象。
