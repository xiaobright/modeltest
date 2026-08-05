# Kimi K2.7 Code 交叉审核意见

## 总裁决

**有条件同意。**

V4 的方向是正确的：以 V2 工程壳为唯一实施基底，拒绝 V3.1 的阶梯 hard-cap 排序器，用 Ship/Ability 双轨 + 阻断标签把「能不能发布」和「做了多少工程」拆开。这个设计与 V2 soft-cap 实验榜的经验数据一致，也能解释为什么 GPT-5.5/Grok-4.5/GLM-5.2 能到 95+ 而大批模型挤在 82——问题主要是评分结构，不是模型都不会做题。

但默认文本里仍有三个点会在实施中复刻「墙」的失败模式，必须在进入代码阶段前改掉。

---

## 必须修改（blocking）

### B1. F3e 的 Ship 数值上限 89 必须取消，改为仅 Class B+ 标记

当前 `02_SCORING_SYSTEM.md §4.3` 默认：过 F3a/b 但未过 F3e → `min(ship, 89)`。

问题：

- V2 中至少 8–10 个 82 团样本都带 `S-ambient`（Kimi K2.7、GLM-5.1、Mimo Pro、LongCat、Composer、DeepSeek Flash、Minimax M3 等）。
- 按 V4 默认规则，这些模型的 Ship 会全部落在 88–89，形成新的「89 墙」。
- Class B+ 已经准确表达了「不可 A 类发布」的语义；Ability 上 F3e 扣 5 分 + 其它 family 差异，足以把 82 团摊到 83–88（见附录示例），不需要再用 Ship 数值天花板压一次。
- 一旦对外传播只用一个数，89 会重蹈 82 的覆辙。

**建议修改**：

```diff
- | 过 F3a/b 但未过 F3e | min(ship, **89**) |
+ | 过 F3a/b 但未过 F3e | **不设 Ship 数值上限**；仅标记 Class B+，并在报告中显式列出 `S-ambient` |
```

_ship_gate_hint_ 可保留为提示性信息，不等同于硬顶。

### B2. 默认榜单视图必须明确为 Ability 降序

当前设计说「Release view + Ability view 双视图」，但没有指定默认主排序。若实施者或报告工具默认按 Ship 排序，B1 取消数值顶的效果会被抵消——模型 Ability 88 与 Ability 83 只要都有 `S-ambient`，就会贴在一起。

**建议修改**：

官方主榜默认：

```text
Rank | Model | Channel | Ability | Ship | Class | Blockers | ...
```

按 Ability 降序；同 Ability 时按 Ship 降序；Ship/Class 作为并列信息列。Release view（按 Ship/Class 筛选）作为第二视图，用于发布审批。

### B3. F1 不要引入基于 git 时间戳的「时序造假」自动扣分

DeepSeek 评审建议对比首次 commit 时间与 public.log 时间戳来检测「先修完再补写初始诊断」。

问题：

- 很多模型在修复过程中不频繁 commit，首次 commit 可能在大量修改之后；这会导致误报。
- 部分 harness（如 Qoder/WorkBuddy）会压缩或重置上下文，commit 时间戳与本地 public 运行时间没有稳定对应关系。
- git 时间戳可被随意设置，不能作为信任证据。
- F1 的核心应是「PR 内容与 diff/log 是否一致」+「未篡改测试/探针」，时序属于辅助观察，不应进自动打分。

**建议**：把「时序验证」降级到 `score_draft_confidence.json` 的 `notes` 或人工 review 提示，不在 F1 oracle 中自动扣分。

---

## 建议修改（non-blocking）

### S1. F9「无 IDF 环境」统一给 3 分并显式标记

当前是 2–3 分区间，容易因 reviewer 差异产生噪声。建议固定为 **3 分**，并在 `score_draft.json` 中写入 `f9_mode: "skipped_env"`。是否采用「分母缩小到 94」是可选的；关键是：

- 不给满分（6）。
- 不惩罚到 0–2（环境不可用 ≠ 造假）。
- 报告必须显式区分 `build_skipped` 与 `build_passed`。

### S2. F4 voice bridge 拆分为「识别 1 分 + 正确修复 3 分」

当前 F4 只有一项 4 分，全有或全无。实际中模型可能识别风险但没时间修完。拆成：

| 子项 | 分 | Oracle |
|------|---:|--------|
| F4a 识别风险 | 1 | PR/probe 中意识到 voice/RK3588 可能因 context 收紧而断裂 |
| F4b 正确修复 | 3 | 代码中 voice 路径在请求敏感 context 前获取显式 session |

这样保留 4–0 的区分度，同时给部分完成者 1 分。

### S3. F8-07 缓冲检查必须允许动态分配

