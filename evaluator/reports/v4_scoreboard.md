# Project2 V4 成绩榜

**基准版本：** V4.0 frozen  
**榜单修订：** 2026-07-12 corpus update  
**更新：** 2026-07-12  
**排序：** Ability 降序（同 Ability 时按 Ship）

规则摘要：Ability = 工程完成度；Ship / Class = 发布风险；`S-ambient` 等行为 blocker **不**做 82 数值硬顶；reason-only 只进 F12。

---

## 主榜（Ability）

| 名次 | 模型 | 渠道/强度 | Ability | Ship | Class | 主缺口 / Behavior Blockers | 评审 |
|:--:|---|---|:---:|:---:|:---:|:---|:---|
| 1 | GPT-5.6-sol | Codex xhigh | **99** | 99 | **A** | 仅 F12 reason-only | `v4_gpt-5.6-sol_codex_*.md` |
| 1 | GPT-5.6-luna | Codex xhigh | **99** | 99 | **A** | 仅 F12 reason-only | `v4_GPT-5.6-luna_codex_*.md` |
| 3 | GPT-5.6-sol | Codex high | **98** | 98 | **A** | `E-contract` | `v4_GPT-5.6-sol_codex-high_*.md` |
| 3 | GPT-5.6-luna | Codex high | **98** | 98 | **A** | `E-contract` | `v4_GPT-5.6-luna_codex-high_*.md` |
| 5 | GPT-5.6-terra | Codex high | **97** | 97 | **A** | `E-contract` | `v4_GPT-5.6-terra_codex-high_*.md` |
| 6 | GPT-5.6-terra | Codex xhigh | **95** | 95 | **A** | F4 voice 未改 | `v4_GPT-5.6-terra_codex_*.md` |
| 7 | Gemini-3.5-Flash | Antigravity | **93** | 93 | **B+** | `S-no-actor`, `P-report` | `v4_Gemini-3.5-Flash_antigravity_*.md` |
| 8 | GPT-5.5 | Codex xhigh | **92** | 92 | **B+** | `S-ambient` | `v4_GPT-5.5_codex-xhigh_*.md` |
| 8 | HY-3 | WorkBuddy | **92** | 92 | **B+** | `S-ambient` | `v4_HY-3_workbuddy_*.md` |
| 8 | Composer-2.5 | grok-cli | **92** | 92 | **B+** | `S-ambient` | `v4_composer-2.5_grok-cli_*.md` |
| 11 | GPT-5.4 | Codex xhigh | **91** | 91 | **B+** | `S-ambient`, `E-contract` | `v4_GPT-5.4_codex-xhigh_*.md` |
| 11 | GPT-5.6-sol | Codex medium | **91** | 91 | **B+** | `S-ambient`, `E-contract` | `v4_GPT-5.6-sol_codex-medium_*.md` |
| 13 | Kimi-K2.7-Code | Qoder | **90** | 90 | **B+** | `S-ambient`, `M-fidelity` | `v4_Kimi-K2.7-Code_qoder_*.md` |
| 13 | Gemini-3.1-Pro | Antigravity | **90** | **60** | **D** | 明文密码（Ship cap 60） | `v4_Gemini-3.1-Pro_antigravity_*.md` |
| 15 | HY-3 | OpenCode | **86.5** | 86.5 | **B+** | `S-ambient`, `P-report`, `E-contract` | `v4_HY-3_opencode_*.md` |
| 16 | Minimax-M3 | WorkBuddy | **84** | 84 | **B** | `S-ambient`, `R-regression` | `v4_minimax-m3_workbuddy_*.md` |
| 17 | Grok-4.5 | grok-cli | **82** | 82 | **B** | `S-ambient`, `M-crash` | `v4_grok-4.5_grok-cli_*.md` |
| 17 | DeepSeek-V4-Pro | OpenCode | **82** | 82 | **B** | `S-ambient`, `M-fidelity`, `E-contract` | `v4_DeepSeek-V4-Pro_opencode_*.md` |
| 17 | GLM-5.2 | OpenCode | **82** | 82 | **B** | `S-ambient`, `M-crash`, `M-fidelity` | `v4_GLM-5.2_opencode_*.md` |
| 20 | GLM-5.2 | WorkBuddy | **81** | 81 | **B** | `S-ambient`, `M-crash`, `E-contract` | `v4_glm-5.2_workbuddy_*.md` |
| 20 | GLM-5.2 | Qoder | **81** | 81 | **B** | `S-ambient`, `M-crash`, `P-report` | `v4_glm-5.2_qoder_*.md` |
| 20 | LongCat-2.0 | OpenCode | **81** | 81 | **B** | `S-no-actor`, `S-ambient`, `M-fidelity` | `v4_LongCat-2.0_opencode_*.md` |
| 20 | Doubao-Seed-2.0-Code | OpenCode | **81** | 81 | **B** | `S-no-actor`, `S-ambient`, `M-fidelity` | `v4_Doubao-Seed-2.0-Code_opencode_*.md` |
| 24 | Qwen-3.7-Max | Qoder | **76** | 76 | **B** | `S-ambient`, `M-crash`, `E-contract` | `v4_Qwen-3.7-Max_qoder_*.md` |
| 25 | Minimax-M2.7 | Qoder | **61** | **60** | **D** | 明文密码、cookie 绕过 | `v4_minimax-m2.7_qoder_*.md` |

