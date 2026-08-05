# Project2 评测轮次总结（2026-07-18 · 中途快照）

> **已被终稿取代：** 请读 [`ROUND_SUMMARY_20260719.md`](./ROUND_SUMMARY_20260719.md)。  
> 下文保留作 07-18 当日压缩前快照；**数字以 0719 终稿与 `v4.1b_scoreboard.md` 为准**。

**目的（历史）：** 在上下文压缩前固化本轮结论。  
**现行主线：** **V4.1b**（`project2-v4.1b`）  
**日期跨度：** 约 2026-07-18（同日完成归档、尺子升级与多模型锚点）  
**状态（历史）：** 锚点主体进行中 —— **后续已在 0719 闭环**

---

## 0. 一句话

> 先完整冻结 V4.0 → 做 V4.1a（F6 不连坐 + multi-run）→ 做 V4.1b（ambient 不连坐 F5）→ 在 live 主空间锚点一圈。  
> **顶端可达 99/A**（sol、DeepSeek 灰度）；榜上拉开 **99→86**；Grok Build 已无 Composer；日常不再用 handoff。

---

## 1. 版本与仓库状态

### 1.1 版本线

| 版本 | 含义 | 正式成绩 |
|------|------|----------|
| **V4.0** | Ability/Ship、F1–F12、Gold 100、handoff 曾为正式投放 | 冻结：`archives/v4_round_final_20260718/` + `v4_scoreboard.md` |
| **V4.1a** | F6 独立 fixture；multi-run meta；benchmark `project2-v4.1` | 历史：`v4.1_scoreboard.md`（Grok 91 / HY 86 / luna 91） |
| **V4.1b** | ambient 只扣 F3-05；F5-05 仅授权 care；benchmark `project2-v4.1b` | **现行：** `evaluator/reports/v4.1b_scoreboard.md` |

**禁止：** 用新规则重算 V4.0 / V4.1a 已写入正式分。

### 1.2 关键仓库改动（尺子）

**V4.1a**

- `test_db_migration.py`：F6-01 全最老库；F6-02..05 中间态独立
- scorer：`M-crash` cascade 标注；F6 可 7/10 而非 0/10
- `run_full_eval`：`--run-group-id` / `--run-index` / `--thinking-level` / `--meta-extra`
- multi-run 主列 Ability = **worst**

**V4.1b**

- F5-05 → `test_care_event_authorized_context_includes_care`（只测授权 care）
- F3-05 播种 care 标记 + zero-leak（unauth care 只扣一次）
- scorer：`S-ambient` cascade；`cascades[]`
- registry `v4.1b` / Gold gate `20260718_162420` → **100/A**

**运维**

- 默认：**live `workspace/project2_task` + `make_broken_project` 重置**
- handoff 脚本保留，**日常不用**；已删 `modeltest_candidate_handoffs/`（约 180MB）
- Composer channel 勘误：全程 **grok-cli**，不是 Cursor

### 1.3 关键路径索引

| 用途 | 路径 |
|------|------|
| 现行榜 | `evaluator/reports/v4.1b_scoreboard.md` |
| V4.1a 历史榜 | `evaluator/reports/v4.1_scoreboard.md` |
| V4.0 冻结 | `archives/v4_round_final_20260718/` |
| V4.0 Gold | `archives/v4_gold/` |
| 设计 | `docs/v4.1/DESIGN.md`、`V4.1b_NOTES.md`、`MULTI_RUN_PROTOCOL.md` |
| 候选/评审提示词 | `CANDIDATE_PROMPT.md`、`REVIEWER_PROMPT.md` |
| V5 远期（未开工） | `docs/V5_DESIGN_DIRECTION.md` |
| 本总结 | `docs/v4.1/ROUND_SUMMARY_20260718.md` |

---

## 2. 现行 V4.1b 主榜（截止写总结时）

| 名次 | 模型 | 渠道 | n | Ability | Ship | Class | result_id（代表） |
|:--:|------|------|:-:|--------:|-----:|:----:|-------------------|
| 1 | GPT-5.6-sol | Codex high | 1 | **99** | 99 | **A** | `20260718_201302` |
| 1 | DeepSeek-V4-Pro | OpenCode 灰度正式 | 1 | **99** | 99 | **A** | `20260718_212524` |
| 3 | GPT-5.6-luna | Codex high | 1 | **96** | 96 | **B+** | `20260718_165643` |
| 4 | GPT-5.6-terra | Codex high | 1 | **94** | 94 | **B+** | `20260718_222503` |
| 5 | GLM-5.2 | WorkBuddy **xhigh** | 1 | **91** | 91 | **B+** | `20260718_204550` |
| 5 | Grok-4.5 | grok-cli | 2 | **90**（worst） | 65–88 | D–B+ | run1 `170848` / run2 `172417` |
| 7 | HY-3 | WorkBuddy | 1 | **86** | 86 | **B+** | `20260718_192716` |

**Gold：** `20260718_162420` → 100/A（V4.1b + ESP build）

评审均在 `evaluator/reviews/v4.1b_*.md`（V4.1a 为 `v4.1_*`）。

---

## 3. 关键结论（按主题）

### 3.1 尺子是否有效

| 问题 | 结论 |
|------|------|
| F6 0/10 双峰 | **已缓解**。HY/Grok 可 F6=5–7；仅 F6-01 crash 不连坐 fidelity |
| ambient −7 软墙（F3−5+F5−2） | **V4.1b 已拆**。ambient 只 −5；F5 可仍满分 |
| 顶端是否可满分 | **几乎可以**：sol / DeepSeek **99/A**；Gold 100 |
| 是否拉开差距 | **是**：99 → 96 → 94 → 91 → 90 → 86 |

