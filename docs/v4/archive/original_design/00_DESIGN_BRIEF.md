# V4 设计简报（Design Brief）

## 1. 要解决什么

在 **不推翻真实工程壳** 的前提下，解决：

1. **V2 的 82 分墙**：敏感 context ambient fallback 一刀切，十余模型挤同一分。  
2. **V3.1 总分榜失败**：阶梯 hard cap 再次把大多数模型压到 82–84。  
3. **单分数讲三个故事**：代码质量 / 过程诚实 / 效率混在一个整数里。  
4. **reason-code 过重**：语义字符串错误与数据泄漏同级对待。  
5. **渠道噪声**：模型本体与工具链未分列。  
6. **ESP static 刷分 vs 真实 build 证据不足**。  
7. **出题偏置疑虑**：GPT 参与出题时，契约措辞与过程叙事可能对同类模型更友好。

## 2. V4 一句话

**以 V2 为基底大动评分与题库；题考行为不变量；分用 Ship + Ability 双轨；阻断标签表达发布风险；hard cap 只打信任崩坏。**

## 3. 目标（Goals）

| ID | 目标 |
|----|------|
| G1 | 原 82 团在 Ability 上能自然摊到约 80–92 区间，且可解释；若 V4.0 校准后 ≥3 个模型 Ability≥96 **或** top3 Ability 极差<2，则 V4.1 引入 1 个 capstone 防止顶部拥挤（MiniMax-M3 增补极差条件，防 2 人 96+ 但顶部仍拥挤） |
| G2 | Ship 仍能表达「能不能收」；隐私/迁移问题有阻断，但不抹平其余工程量 |
| G3 | 题库 ≥12 个互不耦合的中等权重考点（2–5 分级） |
| G4 | reason-code 最多影响 4 分，不能单独决定头部名次 |
| G5 | 榜单强制展示 Channel；承认端到端分数定义 |
| G6 | 实施成本可控：V2 seed 手术式增强，不整仓重写 |
| G7 | 历史 V2 结果可重标注，不必全量重跑 |
| G8 | **默认主榜硬约束**：官方主榜按 Ability 降序排序，Ship/Class 作为并列信息列；Release view（按 Ship/Class 筛选/排序）为按需生成的第二视图。**不得在主榜把 Ship 当排序器**（MiniMax-M3 增补；与 DeepSeek S1 / Kimi B2 收敛） |

## 4. 非目标（Non-goals）

- 测真实板级 Wi-Fi/MQTT/烧录/摄像头精度  
- 测「纯模型智商」而忽略 harness（V4 明确拒绝这种定义）  
- 用弱提示 V1 作为默认主榜  
- 以 V3.1 目录树为实施基底  
- 用更多 hard cap 制造「看起来很严」的假区分度  
- 本设计阶段改代码或重跑模型  

## 5. 三轨定位

| 轨道 | 状态 | 用途 |
|------|------|------|
| **V4 Main** | 设计中 → 未来默认 | 新模型主榜 |
| **V1 Optional** | 已归档 | 弱提示主动性；分数不与 V4 硬比 |
| **V3.1 Archive** | 已归档 | 题源与教训；不再做主榜 |

## 6. 成功标准（给审核方）

设计通过交叉审核，当且仅当审核方同意：

1. 仅漏 ambient fallback 时，**不可能**再出现十余模型 Ship/Ability 被压成同一整数。  
2. public 失败 / 改测试 / 编译造假 仍会在 Ship 上被重罚。  
3. 题库条目均可自动化或半自动 oracle，且允许多种正确实现。  
4. 不要求硬件即可完成 full eval 主路径。  
5. 与 V2 叙事可通过附录重标注对照。  
6. （MiniMax-M3 增补）F3/F12 拆分在 hidden test 层面真实落地——已正确拒绝且零泄漏但 reason 错的样本，relabel 后 F3 对应子项得分、只扣 F12，不得升级为 S-* behavior blocker。  
7. （MiniMax-M3 增补）`reference/api_contracts.md` 第 49 行去剧透后，V2 历史样本中过 F3e 的（GLM-5.2/Doubao/Grok-4.5）仍过、漏 F3e 的（Kimi K2.7/LongCat/Composer）继续漏。  
8. （MiniMax-M3 增补）F8-07 static 改写后，V2 已知样本（Grok-4.5 8/8、DeepSeek Pro 5/8、LongCat 5/8）分值不变突变 ±1。  

## 7. 默认决策（可被审核推翻）

详见各章；摘要如下：

| 议题 | 默认 |
|------|------|
| 报告文件 | 保留 `PULL_REQUEST_TEMPLATE.md` |
| 分数 | Ability = family 加总；Ship = Ability + 信任类 hard cap + Release Class |
| 主榜排序 | **Ability 降序**（G8 硬约束）；Ship/Class 并列；Release view 为第二视图 |
| 脏库 | seed 内旧 schema 样例 + 测试用 temp；public 默认干净 temp DB；脏库放 `data/legacy_sample.db`（非默认 DB 路径） |
| ESP build | 检测到工具链则默认跑；否则 `build_skipped` 固定 3 分（F9 满分 6），不得白送满分 |
| 主渠道 | 实验室自声明；同 model + 不同 channel/harness 分行（详见 `05 §4.1` 端到端定义边界） |
| 弱提示 | 不进 V4 主流程 |
| F3e Ship 数值顶 | **取消**；仅 Class B+ 标记，Ability 上扣 F3e 的 5 分已能拉开差距 |
| F1 时序验证 | **不引入** git 时间戳自动扣分；时序异常仅作 `score_draft_confidence.json` notes 或人工 review 提示 |
| F4 拆分 | 拆为 F4a 识别 1 分 + F4b 正确修复 3 分 |
| F9 无工具链 | 固定 3 分，标 `f9_mode: "skipped_env"`；不分母缩放（避免 95/100 vs 95/94 口径混乱） |
| F8-07 uncertain | static 解析不出时记 `f8_07_status: "uncertain"`，由人工 final 判；不得自动记过/自动扣分 |

## 8. 文档地图

见 [README.md](./README.md)。实施前必读争议面：`02`、`03`、`08`。