Static 检查器不应只检测字面量 `char buf[256]`。`allowed_equivalents` 应明确写入：

- 动态分配（`malloc`/`new`/`std::string`/`std::vector`）视为正确。
- 仅标记「固定 ≤512 字节缓冲且用于 b64 编码」为 `E-contract`。
- 不强制检测间接宏定义（如 `#define TOF_BUF_SIZE 256`），那应由真实 build 暴露。

### S4. Capstone 默认不进 V4.0，但写入触发条件

当前 `CAPSTONE_ITEM_IDEAS.md` 建议 V4.0 先不加。为了把条件固定下来，建议在 `00_DESIGN_BRIEF.md` 的 G1 中加入：

> 若 V4.0 校准跑完成后 ≥3 个模型 Ability ≥96，则 V4.1 必须从候选池选入 1 个 capstone（8 分独立 family），否则顶部再次拥挤。

---

## 同意的亮点

1. **V2 作为唯一基底是正确的**。V1 测的是不同维度，V3.1 的题虽好但评分失败，都不能替代 V2 的工程壳。
2. **Ship/Ability 双轨是核心洞见**。这与 soft-cap 实验榜完全吻合：同样 82 的模型下面藏着 81.2–88.0 的能力差异。
3. **F3/F12 拆分解决了 V2 最不公平的场景**：已正确拒绝且零泄漏，只因 reason 字符串不合枚举就被当成安全失败。
4. **F8/F9 分家防止 static marker 工程师刷分**。Mimo Flash 和 Minimax M2.5 的案例说明 static 满分不等于构建可信。
5. **item bank 的 behavior oracle + allowed_equivalents** 是反出题偏置的有效纪律。
6. **信任类 hard cap 保留得当**：public 失败、改测试、构建造假、严重 overclaim 仍然需要重罚。
7. **score_draft_confidence + unscored_items** 把自动推断和人工确认的边界显式化。
8. **门槛聚集审计**（06 §2.11）直接针对 V3.1 的病因，应在冻结前强制执行。

---

## 对开放争议点的投票

| 争议 | 选择 | 理由 |
|------|------|------|
| F3e Ship 顶 89 / 取消 / 改值 | **取消数值顶，仅 Class B+** | 避免把 82 墙换成 89 墙；Ability 已能拉开差距 |
| 主榜排序 Ship 优先 vs Ability 优先 | **Ability 降序为主榜** | 评测目标是工程完成度，Ship/Class 作发布参考 |
| 无 IDF 时 F9 给 2–3 分是否公平 | **固定 3 分，显式 `build_skipped`** | 环境差异不应吃掉 4 分，也不应白送满分 |
| sketch_jan22a 保留 vs 移除 | **保留** | 真实仓库噪声；顶部模型不依赖它，中等模型可获线索 |
| 重复 CSV 幂等是否纳入 V4.0 | **不纳入** | V4.0 题库已够大，幂等适合 V4.1 |
| 是否加入高耦合 capstone | **V4.0 不加；校准后顶部 ≥3 人 Ability≥96 则 V4.1 必加** | 当前目标是修复评分结构，不是一次性扩题 |
| Ability 是否允许人工 ±2 | **允许，强制写理由** | 自动证据不能替代架构/报告审查 |
| F12=4 是否合理 | **合理** | 让 reason-perfect 的模型在 96 分段有小优势，但不决定中游排名 |

---

## 风险与可实施性

### 高风险

1. **评分实现漂移**。如果 `score_model.py` 或 reviewer_prompt 又把 Ship gate 当主排序器，V4 会复刻 V3.1。缓解：在 reviewer_prompt 中硬编码「默认按 Ability 排序；Ship 仅作发布参考」并设自检问题。
2. **双视图在对外传播中坍缩为单数**。如果只对外说「GLM-5.2 V4 得分 89」，而 89 是 Ship（Ability=95），就会丢失设计意图。缓解：官方报告模板 Ability 列在 Ship 左侧且加粗。

### 中风险

3. **F8 static 检查器改写**。当前 V2 的 `test_espidf_static_contract.py` 是关键词匹配，需要按 `allowed_equivalents` 重写，工程量大且容易过宽/过紧。
4. **F4 voice bridge hidden 测试误杀等价实现**。如果模型直接查本地 DB 而非走 `/api/v3/context/chat`，应视为等价正确。

### 低风险

5. **PR-A..PR-E 切分合理**。PR-A（评分管线）必须先落地，然后用旧 V2 seed 跑一次确认 score_draft 与人工差 <5 分再继续。
6. **V2 relabel 的 ±3 误差带诚实**，只要每行标 `[RELABEL, NOT RERUN]`。

---