### 3.2 GPT-5.6 三产品 @ Codex high

| 产品 | Ability | Class | 主缺口 |
|------|--------:|-------|--------|
| sol | 99 | A | 仅 F12 reason |
| luna | 96 | B+ | F6 backfill、tof1、F12（**无 ambient**） |
| terra | 94 | B+ | **仅 ambient** + F12；F6/ESP 满 |

- **sol > luna > terra**（本轮 single-obs）  
- luna **不具备稳定满分**叙事已成立  
- high 档不等于 A；ambient 仍是常见 B+ 闸门

### 3.3 DeepSeek-V4-Pro（灰度正式）

| 项 | 值 |
|----|-----|
| 第一枪 | **99/A**，仅 F12，ESP 满分 |
| 费用 | 操作者报 **~$0.12**，性价比极强 |
| V4.0 同 harness | **82/B** → 本枪 **99/A**（质变级，勿只归因尺子） |
| 第二枪 | **中途被路由到预览版**，作废；**不入榜**；等正式版稳定再 n=2 |

### 3.4 其它模型要点

| 模型 | 要点 |
|------|------|
| **Grok-4.5** | n=2：Ability 稳定 90–91；run1 **session spoof → Ship 65/D** 属轨迹失常；run2 恢复 91/88/B+。ambient+F6-01 两跑都有。Composer 曾误标 Cursor，实为 **grok-cli**；Grok Build 现 **无 Composer 可选** |
| **HY-3** | 4.1a/4.1b 均为 **86**；4.1b 结构变：F5 满、多 no-actor、F6=5、F8 较好 |
| **GLM-5.2 xhigh** | **91/B+**，**无 M-crash**；远高于 V4.0 WB 中思考 81。勿全归因 xhigh；single-obs |
| **Doubao Evolving-0714**（V4.0） | **82/B**：ambient + F6 全家 0 + ESP 满分。相对 2.0-Code 约 +1。**待 V4.1b 重测**（workspace 已重置） |

### 3.5 常见失败模式（本轮）

| 模式 | 谁常中 | Ability 影响（4.1b） |
|------|--------|---------------------|
| ambient | terra、GLM、Grok、HY | −5 + Class B+ |
| F6-01 crash | Grok、HY（GLM 本跑已过） | −3，Ship≤88 |
| F6-03 backfill | luna、GLM、sol 无 | −2 |
| F12 reason | 几乎所有强模型 | −1，不进 S-* |
| ESP 契约碎扣 | luna tof1、HY lwip、GLM wifi_ssid | −1～−3 |
| session spoof | Grok run1 | Ship 65 / D |

### 3.6 渠道 / 工具

- **Composer @ Grok Build：** 2026-07 中下旬起 `grok models` 仅 `grok-4.5`；Composer 不可选（社区与本机一致）
- **默认测法：** 主空间 `workspace/project2_task`，不做 handoff
- **效率：** DeepSeek ~$0.12/99 极突出；效率副榜模板在 `v4.1_efficiency_board.md`（未系统填）

---

## 4. 未完成 / 下一步

| 状态 | 事项 |
|------|------|
| **就绪待跑** | Doubao Evolving（或当周新 seed 名）@ OpenCode → V4.1b |
| **暂停** | DeepSeek 第二轮（等正式版稳定，防预览路由） |
| **可选** | Kimi K2.7；效率副榜补 cost；Grok/GLM/luna n=2 |
| **不做** | 用 4.1b 重算历史正式分；V5 新鲜度/真机（仍 memo） |

### 日常命令

```powershell
python evaluator\make_broken_project.py
# 模型改 workspace\project2_task
python evaluator\run_full_eval.py workspace\project2_task `
  --model NAME --channel CH --harness H `
  --require-meta --include-espidf-build `
  --run-group-id GROUP --run-index N --thinking-level LEVEL
```

评审：`REVIEWER_PROMPT.md` → `evaluator/reviews/v4.1b_{model}_{channel}_{RESULT_ID}.md`  
写榜：`evaluator/reports/v4.1b_scoreboard.md`

---

## 5. 关键数字对照（记忆锚点）

| 对照 | 数字 |
|------|------|
| V4.0 中游墙 | 常 81–82（ambient + M-crash） |
| V4.1a ambient 连坐 | Ability 约 −7 → 91 扎堆（luna/Grok） |
| V4.1b ambient | 只 −5；F5 可 12 |
| 顶端 | **99/A**（sol、DeepSeek 灰度） |
| Gold | **100/A** `20260718_162420` |
| Grok Ship 波动 | 65（spoof）– 88（M-crash gate） |
| DeepSeek 价 | ~**$0.12** / 99 分（操作者记录） |

---

## 6. 给下一会话的接续指令（可复制）

1. 读本文件 + `evaluator/reports/v4.1b_scoreboard.md`  
2. 现行规则：**V4.1b**，不重算 V4.0/4.1a  
3. 默认评测路径：`workspace\project2_task`  
4. 待办：Doubao Evolving V4.1b；DeepSeek n=2 等稳定版  
5. 打分产出：`v4.1b_*.md` review + 更新 scoreboard  

---

*写于 2026-07-18，供压缩/换会话后无损接续。*
