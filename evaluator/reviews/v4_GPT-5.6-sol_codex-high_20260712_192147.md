# V4 Review: GPT-5.6-sol @ Codex (High)

## Meta
- result_id: `20260712_192147`
- harness: Codex (high thinking)
- tool_interference: **no**
- duration: **~13 min**（medium 8 min, xhigh 24 min）
- 操作者备注: 思考强度梯度对照：xhigh→high→medium

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **44 / 45**（仅 1 fail）
  - **F12-04** reason-only：`not_authenticated` ≠ `not_authorized_for_target`
  - **无** S-ambient / S-no-actor / M-crash / trust
- esp static: **8 / 9**（1 failed：topic stream `tof1` 标记缺失 → E-contract）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **98.0 / 98.0 / B+**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 全过 |
| F2 | 12 | **12** | auth 满分 |
| F3 | 16 | **16** | **满分：无 ambient**——high 已足够关掉环境 session |
| F4 | 4 | **4** | voice 正确 |
| F5 | 12 | **12** | care 全链过 |
| F6 | 10 | **10** | 迁移满分 |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 7 | **7** | topic stream `tof1` 标记缺失（−1, E-contract） |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实 |
| F12 | 3 | **3** | reason 精度 |

**Ability：** 8+12+16+4+12+10+8+7+6+8+4+3 = **98**

## Final scores
- **Ability:** **98 / 100**
- **Ship:** **98 / 100**（无 hard cap）
- **Class:** **A**（仅 E-contract + F12 语义，不构成发布阻断）
- **Blockers (behavior only):** `E-contract`
- **Semantic-only notes:** `V4-F12-04`

## Dimensions（0-10）
- final_code: **10.0**
- security: **9.7**
- migration: **10.0**
- esp_deploy: **9.3**
- process_truth: **10.0**

## Findings

### 做得好的
1. **Ambient 正确关闭（F3=16）**：high 强度已足够处理这个边界。
2. **Voice / Migration / Sleep / Auth / Regression 全满分**。
3. **44/45 hidden，仅剩 reason 精度 + topic 标记两个小缺口**。

### 主要缺口
1. **`E-contract`（F8-07）**：topic stream `tof1` 标记缺失——high 修复了 ambient 但错过了这个细节。
2. **F12-04 reason**：同系列共性问题。

### 思考强度梯度

| 强度 | 耗时 | Ability | Class | 缺项 |
|:---:|:---:|:------:|:-----:|:----|
| **xhigh** | ~24 min | **99** | A | 仅 F12 reason |
| **high** | ~13 min | **98** | A | F8 topic stream + F12 |
| **medium** | ~8 min | **91** | B+ | F3 ambient + F8 mqtt + F12 |

边际收益递减明显：
- medium→high（+5 min）：**修复 ambient（+5）**，topic stream 仍漏
- high→xhigh（+11 min）：**修复 topic stream（+1）**，逼近满分

13 分钟出 **98 分**是性价比最优的档位——仅差一个 topic 标记到满分。

## Recommendation
- **accept**
- 一句话：GPT-5.6-sol @ Codex High 是 **「13 分钟 98 分，仅 topic 标记 + reason 精度两个 1 分缺口，A 级」** 的高性价比样本；high 是思考强度-质量 Pareto 最优档。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格
- [x] 未用 82 墙
- [x] 三档思考强度对比分析
