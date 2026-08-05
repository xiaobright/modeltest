# V4 Review: GPT-5.6-sol @ Codex (Medium)

## Meta
- result_id: `20260712_190427`
- harness: Codex (medium thinking)
- tool_interference: **no**
- duration: **~8 min**（xhigh ~24 min）
- 操作者备注: 同模型同渠道对照：xhigh（99/A）vs medium（本次）

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **42 / 45**（3 fail）
  - `S-ambient`：环境 session 未关（F3e −5）
  - F5 care context 连带
  - `V4-F12-04` reason-only
  - **无** S-no-actor / M-crash / trust
- esp static: **8 / 9**（1 failed：`mqtt` 缺 CMake REQUIRES）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **91.0 / 91.0 / B+**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 全过 |
| F2 | 12 | **12** | auth 满分 |
| F3 | 11 | **11** | **ambient 出现**（xhigh 版满分 16，medium −5） |
| F4 | 4 | **4** | voice 正确（与 xhigh 一致） |
| F5 | 10 | **10** | context −2（ambient 连带） |
| F6 | 10 | **10** | 迁移满分 |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 7 | **7** | `mqtt` 缺 REQUIRES（−1, E-contract） |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实（但比 xhigh 简略） |
| F12 | 3 | **3** | reason 精度 |

**Ability：** 8+12+11+4+10+10+8+7+6+8+4+3 = **91**

## Final scores
- **Ability:** **91 / 100**
- **Ship:** **91 / 100**
- **Class:** **B+**
- **Blockers (behavior only):** `S-ambient`, `E-contract`
- **Semantic-only notes:** `V4-F12-04`

## Dimensions（0-10）
- final_code: **9.5**
- security: **8.3** — 比 xhigh 低（ambient 未关）
- migration: **10.0**
- esp_deploy: **9.3** — 缺 mqtt REQUIRES
- process_truth: **10.0**
- efficiency: **快**（8 min vs xhigh 24 min）

## Findings

### 做得好的
1. **Auth / Voice / Migration / Sleep / Regression 仍满分**：核心工程能力不受思考强度影响。
2. **8 分钟完成，比 xhigh 快 3×**。
3. **无 trust / no-actor / M-crash** 等严重缺口。

### 主要缺口
1. **`S-ambient`（F3 −5）**：xhigh 正确关掉了 ambient，medium 没关——这是思考强度带来的最明显退化。
2. **`E-contract`（F8 −1）**：`mqtt` 缺 REQUIRES，xhigh 是加上了的。
3. **F12 reason 精度**：两版本一致。

### xhigh vs medium 对比

| 项目 | xhigh (99/A) | medium (91/B+) | 差距 |
|:---|---:|:---:|:----:|
| 耗时 | ~24 min | **~8 min** | 3× 快 |
| F3 ambient | ✅ 16/16（关掉） | ❌ 11/16（出现） | **−5** |
| F8 mqtt REQUIRES | ✅ 8/8 | ❌ 7/8 | −1 |
| F5 care context | ✅ 12/12 | ❌ 10/12 | −2（ambient 连带） |
| 其余 | 全满分 | 全满分 | 0 |
| **Ability** | **99** | **91** | **−8** |

Medium 省了 16 分钟思考时间，代价是 **ambient 边界没守住（−5）和 mqtt 细节遗漏（−1）**。但 auth/voice/migration/sleep/ESP build 等核心能力仍在同一水平。

## Recommendation
- **revise**（需补 ambient + mqtt REQUIRES）
- 一句话：GPT-5.6-sol @ Codex Medium 是 **「思考强度降档后 ambient 和 ESP 细节丢失，从 99 降到 91，但核心工程能力仍然在线」** 的 B+ 档样本；8 分钟出 91 分性价比极高。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格
- [x] 未用 82 墙
- [x] channel + thinking intensity 注明
- [x] xhigh vs medium 对比分析
