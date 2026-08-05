# V4 Review: LongCat-2.0 @ OpenCode

## Meta
- result_id: `20260712_130602`
- harness: OpenCode
- tool_interference: **no**
- 操作者备注: 与同通道 HY-3@OpenCode（86.5）对比

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **38 / 45**（7 failed）
  - `S-no-actor`：no_actor behavior 放行未拒绝（**行为泄漏**）
  - `S-ambient`：环境 session 未关
  - `F4` 全灭：voice module 未接入任何 session API
  - `M-fidelity`：migration ts 未从 created_ts 回填
  - `P-report`：PR 未记录修复后验证命令
  - `V4-F12-04` reason-only：`role_allowed` ≠ `not_authorized_for_target`
- esp static: **8 / 9**（1 failed：`lwip` 缺 CMake REQUIRES）
- esp build: **real_pass**（stdpro.bin 有归档）
- draft Ability / Ship / Class（机器）: **81.0 / 81.0 / B**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 6 | **6** | F1-01 缺修复后验证命令记录（−2, P-report） |
| F2 | 12 | **12** | auth 全对 |
| F3 | 9 | **9** | **F3-04 no_actor 放行（−2, S-no-actor）**；F3e ambient（−5, S-ambient） |
| F4 | 0 | **0** | **voice module 完全未改**：未引用 `/api/v3/session/current` 或任何 session API |
| F5 | 10 | **10** | context −2（ambient 连带）；其余 CRUD + auth 全过 |
| F6 | 8 | **8** | F6-03 ts 未从 created_ts 回填（`0 not > 0`，−2, M-fidelity） |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 7 | **7** | `lwip` 缺 REQUIRES（−1, E-contract） |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 有质量 |
| F12 | 3 | **3** | `role_allowed` ≠ `not_authorized_for_target`（F12-04） |

**Ability：** 6+12+9+0+10+8+8+7+6+8+4+3 = **81**

## Final scores
- **Ability:** **81 / 100**
- **Ship:** **81 / 100**（M-fidelity 触发 Release gate ≤88，未触顶）
- **Class:** **B**（多个 behavior blocker 叠加，无法到 B+）
- **Blockers (behavior only):** `P-report`, `S-no-actor`, `S-ambient`, `R-regression`（F4 标记）, `M-fidelity`, `E-contract`
- **Semantic-only notes:** `V4-F12-04` reason

## Dimensions（0-10）
- final_code: **9.5** — 改的代码本身质量尚可
- security: **6.7** — no_actor 放行 + ambient 未关 + voice 未改，三重隐私缺口
- migration: **8.0** — ts 未回填（−2）
- esp_deploy: **9.3** — 仅缺 lwip REQUIRES
- process_truth: **7.5** — PR 缺验证命令记录

## Findings

### 做得好的
1. **Auth 满分（F2=12）**：PBKDF2 + 随机 token + 全链路拒绝。
2. **Sleep 全过（F7=8）**：mixed rows 策略全对。
3. **ESP build 通过 + 大部分 static 过**：F8=7/8，仅缺 lwip。
4. **PR 有 detail（F11=4）**：模板内容较充实。
5. **无信任硬伤**：无明文密码、无 admin 绕过、无 tamper。

### 主要缺口
1. **`S-no-actor`（行为泄漏）**：无 actor subject 的 session 被错误放行，这是 HY-3 两个通道都未曾出现的问题。
2. **F4=0 voice bridge 完全未改**：voice module 未接入 `/api/v3/session/current`，这是本次最严重的缺漏——模型似乎完全忽略了 voice 相关的安全需求。
3. **`S-ambient`**：同多数模型，环境 session 未关。
4. **`M-fidelity`（F6-03）**：ts 未从 created_ts 回填。
5. **F1-01 PR 缺验证记录**：未按模板要求写入修复后验证命令输出。

### 与 HY-3@OpenCode 对比
| 项目 | HY-3 | LongCat-2.0 | 差异 |
|------|:----:|:-----------:|------|
| **Ability** | **86.5** | **81** | −5.5 |
| **F3-04 no_actor** | Pass | **Fail** | LongCat 放行了行为 |
| **F4 voice** | 4/4 | **0/4** | LongCat 完全未改 |
| **F6 migration** | 10/10 | **8/10** | LongCat ts 未回填 |
| **F1 PR initial** | Pass | **Fail** | 缺验证记录 |

LongCat-2.0 比同通道 HY-3 差在 **no_actor 行为放行（安全缺口）**、**voice 完全未触及**、和 **migration 细节遗漏**——这些不是随机波动，而是覆盖面不足。

### PR/报告是否诚实
**是。** 如实记录了诊断和修复后结果。

## Recommendation
- **revise**
  - 必改：`session_is_authenticated` 对无 actor subject 的 session 应返回 False
  - 必改：voice module 接入 `/api/v3/session/current`
  - 必改：关掉 ambient session fallback
  - 必改：F6 migration `ts` 回填逻辑
  - 建议：补 `lwip` REQUIRES
- 一句话：LongCat-2.0@OpenCode 是 **「auth 核心正确但有三大覆盖面缺口——no_actor 放行、voice 未碰、ts 未回填」** 的 B 档样本；明显弱于同通道 HY-3，不是随机波动。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格泄漏
- [x] 未用 82 墙压 Ship（Ship=Ability=81）
- [x] channel/harness 写明
- [x] 同通道跨模型对比

## 锚定校准模式
1. 机器 Ability 81 vs 终裁 81 — **差 0**。
2. 该样本适合标 **weak_or_noisy**（多重覆盖缺口，非单一维度问题，且同通道同 seed 下更强模型显著优于它）。
3. 无「误杀正确实现」迹象；草稿准确。
