# V4 Review: GPT-5.6-luna @ Codex (High)

## Meta
- result_id: `20260712_213626`
- harness: Codex (high thinking)
- tool_interference: **no**
- duration: **~18 min / $1.29**
- 操作者备注: 系列收尾——luna high 性价比验证

## Automatic evidence
- public: **pass**
- debug_probe: **pass**
- hidden: **44 / 45**（仅 1 fail）
  - **F12-04** reason-only
  - **无** S-ambient / S-no-actor / M-crash / trust / P-report
- esp static: **8 / 9**（1 failed：topic stream `tof1` 标记缺失）
- esp build: **real_pass**
- draft Ability / Ship / Class（机器）: **98.0 / 98.0 / B+**

## Family breakdown（终裁）

| Family | Draft | Final | 调整理由 |
|--------|------:|------:|----------|
| F1 | 8 | **8** | process 全过 |
| F2 | 12 | **12** | auth 满分 |
| F3 | 16 | **16** | **满分：无 ambient** |
| F4 | 4 | **4** | voice 正确 |
| F5 | 12 | **12** | care 全链过 |
| F6 | 10 | **10** | 迁移满分 |
| F7 | 8 | **8** | sleep 全过 |
| F8 | 7 | **7** | topic `tof1` 标记缺失（−1, E-contract） |
| F9 | 6 | **6** | real_pass |
| F10 | 8 | **8** | 回归过 |
| F11 | 4 | **4** | PR 充实 |
| F12 | 3 | **3** | reason 精度 |

**Ability：** 8+12+16+4+12+10+8+7+6+8+4+3 = **98**

## Final scores
- **Ability:** **98 / 100**
- **Ship:** **98 / 100**
- **Class:** **A**（仅 E-contract + F12 语义）
- **Blockers (behavior only):** `E-contract`
- **Semantic-only notes:** `V4-F12-04`

## Findings

### 做得好的
1. **F3=16 无 ambient + F4=4 voice + F6=10 迁移满分**。
2. **44/45 hidden，零 behavior 安全泄漏**。
3. **$1.29 拿到 98 分——性价比碾压全场**。

### 主要缺口
1. **`E-contract`（F8-07）**：topic `tof1` 标记缺失（与 sol high 同款问题）。
2. **F12-04 reason**。

### Luna high vs Terra high vs Sol high

| 模型 | 强度 | 耗时 | 花费 | Ability | CPI |
|:---|:---:|:---:|:---:|:------:|:---:|
| sol | high | 13 min | $3.49 | **98** | 28.1 分/刀 |
| terra | high | 15 min | $2.01 | **97** | 48.3 分/刀 |
| **luna** | **high** | **18 min** | **$1.29** | **98** | **76.0 分/刀** |

**你的结论完全正确：luna high 和 terra high 拉不开差距（98 vs 97），但 luna 便宜 36%。** 以后日常用 luna high 是最优解。

### 全赛道终榜（更新）

| 名次 | 模型 | 渠道 | Ability | Class |
|:--:|:---|:---:|:------:|:-----:|
| 1 | GPT-5.6-sol | Codex xhigh | **99** | A |
| 1 | GPT-5.6-luna | Codex xhigh | **99** | A |
| 3 | GPT-5.6-sol | Codex high | **98** | A |
| 3 | **GPT-5.6-luna** | **Codex high** | **98** | **A** |
| 5 | GPT-5.6-terra | Codex high | **97** | A |
| 6 | GPT-5.6-terra | Codex xhigh | **95** | A |
| 7 | Gemini-3.5-Flash | Antigravity | **93** | B+ |
| 8 | GPT-5.5 | Codex xhigh | **92** | B+ |
| 8 | HY-3 | WorkBuddy | **92** | B+ |
| 8 | Composer-2.5 | grok-cli | **92** | B+ |
| 11 | GPT-5.4 | Codex xhigh | **91** | B+ |
| 11 | GPT-5.6-sol | Codex medium | **91** | B+ |
| 13 | Kimi-K2.7-Code | Qoder | **90** | B+ |
| 13 | Gemini-3.1-Pro | Antigravity | **90** | **D** |
| 15 | HY-3 | OpenCode | **86.5** | B+ |
| 16 | Minimax-M3 | WorkBuddy | **84** | B |
| 17 | Grok-4.5 / DeepSeek-V4-Pro / GLM-5.2×3 / LongCat-2.0 / Doubao | 各渠道 | 81-82 | B |
| 22 | Qwen-3.7-Max | Qoder | 76 | B |
| 23 | Minimax-M2.7 | Qoder | 61 | D |

## Recommendation
- **accept**（日常使用推荐 luna high，$1.29/98 分）
- 一句话：GPT-5.6-luna @ Codex High 是 **「98 分 A 级、仅 topic 标记 + reason 精度两个 1 分缺口、$1.29 全场性价比之王的终极推荐」**。
