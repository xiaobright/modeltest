# DeepSeek V4 交叉审核意见

## 总裁决

**有条件同意。**

V4 的核心方向正确：以 V2 真实工程壳为基底、用 Ship/Ability 双轨 + 阻断标签替代 hard cap 主导排序、reason-code 降权到 F12、ESP static 与 real build 分家。这些改动精确对应 V2/V3.1 的已验证失败模式。以下 blocking 项解决后可进入实施。

---

## 必须修改（blocking）

### B1. F3e Ship≤89 门槛具备「新墙」风险 → 改为 91 或 Class-only

当前设计：F3e（ambient fallback）失败 → Ship ≤ 89。

问题：V2 原 82 团中至少有 6-7 个模型都带 `S-ambient`。在 V4 下，这批模型的 Ship 将全部 ≤89。即便 Ability 从 83 摊到 88，Ship 列仍会显示一排 88-89。虽然设计写明「同 gate 内按 Ability 排序 + 强制双视图」，但：

- **榜单向传播时天然倾向只看一个数**。如果那个数是 Ship，89 墙就取代了 82 墙；
- 89 的语义边界（「可发布」vs「不可发布」）本身合理，但数值 89 vs 88 vs 87 的差异不可解释——为什么 ambient 失败扣到 89 而不是 88 或 90？

**建议**：

- **方案 A（推荐）**：F3e 仅保留 **Class 标记**（B+），不设 Ship 数值天花板。Class 已经表达了「不可 A 类发布」。用 Ability 做主排序时，S-ambient 模型自然因扣 F3e 的 5 分而被拉开（Ability 差约 5 分）。
- **方案 B**：若坚持保留数值天花板，至少提到 **91**。理由：91 离满分 100 差 9 分，与 F3e 的 5 分 + F4 可能缺失的 4 分加和一致，不会造成「明明只漏一个 ambient 却被压到和漏 ambient+migration 一个档次」的感知。

```diff
- | 过 F3a/b 但未过 F3e | min(ship, **89**) |
+ | 过 F3a/b 但未过 F3e | 不设 Ship 数值天花板；仅 Class B+ |
```

若采纳方案 A，附录中 Ship 列对应的 89 值也应同步调整。

### B2. F9 无工具链时的保底分需要校准

当前：工具链不可用时「诚实写 skip + 环境限制」→ 2–3 分。

问题：F9 满分 6 分。无 ESP-IDF 环境的实验室在 F9 上直接损失 3–4 分——这是 100 分 Ability 中的 3–4%，对 80-95 段的排序影响不可忽略。而「有没有装 IDF」与模型能力无关。

**建议**：将「诚实 skip」档的下限提高到 **3 分**，并明确当 `build_skipped=true` 时：

- F9 不计入 Ability（分母缩小到 94），或
- F9 统一给固定补偿 3 分（=满分的一半），以中性化环境差异

选择一种并在 `score_draft.json` 中显式标注 `f9_mode: "skipped_env" | "ran"`。

### B3. PR 过程事实一致性检查需要防时序造假

当前 F1-01/02 检查 PR 中「是否记录了初/终诊断」，但只做内容匹配，不做时序验证。

问题：模型可以先完成所有修复，再在 PR 中**倒填**「初始失败摘要」——这无法被当前 F1 oracle 检测。而 git 时间戳天然提供时序信息。

**建议**：在 F1 的 oracle 中加入：

- `git log` 的首次有效 commit 时间 ≤ 首次 public test 运行时间（可从 public.log 时间戳推断）——若不满足，F1 自动扣 2 分并触发 `P-report`
- 不需要 100% 精确匹配，允许 ±5 分钟误差，只抓「先修完再补写初始诊断」的明显造假

实施上，`score_model.py` 对比 candidate_log.txt 的首 commit 时间和 public.log/debug_probe.log 的文件修改时间即可。

---

## 建议修改（non-blocking）

### S1. 默认榜单视图应为 Ability 优先，Ship 为辅

当前设计说「Release view + Ability view 双视图」，但未明确**默认展示哪个为主排序**。对于「评测模型工程能力」这个核心目标，Ability 比 Ship 更直接。

**建议**：

```text
默认榜单:
Rank | Model | Channel | Ability | Ship | Class | Blockers | ...
```

即 Ability 降序排列，Ship 和 Class 作为并列信息列。Release view（Ship 降序 + Class 筛选）作为**按需生成的第二视图**，用于回答「能不能合入主线」。

### S2. F4 voice bridge 评分应增加「部分完成」的中位档

当前 F4 只有 1 个 item，4 分，全有或全无。但实际可能出现：

