# V4 Review: GPT-5.6-terra @ Codex (High)

## Meta
- result_id: `20260712_194212`
- harness: Codex (high thinking)
- tool_interference: **no**
- duration: **~15 min / $2.01**
- 操作者备注: 对比 terra xhigh（95/A, 24min, $4.00）

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **44 / 45**（仅 1 fail）
  - **F12-04** reason-only：`not_authenticated` ≠ `not_authorized_for_target`
  - **无** S-ambient / S-no-actor / M-crash / trust
- esp static: **7 / 9**（2 failed：`mqtt` 缺 REQUIRES + topic `tof1` 标记缺失）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **97.0 / 97.0 / B+**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 全过 |
| F2 | 12 | **12** | auth 满分 |
| F3 | 16 | **16** | **满分：无 ambient** |
| F4 | 4 | **4** | voice 正确接入（**xhigh 版没做对，high 反而对了**） |
| F5 | 12 | **12** | care 全链过 |
| F6 | 10 | **10** | 迁移满分 |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 6 | **6** | `mqtt` 缺 REQUIRES（−1）+ topic `tof1` 标记缺失（−1） |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实 |
| F12 | 3 | **3** | reason 精度 |

**Ability：** 8+12+16+4+12+10+8+6+6+8+4+3 = **97**

## Final scores
- **Ability:** **97 / 100**
- **Ship:** **97 / 100**
- **Class:** **A**（仅 E-contract + F12 语义）
- **Blockers (behavior only):** `E-contract`
- **Semantic-only notes:** `V4-F12-04`

## Dimensions（0-10）
- final_code: **10.0**
- security: **9.7**
- migration: **10.0**
- esp_deploy: **8.6**
- process_truth: **10.0**

## Findings

### 做得好的
1. **F4 voice 正确**：xhigh 反而没做对——**随机覆盖差异**，非强度问题。
2. **F3=16 无 ambient** + **F6=10 迁移满分**。
3. **44/45 hidden，零 behavior 安全泄漏**。

### 主要缺口
1. **`E-contract`（F8 −2）**：mqtt REQUIRES + topic 标记双缺。
2. **F12-04 reason**：同系列通病。

### xhigh vs high terra 对比

| 强度 | 耗时 | 花费 | Ability | Class | F4 voice | F8 |
|:---:|:---:|:---:|:------:|:-----:|:--------:|:--:|
| high | 15 min | **$2.01** | **97** | A | ✅ 4/4 | 6/8 |
| xhigh | 24 min | **$4.00** | **95** | A | ❌ 0/4 | 6/8 |

High 版便宜一半，反而因 voice 覆盖运气好多了 2 分。F8 双缺两版一致——这是 terra 自身的系统性细节遗漏，不随强度变化。

### 全系列性价比图

| 型号 | 强度 | 耗时 | 花费 | Ability | CPI |
|:---|:---:|:---:|:---:|:------:|:---:|
| luna | xhigh | 24 min | $2.11 | **99** | 46.9 分/刀 |
| sol | xhigh | 24 min | $7.25 | **99** | 13.7 分/刀 |
| sol | high | 13 min | $3.49 | **98** | 28.1 分/刀 |
| **terra** | **high** | **15 min** | **$2.01** | **97** | **48.3 分/刀** |
| sol | medium | 8 min | $2.32 | 91 | 39.2 分/刀 |
| terra | xhigh | 24 min | $4.00 | 95 | 23.8 分/刀 |

**Terra high 以 $2.01 拿到 97 分，CPI 48.3 分/刀——性价比全场最佳。**

## Recommendation
- **accept**
- 一句话：GPT-5.6-terra @ Codex High 是 **「$1.88 拿 97 分、44/45 hidden、仅 ESP 细节 + F12 语义两个小缺口的极致性价比选择」**。

## Self-check
- [x] Ability-first
- [x] reason-only 未升格
- [x] 未用 82 墙
- [x] 全系性价比对比