## 检查清单逐项

### A. 目标一致性

| # | 检查项 | P/F/U |
|---|--------|-------|
| A1 | V4 是否清楚以 V2 为基底而非 V3.1 树？ | **P** |
| A2 | 是否明确解决 82 墙，而非用新 cap 换墙？ | **P**（双轨解决；但 F3e Ship≤89 有残余风险，见 B1） |
| A3 | 是否保留信任类重罚？ | **P** |
| A4 | 非目标是否足够（无硬件、不混 V1 分）？ | **P** |
| A5 | 成功标准是否可判定？ | **P** |

### B. 评分体系

| # | 检查项 | P/F/U |
|---|--------|-------|
| B1 | F1–F12 加总是否为 100？ | **P** (8+12+16+4+12+10+8+8+6+8+4+4=100) |
| B2 | 仅 ambient 失败时，是否仍能在 Ability 上区分不同完成度模型？ | **P** |
| B3 | F3e Ship≤89 是否可接受？ | **F** — 建议取消数值天花板 |
| B4 | F12=4 是否合理？ | **P** |
| B5 | Hard cap 列表是否过宽/过窄？ | **P** |
| B6 | Release Class 是否与分数重复或互补清晰？ | **P** |
| B7 | 渠道强制列是否足够抑制工具噪声误解？ | **P** |
| B8 | 自动草稿 + 人工终裁职责是否清楚？ | **P** |
| B9 | 是否强制同时展示 Release view 与 Ability view？ | **P**（建议补充默认 Ability 优先，见 B2） |
| B10 | reason-only 是否只进 F12 / semantic_only？ | **P** |

### C. 题库

| # | 检查项 | P/F/U |
|---|--------|-------|
| C1 | 是否 ≥12 个低耦合中等权重点？ | **P** |
| C2 | 每条高分值题是否行为 oracle 而非命名 cop？ | **P** |
| C3 | F3 与 F12 拆分是否避免「拒绝了仍当安全失败」？ | **P** |
| C4 | F4 voice 是否会诱导恢复 ambient？ | **P**（probe warning-only + 禁止恢复 ambient） |
| C5 | F6 多台阶是否可自动测？ | **P** |
| C6 | F7 混合 CSV 是否真实且可测？ | **P** |
| C7 | F8/F9 分家是否降低 static 刷分？ | **P** |
| C8 | 是否存在仍严重 GPT 口味的题？ | **U** — F12 reason 枚举仍有软偏置，但 4 分权重够低 |
| C9 | 题量是否导致评测过贵/过慢？ | **P** |
| C10 | 是否应从 capstone 选 1-2 题进 V4.0？ | **P**（推迟到 V4.1） |
| C11 | capstone 若加入能否避免连坐？ | **P** |

### D. Seed / 提示

| # | 检查项 | P/F/U |
|---|--------|-------|
| D1 | public 绿 + hidden 红的 broken 标准是否成立？ | **P** |
| D2 | 脏库策略是否避免 public 必红？ | **P** |
| D3 | ONBOARDING 去剧透是否足够？ | **P** |
| D4 | probe warning 是否泄漏过多解法？ | **P** |
| D5 | 保留 PR 模板 vs answer.md 是否合理？ | **P** |

### E. 流水线

| # | 检查项 | P/F/U |
|---|--------|-------|
| E1 | artifact 列表是否完整可复盘？ | **P** |
| E2 | blockers/score_draft 契约是否可实现？ | **P** |
| E3 | build skipped 是否被防白送分？ | **P** |
| E4 | 实施切分 PR-A..D 是否合理？ | **P** |
| E5 | score_draft_confidence / unscored_items 是否足以区分正式 V4 run 与历史 relabel？ | **P** |

### F. 反偏置与历史

| # | 检查项 | P/F/U |
|---|--------|-------|
| F1 | 十条纪律是否可执行？ | **P** |
| F2 | 跨模型试跑门禁是否必要/过重？ | **P** |
| F3 | 重标注误差带 ±3 是否诚实？ | **P** |
| F4 | 附录示例是否显示 82 团被拉开？ | **P** |
| F5 | 冻结前是否要求门槛聚集审计？ | **P** |

---

## Blocking 项总结

| # | 项 | 优先级 |
|---|-----|--------|
| B1 | 取消 F3e 的 Ship 数值天花板（仅保留 Class B+） | **高** |
| B2 | 默认榜单视图明确为 Ability 降序 | **高** |
| B3 | F1 不引入 git 时间戳自动扣分 | **中** |

以上 B1/B2 解决后，V4 设计可以进入实施阶段。

---

*审核模型: Kimi K2.7 Code | 渠道: Opencode/API | 日期: 2026-07-11*