- 模型修了 context 但完全没有注意到 voice 断裂 → 0 分
- 模型意识到了问题但在 voice 侧做了错误修复（如恢复 ambient）→ 0 分且可能扣 F3
- 模型在 PR 中提到 voice 风险但未实现修复 → 当前没有对应分值

**建议**：拆成两个子项：

| 子项 | 分 | Oracle |
|------|---:|--------|
| F4a 识别问题 | 1 | PR 或 answer 中提到 voice/RK3588 可能因 context 收紧而受影响 |
| F4b 正确修复 | 3 | 实际代码中 voice 路径在请求敏感 context 前获取显式 session |

这样即使模型没时间修完，只要识别了风险就能拿 1 分。

### S3. 题库中「F8-07 载荷缓冲」的 static 检查可能过度依赖代码模式匹配

当前 oracle：「不得用固定过小缓冲（如 256）承载完整 ToF base64 JSON；static 可检」。

风险：static 检查器可能只检测 `char buf[256]` 这类字面量，但模型可以：

- 用 `char buf[TOF_BUF_SIZE]` + 远端 `#define TOF_BUF_SIZE 256` → static 漏检
- 用 `std::string` / `std::vector<char>` → static 可能误报

**建议**：在 `allowed_equivalents` 中明确：
- 动态分配（malloc/new/std::string/std::vector）视为等价正确
- static 只标记「固定≤512 字节缓冲且用于 b64 编码」为 `E-contract`
- 不强制检测所有可能的 indirect 小缓冲（那需要真实 build）

### S4. Capstone 高耦合上限题的引入时机

当前设计将 capstone 推迟到 V4.1。考虑到 V4.0 的题库已有 40+ 项、F1-F12 覆盖全面，这个决策正确。

但有一个风险：**V4.0 把所有 V2 82 团拉开后，可能在 95-97 段形成新的顶部拥挤**（GPT-5.5、Grok-4.5、GLM-5.2 API 都接近满分）。建议：

- V4.0 校准跑完成后，若 ≥3 个模型 Ability ≥ 96，则 **V4.1 必须从 `CAPSTONE_ITEM_IDEAS.md` 选入 1 个 capstone**（8 分，独立 family F13），否则顶部失去区分度
- 把这个条件写入 `00_DESIGN_BRIEF.md` 的 G1 目标

### S5. Reviewer prompt 中应加入「常犯错误速查表」

V2/V3.1 中反复出现的人工评审偏差：

| 错误模式 | 预防 |
|----------|------|
| 把 reason 错当成安全失败 | reviewer_prompt 显式列出「仅扣 F12」的条件 |
| 把 static marker 缺失当成「ESP 没做」 | 区分 F8（协议）和 F9（构建） |
| 把 PR 写得不好当成「代码能力差」 | 明确 F1 与 F2-F11 独立 |
| 用「看起来不像参考实现」扣分 | 写入禁止条款 |

**建议**：在 `evaluator/scoring/reviewer_prompt.md` V4 版中加入一节「Hall of Shame: Common Review Errors」，列出上述反例。

---

## 同意的亮点

1. **V2 作为基底是唯一正确选择**。V1 太弱提示（测不同维度），V3.1 被 cap 绑架。V2 的工程壳、debug workflow、visible/hidden 分离已经过 24+ 模型验证，是最稳定的基线。

2. **Ship/Ability 双轨是本设计的核心洞见**。V2 soft-cap 实验榜已经证明：同样的「82 分」下面藏着 81.2 到 88.0 的巨大差距。双轨把「能不能发布」和「做了多少工程」解耦，是对 V2 问题的精确回答。

3. **Reason-code → F12 降权（4 分）** 解决了 V2 中最不公平的扣分场景：模型正确拒绝了请求、零数据泄漏，只因 error message 字符串不是契约期望的枚举值就被扣到和「未认证泄漏」同级。

4. **ESP static (F8) 与 real build (F9) 分家** 防止「static 8/8 但 build 失败」被伪装成满分。Composer 2.5 和 Mimo Flash 的 V2 案例已证明这个区分的必要。

5. **行为 oracle + allowed_equivalents** 是反出题偏置的正确方法。把评分从「像不像 GPT 的写法」拉回到「输入→输出对不对」。

6. **信任类 hard cap 保留得当**。public 崩、改测试、构建造假、报告欺诈——这些在任何评测框架下都应重罚。V4 没有为了「去除 cap」而走极端。

7. **Item bank 的 12+ 低耦合中等权重点**（F3a/b/e, F4, F6a/c, F7-07/08, F8-07, F9, F2-03）有效避免了 V1 中 auth 连坐的失败模式。

8. **`score_draft_confidence.json` + `unscored_items`** 机制把「自动推断」和「人工确认」的边界显式化，防止 V2 中「re-label 被当成正式成绩」的混乱。

