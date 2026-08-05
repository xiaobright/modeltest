# 附录：V2 样本在 V4 规则下的示意重标注

> **重要**：以下为 **illustrative relabel**，不是重新跑测后的官方 V4 分。  
> 依据：`v2_scoreboard_current.md`、`v2_soft_cap_experimental_scoreboard.md`、各 review 叙述。  
> 误差带：约 ±3 Ability。用于检验「82 团是否被拉开」。

## 1. 方法摘要

1. 以 V2 正式分与 soft-cap 叙述为起点。  
2. 将已知失败映射到 F3e / F6 / F8 / F9 / F12 等扣分。  
3. Ability ≈ 100 − Σ(family 合理扣分)。  
4. Ship 套用信任 cap + F3 门槛（见 `02`）。  

## 2. 对照总表

| 模型 | 渠道 | V2 正式 | V2 soft | V4 Ability≈ | V4 Ship≈ | Class | 主 Blockers | evidence_source |
|------|------|--------:|--------:|------------:|---------:|-------|-------------|------------------|
| GPT-5.5 | Codex | 96 | 96.0 | **97** | **97** | A | 轻微 F12 | hidden_v2_remap |
| Grok-4.5 | workspace | 96 | 95.7 | **96** | **96** | A | F12 小、报告 nit | hidden_v2_remap |
| GLM-5.2 | Opencode/API | 95 | 95.0 | **95** | **95** | A | F12/E-contract 轻 | hidden_v2_remap |
| GLM-5.2 | 火山/Opencode | 89 | 88.9 | **91** | **88** | B+ | `M-crash` | hidden_v2_remap |
| GPT-5.4 | Codex | 88 | 88.3 | **90** | **88** | B+ | `M-crash` | hidden_v2_remap |
| Kimi K2.7 Code | Opencode/API | 82 | 88.0 | **88** | **88** | B+ | `S-ambient`, M-fidelity | hidden_v2_remap |
| GLM-5.2 | WorkBuddy | 88 | 87.8 | **89** | **88** | B+ | `M-crash` | hidden_v2_remap |
| doubao-seed-2.0 | Opencode/API | 86 | 86.0 | **87** | **87** | B+ | `M-crash`, E-contract | hidden_v2_remap |
| GLM-5.1 | Qoder | 82 | 86.0 | **86** | **86** | B+ | `S-ambient` | hidden_v2_remap |
| Mimo v2.5 Pro | Opencode/API | 82 | 85.0 | **85** | **85** | B+ | `S-ambient`, M-fidelity | hidden_v2_remap |
| LongCat-2.0 | workspace | 82 | 84.5 | **85** | **85** | B+ | `S-ambient`, E-contract | hidden_v2_remap |
| DeepSeek V4 Flash | Opencode/API | 82 | 84.0 | **84** | **84** | B | `S-ambient`, `M-crash` | hidden_v2_remap |
| Composer 2.5 | grok-cli | 82 | 83.5 | **83** | **83** | B | `S-ambient`, `M-crash` | review_inferred |
| Minimax M3 | Opencode/API | 82 | 83.0 | **83** | **83** | B | `S-ambient`, `M-crash` | review_inferred |
| Gemini 3.5 Flash | Antigravity | 79 | 79.0 | **80** | **80** | C+ | 多处 S/M | review_inferred |
| Mimo v2.5 Flash | Opencode/API | 72 | 72.0 | **74** | **72** | C- | `E-build`, `P-report` | review_inferred |
| Minimax M2.5 | Opencode/API | 66 | 66.0 | **70** | **66** | D | `F-public`, `E-build`, `P-report` | review_inferred |

### 读表要点

**evidence_source 列含义（MiniMax-M3 S8 增补）**：

| 取值 | 含义 |
|------|------|
| `hidden_v4` | V4 新增 item 实测（F3/F12 拆分落地后才有此值） |
| `hidden_v2_remap` | V2 hidden 结果按 V4 family 映射（hidden 数 27–34 + family 加总） |
| `review_inferred` | 从 V2 review 叙述推断（缺乏结构化 hidden 数据） |

`score_draft_confidence.json` 写入时，每行的 `evidence_source` 与 `score_draft.json` 的 `family_draft` 一一对应，置信度评估规则：

