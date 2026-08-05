# V4 Review: DeepSeek-V4-Pro @ OpenCode

## Meta
- result_id: `20260712_132325`
- harness: OpenCode
- tool_interference: **no**
- 操作者备注: 对比同通道 HY-3（86.5）和 LongCat-2.0（81）

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **39 / 45**（6 failed）
  - `S-ambient`：环境 session 未关（F3e −5）
  - `F4=0`：voice module 未接入 session API
  - `M-fidelity`：旧表 migration 缺 `severity` 列追加
  - `P-report`：PR 未记录修复后验证命令
  - `V4-F12-04` reason-only：`not_authenticated` ≠ `not_authorized_for_target`
- esp static: **7 / 9**（2 failed：`mqtt` 缺 REQUIRES、topic stream `tof1` 标记缺失）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **82.0 / 82.0 / B**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 6 | **6** | F1-01 缺修复后验证命令（−2, P-report） |
| F2 | 12 | **12** | auth 全对 |
| F3 | 11 | **11** | F3e ambient −5（S-ambient）；**F3-04 no_actor 行为正确拒绝**（优于 LongCat） |
| F4 | 0 | **0** | **voice module 完全未改**，未引用 `/api/v3/session/current` |
| F5 | 10 | **10** | context −2（ambient 连带） |
| F6 | 8 | **8** | F6-02 旧表 migration 缺 `severity` 列追加（−2, M-fidelity） |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 6 | **6** | `mqtt` 缺 REQUIRES（−1）+ topic stream `tof1` 标记缺失（−1） |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实 |
| F12 | 3 | **3** | `not_authenticated` ≠ `not_authorized_for_target` |

**Ability：** 6+12+11+0+10+8+8+6+6+8+4+3 = **82**

## Final scores
- **Ability:** **82 / 100**
- **Ship:** **82 / 100**（M-fidelity ≤88，未触顶）
- **Class:** **B**（voice 全灭 + S-ambient）
- **Blockers (behavior only):** `P-report`, `S-ambient`, `R-regression`（F4 标记）, `M-fidelity`, `E-contract`
- **Semantic-only notes:** `V4-F12-04`

## Dimensions（0-10）
- final_code: **9.5**
- security: **7.2** — no_actor 正确但 ambient + voice 缺口
- migration: **8.0** — 旧表列追加失败
- esp_deploy: **8.6** — 缺 mqtt REQUIRES + topic 标记
- process_truth: **7.5** — PR 缺验证命令记录

## Findings

### 做得好的
1. **Auth 满分（F2=12）**：PBKDF2 + 随机 token + 全链路拒绝。
2. **no_actor 行为正确拒绝（F3-04）**：优于 LongCat（放行），与 HY-3 一致。
3. **Sleep 全过（F7=8）**。
4. **ESP 真编译通过**。
5. **PR 较充实（F11=4）**。

### 主要缺口
1. **`S-ambient`（F3e −5）**：同多数模型。
2. **F4=0 voice 完全未改**：与 LongCat 同款缺漏，HY-3 正确实现了此模块。
3. **`M-fidelity`（F6-02）**：旧表 migration 未追加 `severity` 列（`'severity' not found`）→ **与 LongCat 的 ts 回填失败不同**，是独立的 migration 覆盖不全。
4. **`E-contract`（F8 −2）**：mqtt 缺 REQUIRES + topic stream 标记缺失。
5. **F1-01 缺验证命令记录**。

### 同通道三模型对比

| 模型 | Ability | F3 no_actor | F4 voice | F6 migration | F8 ESP |
|:---|:------:|:----------:|:--------:|:-----------:|:-----:|
| HY-3 | **86.5** | ✅ | ✅ 4/4 | ✅ 10/10 | 5/8 |
| **DeepSeek V4 Pro** | **82** | ✅ | ❌ 0/4 | ❌ 8/10 | 6/8 |
| LongCat-2.0 | 81 | ❌ 放行 | ❌ 0/4 | ❌ 8/10 | 7/8 |

DeepSeek V4 Pro 在 no_actor 行为上正确（优于 LongCat），但 voice 完全未触及且 migration 列追加有遗漏。整体介于 LongCat 和 HY-3 之间。

### PR/报告是否诚实
**是。** 如实记录了诊断和测试结果。

## Recommendation
- **revise**
  - 必改：voice module 接入 session API
  - 必改：关掉 ambient session fallback
  - 必改：F6 migration `severity` 列追加
  - 建议：补 `mqtt` REQUIRES、补 topic stream 标记
- 一句话：DeepSeek-V4-Pro@OpenCode 是 **「auth/no_actor 正确但 voice/migration 覆盖不全」** 的 B 档样本；优于 LongCat（no_actor 正确）但弱于 HY-3（缺 voice + migration）。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格泄漏
- [x] 未用 82 墙压 Ship
- [x] channel/harness 写明
- [x] 同通道三模型对比

## 锚定校准模式
1. 机器 Ability 82 vs 终裁 82 — **差 0**。
2. 该样本适合标 **weak_or_noisy**（多重覆盖缺口，voice 完全未改且 migration 列遗漏，同通道有更强参考）。
3. 无「误杀正确实现」迹象。