9. **门槛聚集审计**（06 §2.11）直接治疗 V3.1 的病因——cap 变成排序器。这个预防机制应该在上线前强制执行。

---

## 对开放争议点的投票

| 争议 | 选择 | 理由 |
|------|------|------|
| F3e Ship 顶 89 / 取消 / 改值 | **取消数值顶，仅 Class B+** | 见 B1。Class 已表达发布风险，数值天花板只会制造新墙。Ability 上 F3e 扣 5 分已经足够拉开差距 |
| 主榜排序 Ship 优先 vs Ability 优先 | **Ability 降序为主榜，Ship+Class 为辅助列** | 见 S1。测的是工程能力，不是发布审批 |
| 无 IDF 时 F9 给 2–3 分是否公平 | **默认 3 分，且建议分母缩小到 94** | 见 B2。环境差异不应吃掉 4 分 |
| sketch_jan22a 保留 vs 移除 | **暂保留** | 真实仓库噪声有价值；topic 构造线索对中等模型有帮助，但对顶部模型不影响 |
| 重复 CSV 幂等是否纳入 V4.0 | **不纳入** | V4.0 题库已够大；幂等适合 V4.1 |
| 是否加入高耦合 capstone | **V4.0 先不加；校准后若顶部拥挤 ≥3 人则 V4.1 必加** | 见 S4 |
| Ability 是否允许人工 ±2 | **允许，强制写理由** | 自动证据无法替代架构/报告审查；但理由必须具体（不能写「感觉不对」） |
| F12=4 是否合理 | **合理** | 4 分足够让 reason-perfect 的模型在 96 分段获得小幅优势，但不足以决定中游排名 |

---

## 风险与可实施性

### 高风险

1. **评分实现漂移**（继承 V3.1 的失败模式）。如果 `score_model.py` 或 reviewer_prompt 在实际使用中又把 cap 当主排序器——比如 reviewer 习惯只看 Ship 列的 89 就说「又是一批 89 分」——那 V4 的所有改进都会被浪费。缓解：reviewer_prompt 中硬编码「必读 Ability + family breakdown；Ship 仅作发布参考」并设自检问题。

2. **双视图在对外传播中坍缩为单数**。如果对外只说「GLM-5.2 V4 得分 89」，而 89 恰好是 Ship（不是 Ability=95），就完全丢失了设计意图。缓解：官方报告模板中 Ability 列必须在 Ship 左侧且用粗体。

### 中风险

3. **F8 static 检查器的 v4 改写**。当前 V2 的 `test_espidf_static_contract.py` 有死板的关键词匹配。需要按照 item bank 中的 `allowed_equivalents` 重写——这个工程量不小，且容易过度放宽（让刷分变容易）或过度收紧（误杀合理实现）。

4. **F4 voice bridge 的 hidden 测试可能误杀真实修复**。如果模型的 voice 助手用了不同的 API 路径（如直接查 DB 而非走 `/api/v3/context/chat`），F4 hidden 测试会失败，但实际上模型做了正确的事（本地 DB 查询不需要 session）。需要在测试中允许等价实现路径。

### 低风险

5. **实施 PR 切分（PR-A 到 PR-E）合理**。最大的依赖是 PR-A（评分管线）必须先落地，PR-B/C 可以在 PR-A 的框架上并行开发。建议 PR-A 完成后先用 V2 的 broken seed 跑一次，确认 score_draft 与人工分差值 < 5 分再继续。

6. **V2 ↔ V4 历史重标注的 ±3 误差带可接受**，只要不宣传为「官方 V4 成绩」。建议在 relabel 文档中**每一行都标水印 `[RELABEL, NOT RERUN]`**。

---

## 检查清单逐项

### A. 目标一致性

| # | 检查项 | P/F/U |
|---|--------|-------|
| A1 | V4 是否清楚以 V2 为基底而非 V3.1 树？ | **P** |
| A2 | 是否明确解决 82 墙，而非用新 cap 换墙？ | **P**（双视图 + Ability 主序解决；F3e Ship≤89 有残余风险，见 B1） |
| A3 | 是否保留信任类重罚？ | **P** |
| A4 | 非目标是否足够（无硬件、不混 V1 分）？ | **P** |
| A5 | 成功标准是否可判定？ | **P**（附录示例给出具体可验证场景） |

### B. 评分体系

