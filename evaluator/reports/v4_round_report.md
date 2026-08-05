# Project2 第 4 版（V4）评测报告

> **历史说明：** 本文件是首批 7 个 V4 样本的校准报告。25 次运行的最终分析见
> `evaluator/reports/v4_v2_comparison_final.md`。

**日期：** 2026-07-11  
**状态：** V4.0 已转正（正式成绩榜）  
**成绩榜：** [`v4_scoreboard.md`](./v4_scoreboard.md)

---

## 1. 本轮设置

- **Seed：** `project2-v4-broken-seed`（V2 工程壳 + V4 题库/种子补丁）  
- **流程：** 候选只见 `workspace/` → 完成后 `run_full_eval` → 人工按 rubric 终裁  
- **分数：** Ability（完成度）+ Ship/Class（发布）+ behavior blockers  
- **Gold：** `archives/v4_gold/`，自检 hidden 45/45、static 9/9、真实 build 通过、Ability 100 Class A  
- **冻结清单：** `evaluator/reports/v4_freeze_manifest.md`

与 V2 的主要差别：

- 取消「ambient 一刀切 82」  
- context behavior / reason（F3/F12）拆分  
- 迁移、mixed CSV、voice bridge 等独立计分  
- ESP static 与真实 build 分家  

---

## 2. 成绩总表

见 [`v4_scoreboard.md`](./v4_scoreboard.md)。摘要：

| 档位 | 代表 | Ability | 特征 |
|------|------|--------:|------|
| 顶尖 A | GPT-5.6-sol @ Codex | 99 | 仅 reason 细粒度；无 behavior blocker |
| 强 B+ | Composer 2.5 | 92 | 迁移/ESP 满；仅 ambient |
| 中上 B | M3 / Grok / GLM | 81–84 | ambient 常见；Grok/GLM 另有 M-crash |
| 信任 D | Minimax M2.7 | 61 / Ship 60 | 明文密码 + cookie 绕过 |

---

## 3. 主要发现

### 3.1 顶部分数可信

GPT-5.6-sol 在 **完整 V4 seed** 上 hidden 44/45、Class A，说明「全过仅 F12」在真题上可达 96–99，不是 remap 注水。

### 3.2 中上游靠收口拉开

| 缺口 | 影响样本 |
|------|----------|
| `S-ambient` | Composer、M3、Grok、GLM |
| `M-crash`（INDEX 先于补列） | Grok、GLM 双渠道 |
| sleep `first` / voice bridge | M3 等 |
| 明文密码 / 伪造 cookie | M2.7 |

### 3.3 工具链干扰要单独记

WorkBuddy / Qoder 上 ESP 常被沙箱、PATH、MinGW 拖累。本榜 **Ability 只看交付代码**；效率与 harness 摩擦写在评审 `tool_interference`，不进主分。

### 3.4 与 V2 的关系

- V2 完整语料冻结于 `archives/second_round_v2_final_20260711/`，**不删**。  
- V4 正式分 **不以** 旧 V2 分直接换算；跨版本只做叙事对照。  
- 曾有一版 Grok「96 remap」已废弃，正式 Grok 成绩为 **真 V4 重跑 82/B**。

---

## 4. 使用方式

```powershell
python evaluator\make_broken_project.py
# 生成项目外 allowlist workspace，只把脚本输出的 candidate_workspace 交付候选
python evaluator\prepare_candidate_handoff.py
python evaluator\run_full_eval.py <candidate_project> `
  --model NAME --channel CH --harness H `
  --require-meta --include-espidf-build
# 评审：REVIEWER_PROMPT.md → evaluator/reviews/v4_*.md
```

新成绩写入 `v4_scoreboard.md` 与对应 review，`model/channel/harness` 均必填。

---

## 5. 单模型评审索引

| 模型 | 文件 |
|------|------|
| GPT-5.6-sol | `reviews/v4_gpt-5.6-sol_codex_20260711_214016.md` |
| Composer 2.5 | `reviews/v4_composer-2.5_grok-cli_20260711_182425.md` |
| Minimax M3 | `reviews/v4_minimax-m3_workbuddy_20260711_193355.md` |
| Grok-4.5 | `reviews/v4_grok-4.5_grok-cli_20260711_210538.md` |
| GLM-5.2 WB | `reviews/v4_glm-5.2_workbuddy_20260711_190659.md` |
| GLM-5.2 Qoder | `reviews/v4_glm-5.2_qoder_20260711_204201.md` |
| Minimax M2.7 | `reviews/v4_minimax-m2.7_qoder_20260711_195139.md` |
| Gold 自检 | `reviews/v4_gold_verification_20260711_222515.md` |

---

## 6. 冻结说明

- 7 个正式样本在 F11 修复后重新计算，机器草稿与终裁差为 **-1 至 +3**。
- 首轮正式样本的 F9 满分标记为 `operator_attested_legacy`，不冒充 result-local artifact。
- 新 Gold result `20260711_222515` 直接评测归档树，并将 build log、bin、大小和 SHA256 固化在同一 result。
- scorer 会复算 result-local artifact 的路径、大小与 SHA256；仅 build 返回 0 不再获得 F9 满分。
- 5 个历史空 meta result 保持原样；canonical meta 只在 freeze manifest 中规范化。