---

## 发布视角（Release）

| Class | 含义 | 本榜样本 |
|-------|------|----------|
| **A** | 接近可合并 | GPT-5.6-sol、GPT-5.6-luna、GPT-5.6-terra |
| **B+** | 完成度高，仍有发布阻断 | Gemini-3.5-Flash、GPT-5.5、HY-3、Composer、GPT-5.4、GPT-5.6-sol medium、Kimi-K2.7-Code |
| **B** | 主线大体完成，多项缺口 | M3、Grok、GLM×3、LongCat、Doubao、DeepSeek |
| **D** | 信任/鉴权不可接受 | Gemini-3.1-Pro、M2.7 |

---

## 参考基线（不进排名）

| 说明 | Ability | Ship | Class | result_id |
|------|--------:|-----:|-------|-----------|
| Gold 自检（归档树 + 真实 ESP-IDF build） | **100** | 100 | **A** | `20260711_222515` |
| Broken seed 冒烟 | 45.5 | 45.5 | D | `20260711_174033` |

---

## 今日新增样本（2026-07-12）

| 模型 | 渠道 | Ability | Ship | Class | 主缺口 |
|:---|:---:|:------:|:----:|:-----:|:------|
| HY-3 | WorkBuddy | **92** | 92 | B+ | `S-ambient` |
| HY-3 | OpenCode | **86.5** | 86.5 | B+ | `S-ambient`, `P-report`, `E-contract` |
| Kimi K2.7 Code | Qoder | **90** | 90 | B+ | `S-ambient`, `M-fidelity` |
| DeepSeek-V4-Pro | OpenCode | **82** | 82 | B | `S-ambient`, `M-fidelity` |
| GLM-5.2 | OpenCode | **82** | 82 | B | `S-ambient`, `M-crash` |
| LongCat-2.0 | OpenCode | **81** | 81 | B | `S-no-actor`, `S-ambient`, `M-fidelity` |
| Doubao-Seed-2.0-Code | OpenCode | **81** | 81 | B | `S-no-actor`, `S-ambient`, `M-fidelity` |
| Qwen-3.7-Max | Qoder | **76** | 76 | B | `S-ambient`, `M-crash`, `E-contract` |
| GPT-5.6-terra | Codex | **95** | 95 | A | F4 voice 未改 |
| GPT-5.6-luna | Codex | **99** | 99 | A | 仅 F12 reason-only |

---

## 相关文件

| 文件 | 内容 |
|------|------|
| `evaluator/reports/v4_round_report.md` | V4 正式说明 |
| `evaluator/reports/v4_freeze_manifest.md` | 正式结果与证据锁定 |
| `evaluator/reviews/v4_*.md` | 单模型评审 |
| `archives/v4_gold/` | 满分金标准 |
| `archives/second_round_v2_final_20260711/` | V2 历史冻结（对照用） |