| # | 检查项 | P/F/U |
|---|--------|-------|
| B1 | F1–F12 加总是否为 100？ | **P** (8+12+16+4+12+10+8+8+6+8+4+4=100) |
| B2 | 仅 ambient 失败时，是否仍能在 Ability 上区分不同完成度模型？ | **P**（F3e 扣 5 分 + F4 扣 0-4 分 + 其他 family 差异 ≥5 分区间） |
| B3 | F3e Ship≤89 是否可接受？ | **F** — 见 B1，建议取消数值天花板仅保留 Class |
| B4 | F12=4 是否合理？ | **P** |
| B5 | Hard cap 列表是否过宽/过窄？ | **P**（信任崩坏场景覆盖完整，不含 S-ambient/M-fidelity/reason） |
| B6 | Release Class 是否与分数重复或互补清晰？ | **P**（Class 表达发布风险维度，Ship/Ability 表达数值，互补不重叠） |
| B7 | 渠道强制列是否足够抑制工具噪声误解？ | **P** |
| B8 | 自动草稿 + 人工终裁职责是否清楚？ | **P** |
| B9 | 是否强制同时展示 Release view 与 Ability view，避免 Ship gate 形成新墙？ | **P**（设计已含，建议补充默认 Ability 优先，见 S1） |
| B10 | reason-only 是否只进 F12 / semantic_only，不升级成 S-*？ | **P**（`blockers.json` 的 `semantic_only` 字段解决） |

### C. 题库

| # | 检查项 | P/F/U |
|---|--------|-------|
| C1 | 是否 ≥12 个低耦合中等权重点？ | **P**（12+ 明确列出） |
| C2 | 每条高分值题是否行为 oracle 而非命名 cop？ | **P**（规格有 `allowed_equivalents` 字段） |
| C3 | F3 与 F12 拆分是否避免「拒绝了仍当安全失败」？ | **P**（核心改进点） |
| C4 | F4 voice 是否会诱导恢复 ambient？ | **P**（probe warning-only + block forbidden 路径） |
| C5 | F6 多台阶是否可自动测？ | **P**（每台阶有明确 SQL/HTTP oracle） |
| C6 | F7 混合 CSV 是否真实且可测？ | **P** |
| C7 | F8/F9 分家是否降低 static 刷分？ | **P** |
| C8 | 是否存在仍严重 GPT 口味的题？ | **U** — F12 的 reason 枚举可能对强 instruction-following 模型更友好；但 4 分权重够低 |
| C9 | 题量是否导致评测过贵/过慢？ | **P**（hidden 测试可在 30s 内跑完） |
| C10 | 是否应从 capstone 选 1-2 题进 V4.0？ | **P**（推迟到 V4.1，先看校准结果） |
| C11 | capstone 若加入能否避免连坐？ | **P**（设计写明独立 family 不连坐） |

### D. Seed / 提示

| # | 检查项 | P/F/U |
|---|--------|-------|
| D1 | public 绿 + hidden 红的 broken 标准是否成立？ | **P**（与 V2 一致） |
| D2 | 脏库策略是否避免 public 必红？ | **P**（public 默认 TEMP 干净 DB） |
| D3 | ONBOARDING 去剧透是否足够？ | **P**（症状级文案，不写根因） |
| D4 | probe warning 是否泄漏过多解法？ | **P**（只给方向，保留推理空间） |
| D5 | 保留 PR 模板 vs answer.md 是否合理？ | **P**（兼容 V2 语料，减少无谓迁移） |

### E. 流水线

| # | 检查项 | P/F/U |
|---|--------|-------|
| E1 | artifact 列表是否完整可复盘？ | **P** |
| E2 | blockers/score_draft 契约是否可实现？ | **P** |
| E3 | build skipped 是否被防白送分？ | **P**（设计明确说不给满分） |
| E4 | 实施切分 PR-A..D 是否合理？ | **P** |
| E5 | score_draft_confidence / unscored_items 是否足以区分正式 V4 run 与历史 relabel？ | **P** |

### F. 反偏置与历史

| # | 检查项 | P/F/U |
|---|--------|-------|
| F1 | 十条纪律是否可执行？ | **P**（具体、可检查） |
| F2 | 跨模型试跑门禁是否必要/过重？ | **P**（必要但不过重；只需 1 个非出题模型） |
| F3 | 重标注误差带 ±3 是否诚实？ | **P** |
| F4 | 附录示例是否显示 82 团被拉开？ | **P**（Kimi K2.7 88 vs Composer 83 差距明确） |
| F5 | 冻结前是否要求门槛聚集审计？ | **P**（已写入 06 §2.11 和 07 §7） |

---

## Blocking 项总结

| # | 项 | 优先级 |
|---|-----|--------|
| B1 | 取消 F3e 的 Ship 数值天花板（仅保留 Class B+） | **高** |
| B2 | F9 无工具链保底分校准（3 分 + 分母缩小选项） | **中** |
| B3 | F1 过程事实一致性增加时序验证 | **中** |

以上三项解决后，V4 设计可以进入实施阶段。

---

*审核模型: DeepSeek V4 Pro | 日期: 2026-07-11*
