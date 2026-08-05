# V4 Review: Qwen-3.7-Max @ Qoder

## Meta
- result_id: `20260712_163502`
- harness: Qoder
- tool_interference: **no**
- 操作者备注: Qoder 通道第二测；对比同通道 Kimi K2.7 Code（90）

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **36 / 45**（4 fail + 5 error）
  - `S-ambient`：环境 session 未关（F3e −5）
  - `F4=0`：voice module 未接入 session API
  - **`M-crash`**：F6 全 5 项 error——旧表 migration crash（同 GLM-5.2 同款问题）
  - `E-contract`：`lwip` 缺 REQUIRES + topic stream `tof1` 标记缺失（−2）
  - `V4-F12-04` reason-only
- esp static: **7 / 9**（2 failed：`lwip` + `tof1` topic 标记）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **76.0 / 76.0 / B**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 全过 |
| F2 | 12 | **12** | auth 全对 |
| F3 | 11 | **11** | 仅 F3e ambient −5；**no_actor behavior 正确拒绝** |
| F4 | 0 | **0** | **voice module 完全未改** |
| F5 | 10 | **10** | context −2（ambient 连带） |
| F6 | 0 | **0** | **全 5 项 error**：旧表 migration 崩溃（同 GLM-5.2 同源 M-crash） |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 6 | **6** | `lwip` 缺 REQUIRES（−1）+ topic stream `tof1` 标记缺失（−1） |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实 |
| F12 | 3 | **3** | `not_authenticated` ≠ `not_authorized_for_target` |

**Ability：** 8+12+11+0+10+0+8+6+6+8+4+3 = **76**

## Final scores
- **Ability:** **76 / 100**
- **Ship:** **76 / 100**（M-crash ≤88，未触顶）
- **Class:** **B**（多 blocker 叠加但无信任硬伤）
- **Blockers (behavior only):** `S-ambient`, `R-regression`（F4 标记）, `M-crash`, `M-fidelity`, `E-contract`
- **Semantic-only notes:** `V4-F12-04`

## Dimensions（0-10）
- final_code: **9.5**
- security: **7.2** — auth 对、no_actor 对；ambient + voice 缺口
- migration: **0** — 全 crash
- esp_deploy: **8.6** — 缺 lwip + topic 标记
- process_truth: **10.0** — PR 诚实

## Findings

### 做得好的
1. **Auth 满分（F2=12）**。
2. **no_actor 行为正确拒绝（F3-04）**。
3. **Sleep 全过（F7=8）**。
4. **PR 完整（F1=8, F11=4）**：无 P-report 问题。

### 主要缺口
1. **`M-crash`（F6=0）**：旧表 migration INDEX 在 migrate 前执行 → 全 5 项 error，与 GLM-5.2 同款。
2. **`S-ambient`（F3e −5）**。
3. **`F4=0` voice 完全未改**。
4. **`E-contract`（F8 −2）**：lwip + topic 标记双缺。
5. 整体覆盖面不足：76 分是目前 Qoder 通道最低分。

### Qoder 通道对比

| 模型 | Ability | F4 voice | F6 migration | F8 ESP |
|:---|:------:|:--------:|:----------:|:-----:|
| Kimi K2.7 Code | **90** | ✅ 4/4 | ❌ 8/10 | ✅ 8/8 |
| **Qwen-3.7-Max** | **76** | ❌ 0/4 | ❌ **0/10** | ❌ 6/8 |

Qwen-3.7-Max 在同通道比 Kimi K2.7 Code 低 14 分，差距集中在 voice（0 vs 4）、migration（0 vs 8）和 ESP（6 vs 8）。

### 与历史 V2 对照
V2 时代 Qwen-3.7-Max @ Qoder 得分 74，V4 得分 **76**，基本持平——说明模型核心能力没有显著变化，ambient + migration + voice 是跨版本持续的短板。

## Recommendation
- **revise**
  - 必改：F6 migration 顺序
  - 必改：voice module 接入 session API
  - 必改：关掉 ambient session
  - 建议：补 lwip + topic 标记
- 一句话：Qwen-3.7-Max @ Qoder 是 **「F6 migration crash + F4 voice 未改 + ambient 三重缺口，76 分」** 的 B 档样本；Qoder 通道目前最弱。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格
- [x] 未用 82 墙压 Ship
- [x] channel 写明
- [x] 同通道 + 跨版本对比

## 锚定校准模式
1. 机器 Ability 76 vs 终裁 76 — **差 0**。
2. 该样本适合标 **weak_or_noisy**（多重硬伤，migration crash + voice 未改 + ESP 双缺）。
3. 无「误杀正确实现」迹象。
