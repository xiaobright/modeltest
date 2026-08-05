# V4 Review: GLM-5.2 @ OpenCode

## Meta
- result_id: `20260712_134753`
- harness: OpenCode
- tool_interference: **no**（本轮无 harness 摩擦）
- 操作者备注: 三通道对比（WorkBuddy 81/B, Qoder 81/B, OpenCode 本次）

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **38 / 45**（7 error, 仅 2 behavior fail）
  - `S-ambient`：环境 session 未关（F3e −5）
  - F5 care context 连带（ambient 导致）
  - **F6 全 5 项 error**：旧表 migration crash（M-crash）
  - 无 F12 失败（reason 全对——优于另两渠道）
- esp static: **8 / 9**（1 failed：`lwip` 缺 CMake REQUIRES）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **82.0 / 82.0 / B**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 全过，PR 完整 |
| F2 | 12 | **12** | auth 全对 |
| F3 | 11 | **11** | 仅 F3e ambient −5 |
| F4 | 4 | **4** | voice bridge 正确接入 session API |
| F5 | 10 | **10** | context −2（ambient 连带） |
| F6 | 0 | **0** | **全 5 项 error**：旧表 `CREATE INDEX (... ts)` 在 migrate 前执行 → `no such column: ts` 崩溃（M-crash） |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 7 | **7** | `lwip` 缺 REQUIRES（−1） |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实 |
| F12 | 4 | **4** | **reason 全对**（优于 WB/Qoder 的 3） |

**Ability：** 8+12+11+4+10+0+8+7+6+8+4+4 = **82**

## Final scores
- **Ability:** **82 / 100**
- **Ship:** **82 / 100**（M-crash ≤88，未触顶）
- **Class:** **B**（M-crash + S-ambient）
- **Blockers (behavior only):** `S-ambient`, `M-crash`, `M-fidelity`, `E-contract`
- **Semantic-only notes:** 无（F12 全对）

## Dimensions（0-10）
- final_code: **9.5**
- security: **8.6** — auth 满分 + voice 正确 + no_actor 正确；仅 ambient
- migration: **0** — 旧表全 crash
- esp_deploy: **9.3** — 仅缺 lwip REQUIRES
- process_truth: **10.0** — PR 诚实完整

## Findings

### 做得好的
1. **Auth 满分（F2=12）**：三通道一致。
2. **Voice bridge 正确（F4=4）**：WorkBuddy 和 OpenCode 都对了；Qoder 也对了。
3. **no_actor 行为正确拒绝（F3-04）**：行为边界扎实。
4. **Reason 满分（F12=4）**：本次三通道中**唯一 reason 全对的**（WB/Qoder 都是 3）。
5. **PR 完整诚实（F1=8, F11=4）**：无 P-report、无 helper 虚报。

### 主要缺口
1. **`M-crash`（F6=0）**：旧表 migration INDEX(ts) 在 migrate 前执行 → 全 5 项 error。**三通道同源 bug**，见下对比。
2. **`S-ambient`（F3e −5）**：环境 session 未关，三通道一致。
3. **`E-contract`（F8-03）**：缺 `lwip` REQUIRES（Qoder 没有此问题，F8=8）。

### 三通道对比

| Family | WorkBuddy | Qoder | OpenCode |
|:---|---:|:---:|:---:|
| F1 (8) | 8 | 8 | **8** |
| F2 (12) | 12 | 12 | **12** |
| F3 (16) | 11 | 11 | **11** |
| F4 (4) | 4 | 4 | **4** |
| F5 (12) | 10 | 10 | **10** |
| **F6 (10)** | **0** | **0** | **0** |
| F7 (8) | 8 | 8 | **8** |
| F8 (8) | 7 | **8** | **7** |
| F9 (6) | 6 | 6 | **6** |
| F10 (8) | 8 | 8 | **8** |
| F11 (4) | 4 | 3 | **4** |
| F12 (4) | 3 | 3 | **4** |
| **Ability** | **81** | **81** | **82** |

**核心结论：GLM-5.2 三个渠道高度一致，差异 <2 分，属于同一档。**

- **F6=0 + S-ambient 是三通道共用硬伤**——与渠道无关，是模型本身在 migration 顺序和隐私边界上的系统性问题。
- **F8 和 F12 的小波动是渠道上下文差异**：Qoder 碰巧把 `lwip` 加上了（F8=8）；OpenCode 碰巧把 reason 字符串写对了（F12=4）。这些是 1 分级的噪声。
- **与同通道其他模型对比**：GLM-5.2 的三通道均值 ~81，低于 HY-3@WorkBuddy（92）、接近 HY-3@OpenCode（86.5）、高于 LongCat@OpenCode（81）和 DeepSeek-V4-Pro@OpenCode（82）——但 **F6=0 的 M-crash 是 GLM 独有的**，其他模型迁移都过了。

### PR/报告是否诚实
**是。** 完整记录诊断、测试结果、编译验证。

## Recommendation
- **revise**
  - 必改：F6 migration 顺序（先 migrate 表结构再建 INDEX）
  - 必改：关掉 ambient session fallback
  - 建议：补 `lwip` REQUIRES
- 一句话：GLM-5.2@OpenCode 是 **「auth/voice/no_actor 扎实但迁移全 crash + ambient，三个渠道能力稳定在 81–82」** 的 B 档样本；F6=0 的系统性缺陷来自模型自身，不是渠道问题。

## Self-check
- [x] Ability-first
- [x] reason-only 无
- [x] 未用 82 墙压 Ship
- [x] channel/harness 写明
- [x] 三通道对比分析

## 锚定校准模式
1. 机器 Ability 82 vs 终裁 82 — **差 0**。
2. 该样本适合标 **trust_fail？不对，是 strong_mid 偏 weak**（强项突出但 M-crash 硬伤——实际上 F6=0 是 GLM-5.2 三通道一致的缺陷，不是测试误杀）。
3. 无「误杀正确实现」迹象；草稿准确。
