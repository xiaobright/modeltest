# V4 Review: Doubao-Seed-2.0-Code @ OpenCode

## Meta
- result_id: `20260712_143044`
- harness: OpenCode
- tool_interference: **yes**（用户反馈：反复调错工具、输出"完美！"但实际覆盖不全）
- 操作者备注: 调用过程体验差，最终产物口径印证了这一点

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **38 / 45**（7 failed）
  - `S-no-actor`：no_actor behavior 放行未拒绝
  - `S-ambient`：环境 session 未关
  - `F4=0`：voice module 未接入 session API
  - `M-fidelity`：migration ts 未从 created_ts 回填
  - `P-report`：PR 未记录 `run_espidf_build` 验证结果
  - `V4-F12-04` reason-only：`role_allowed` ≠ `not_authorized_for_target`
- esp static: **8 / 9**（1 failed：topic stream `tof1` 标记缺失）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **81.0 / 81.0 / B**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 6 | **6** | F1-01 缺 `run_espidf_build` 验证记录（−2, P-report）；PR 内容混乱（见 Findings） |
| F2 | 12 | **12** | auth 全对 |
| F3 | 9 | **9** | **F3-04 no_actor 放行（−2, S-no-actor）**；F3e ambient −5（S-ambient） |
| F4 | 0 | **0** | **voice module 完全未改** |
| F5 | 10 | **10** | context −2（ambient 连带） |
| F6 | 8 | **8** | F6-03 ts 未从 created_ts 回填（−2, M-fidelity） |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 7 | **7** | topic stream `tof1` 标记缺失（−1）；mqtt REQUIRES 正确（优于 HY-3@OC OpenCode） |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 内容量尚可 |
| F12 | 3 | **3** | `role_allowed` ≠ `not_authorized_for_target` |

**Ability：** 6+12+9+0+10+8+8+7+6+8+4+3 = **81**

## Final scores
- **Ability:** **81 / 100**
- **Ship:** **81 / 100**
- **Class:** **B**
- **Blockers (behavior only):** `P-report`, `S-no-actor`, `S-ambient`, `R-regression`（F4 标记）, `M-fidelity`, `E-contract`
- **Semantic-only notes:** `V4-F12-04`

## Dimensions（0-10）
- final_code: **9.5** — 改的代码本身不差
- security: **6.7** — no_actor 放行 + ambient + voice 未改
- migration: **8.0** — ts 未回填
- esp_deploy: **9.3** — 仅缺 topic 标记
- process_truth: **7.5** — PR 缺 espidf 验证结果，且内容编码混乱

## Findings

### 做得好的
1. **Auth 满分（F2=12）**：PBKDF2 + 随机 token + 全链路拒绝。
2. **ESP 编译通过 + MQTT 依赖正确（F8-03 pass）**：mqtt REQUIRES、lwip 都加了，topic 缺失不是编译问题。
3. **Sleep 全过（F7=8）**。
4. **Migration 大部分正确（6/8）**：仅 ts 回填遗漏。

### 主要缺口
1. **`S-no-actor`（行为泄漏）**：no_actor session 被放行，和 LongCat 同款问题。
2. **`S-ambient`**：环境 session 未关。
3. **`F4=0` voice 完全未改**：未接入 session API。
4. **`M-fidelity`（F6-03）**：ts 未回填。
5. **`P-report`（F1-01）**：PR 未记录 `run_espidf_build` 验证结果。更严重的是 **PR 编码混乱**——错误信息中可见大量乱码（GBK/UTF-8 混用），说明 PR 是在管道输出/日志被错误编码截断后拼凑的，与用户描述的"工具调用错半天"吻合。

### 同通道对比

| 模型 | Ability | no_actor | voice | migration | F8 |
|:---|:------:|:--------:|:-----:|:---------:|:--:|
| HY-3@OC | 86.5 | ✅ | ✅ 4/4 | ✅ 10/10 | 5/8 |
| GLM-5.2@OC | 82 | ✅ | ✅ 4/4 | ❌ 0/10 | 7/8 |
| DeepSeek-V4-Pro@OC | 82 | ✅ | ❌ 0/4 | ❌ 8/10 | 6/8 |
| LongCat-2.0@OC | 81 | ❌ 放行 | ❌ 0/4 | ❌ 8/10 | 7/8 |
| **Doubao-Seed-2.0-Code@OC** | **81** | ❌ 放行 | ❌ 0/4 | ❌ 8/10 | 7/8 |

Doubao Seed 2.0 Code 和 LongCat-2.0 得分和失败模式完全相同（no_actor 放行、voice 未改、ts 未回填），但额外多了 **PR 编码/过程质量问题**。用户反映的"调用工具错半天""总说完美"在产物上能看到痕迹——PR 包含大量编码错误文本，说明工作流被反复打断过。

### PR/报告是否诚实
**总体诚实但质量低。** 诊断和修复内容基本如实，但存在编码问题，且 `run_espidf_build` 验证结果未单独记录。

## Recommendation
- **revise**
  - 必改：no_actor 行为拒绝
  - 必改：voice module 接入 session API
  - 必改：关掉 ambient session
  - 必改：F6 ts 回填
  - 建议：PR 质量/编码一致性
- 一句话：Doubao-Seed-2.0-Code@OpenCode 是 **「工具调用体验差、覆盖缺口多（no_actor/voice/migration ts）、81 分垫底档」** 的 B 档样本；产物质量与用户说的"调错半天"一致，同通道属最弱一档。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格
- [x] 未用 82 墙压 Ship
- [x] channel/tool_interference 写明
- [x] 考虑用户使用体验反馈

## 锚定校准模式
1. 机器 Ability 81 vs 终裁 81 — **差 0**。
2. 该样本适合标 **weak_or_noisy**（多重覆盖缺口，过程质量差，产物编码混乱）。