- 全部 `hidden_v4` → `confidence: high`
- 全部 `hidden_v2_remap` 或混合 → `confidence: medium`，需人工 final
- 任一 `review_inferred` → `confidence: low`，必须人工 final

> **重要**：当前 relabel 表 18 行中有 14 行是 `hidden_v2_remap`、4 行是 `review_inferred`——所有行置信度至少为 `medium`；4 行置信度为 `low`，必须人工 final 才进 V4 主榜。

### 4 个核心观察

1. **原 82 团 Ability 摊到约 83–88**，不再同一整数。  
2. **Ship 不再因 `S-ambient` 被压到固定天花板**：Kimi K2.7 Ability 88 → Ship 88（Class B+），Ability 83 的 Composer → Ship 83（Class B）。发布风险由 Class 表达，数值能力由 Ability 拉开。  
3. **顶部 A 档**仍由无严重 S/M-crash 且高完成度模型占据。  
4. **信任崩坏**（M2.5）Ship 仍被硬顶压住。  

## 3. 个例拆解（便于审核攻击）

### 3.1 Kimi K2.7 Code（V2=82 → Ability≈88）

已知：ESP static/build 强；admin/sleep 好；`S-ambient`；迁移保真问题。  

| Family | 估分 | 说明 |
|--------|-----:|------|
| F1 | 7/8 | 过程大体完整 |
| F2 | 12/12 | auth 全 |
| F3 | 11/16 | 扣 F3e 5 分 |
| F4 | 0–2/4 | 多半未做 bridge（估 0） |
| F5 | 11/12 | 主链好 |
| F6 | 7/10 | 保真问题 |
| F7 | 8/8 | |
| F8 | 8/8 | |
| F9 | 6/6 | build 过 |
| F10 | 8/8 | |
| F11 | 3/4 | |
| F12 | 2/4 | 估 |
| **Ability** | **≈88** | |
| **Ship** | **≈88** | `S-ambient` → Class B+（无 89 硬顶） |

V2 把上述压成 82；V4 保留「不能当 A 发布」，但 Ship 与 Ability 同阶，不抹掉 ESP/主线完成度。

### 3.2 Composer 2.5（V2=82 → Ability≈83）

已知：快；ESP 模块化好；`S-ambient`；缺 ts 迁移；`S-no-actor` 类问题更重。  

| 主要扣分 | 估 |
|----------|-----|
| F3e + 可能 F3d | −5～−7 |
| F6a/c | −3～−5 |
| F4 | −4 |
| F8 轻 | −1 |
| **Ability** | **≈83** |
| **Ship** | **≈83**（M-crash 与 S-ambient 均不再制造新天花板） |

与 Kimi K2.7 的 Ability 差距 **约 5 分**，正是 V4 要露出的。

### 3.3 GPT-5.5（V2=96 → Ability≈97）

仅 F12 reason 类小问题；无 S-ambient。  
Ability/Ship 仍顶部；F12 降权后甚至略高于「把 reason 当 hidden 硬失败」的观感。

### 3.4 Minimax M2.5（V2=66）

public 失败 + build 失败 + 报告甩锅 → 信任 cap。  
Ability 草稿可因部分 hidden 偏高而到 70+，**Ship 仍 ≤66–68**。  
V4 继续惩罚「不可信交付」。

## 4. 对「是不是题只让 GPT 高分」的含义

重标注后：

- 非 GPT 顶部（GLM-5.2、Grok-4.5）仍在 A/高分带 → 题不是 GPT 私锁。  
- 原 82 团内部出现 83–88 梯度 → 过去「只有 GPT 破局」部分来自 **cap 结构**，不是全体不会做题。  
- 若未来实施真跑后非 GPT 仍无法过 F3e/F6，那是 **能力差**，不是评分格式问题。  

## 5. 审核时请验证

- [ ] 表中 Ability 排序是否与你对 review 的直觉一致？  
- [ ] Ship 门槛是否错误抬高/压低了某类模型？  
- [ ] 是否需要把 F4 估分改为「未知则给中位 2 分」的规则？  

---

## 文档包结束

返回索引：[README.md](./README.md)
