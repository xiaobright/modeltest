# V4 问题诊断：V1 / V2 / V3.1 复盘与需求推导

## 1. 三版各自测到了什么

| 版本 | 提示形态 | 测到的能力 | 结构性失败 |
|------|----------|------------|------------|
| **V1** | 弱提示 | 主动读项目、主动找安全边界 | 中游 48–55 拥挤；auth 根因连坐过多 |
| **V2** | 强约束 + 可见 probe + 必做 ESP | 真实 debug 闭环与收口 | **80/82 墙**；单点 privacy cap；渠道噪声 |
| **V3.1** | 更细 context/security + 阶梯 cap | 安全专项有效 | **总分榜失败**；多数卡在 82–84 |

阶段性结论（归档已有，V4 继承）：

- 只测一个新模型时，**V2 最均衡**。  
- V3.1 **题不差，榜差**。  
- V1 仍有价值，但是 **另一维度**，不能和 V2/V4 硬比。

## 2. V2 的优点（V4 必须保留）

1. **workspace / evaluator 边界清晰**——候选不可见 hidden / scoring。  
2. **public smoke 可过的 broken seed**——不是「跑不起来的坏种子」。  
3. **debug probe 给现象**——接近真实 bug report，而非纯谜题。  
4. **family 证据 + 人工 rubric**——不唯 hidden 数。  
5. **ESP 必做**——拉开「只会修 Python」与「全栈收口」。  
6. **PR 事实一致性**——抓 overclaim（Minimax M2.5 类反例）。  
7. **git tag 基线 diff**——候选 commit 无法藏改动。  
8. **evaluator-owned public/probe 副本**——防改测试刷分。

## 3. V2 的结构性缺陷

### 3.1 82 墙（最高优先级）

典型路径：

```text
public ✓ → probe ✓ → admin/auth ✓ → sleep ✓ → care_event 大部分 ✓
→ ESP 至少 static 部分 ✓
→ sensitive targeted context 仍 ambient fallback
→ 正式分硬顶 82
```

后果：

- GLM-5.1 / Mimo Pro / DeepSeek Flash / Kimi K2.7 / LongCat / Composer / Minimax… **工程完成度明显不同，分数字面相同**。  
- soft-cap 实验榜已证明：若去掉该硬顶，同批可摊到约 **83–88**。  
- 早期「只有 GPT 破 82」容易被误读为 **出题偏袒**；实质是 **钥匙太少 + cap 太狠**。

### 3.2 reason-code 与真泄漏同级

例：`session_without_actor_subject` 期望 `not_authorized_for_target`，模型写 `not_authenticated` 且 **已拒绝、未泄漏**。  

- 对发布风险：低  
- 对 V2 hidden：常计失败  
- 对顶部：GPT-5.5 / Grok-4.5 仅剩此类问题时仍 96，尚可；但对中游叙事混乱  

V4：**行为拒绝 + 零泄漏为主证；reason 语义降为 F12（4 分）**。

### 3.3 单一总分混维

一个 82 可能是：

- 代码强、隐私门没关；或  
- 过程好、迁移崩；或  
- ESP 强、context 弱  

读者无法从整数区分。V4 用 **Ability + Ship + Blockers + 维度剖面**。

### 3.4 ESP static ≠ 可构建

- static 8/8 仍可能真实 build 失败（依赖解析、C++ 事件 ID 等）。  
- build 多依赖人工确认，未统一进 summary。  
- 关键词实现可抬高 static。  

V4：F8 static 与 F9 build **分家**；造假走信任 cap。

### 3.5 渠道 / 工具方差

同模型：

- GLM-5.2：API 95 / 火山 89 / WorkBuddy 88  
- Kimi K2.6：Qoder 80 vs WorkBuddy 78（且成本形态不同）  
- Qoder 压缩失忆 vs Codex 稳定  

V4：**分数定义含 harness；榜单强制 Channel 列**。

### 3.6 中游已会显性任务

再堆「明显 TODO」边际收益低。拉开中上靠：

- 迁移保真多台阶  
- context 分层小分  
- 跨模块 voice bridge  
- 混合 CSV 行级  
- 报告/构建诚实  

## 4. V3.1 的优点与失败模式

### 优点（迁入 V4 题库）

| 想法 | V4 处理 |
|------|---------|
| context 分层（根本 / session / ambient / 集成） | 进 **F3 内部分项**，不当 hard cap 阶梯 |
| mixed CSV 行级 | F7 新项 |
| voice 先取 session | F4 独立 4 分 |
| 物理脏库 | seed + F6 |
| duration/churn | meta 与效率剖面 |
| answer.md 统一报告 | **不采用更名**；强化 PR 模板结构（兼容 V2 语料） |

### 失败模式（V4 明确禁止）

1. **用 cap 当主排序器**：Tier1=78, Tier2=84, Tier3=88, 集成=92 → 强模型全贴在 84 附近。  
2. **多层 cap 取最低** 在实践中几乎总触发同一层 → 区分度假象。  
3. **安全专项题面 + 总分榜目标** 混用 → 榜面「又严又挤」。  

V4 原则：

> **Hard cap 只服务信任与「绝对不可发布」的少数情况；区分度靠独立小分与 Ability。**

## 5. 「是不是 GPT 出题导致只有 GPT 高分？」

### 不完全是

- 后续 GLM-5.2 / Grok-4.5 可到 95–96 → 非 GPT 锁死。  
- 卡住点多是真实隐私/迁移/构建问题。  
- Doubao 早期已到 86 → 非「只有 GPT 懂题」。  

### 部分是（软偏置）

- 精确 reason 枚举、PR 叙事、契约驱动补全、static marker——对强 instruction-following + 强 agent 更友好。  
- 单点 cap 放大「谁先收口」的时间差。  

V4 用 **行为 oracle + 多等价实现 + reason 降权 + 反偏置出题纪律** 对冲（见 `06`）。

## 6. V4 需求列表（Requirements）

| ID | 需求 | 来源 |
|----|------|------|
| R1 | 双轨 Ship / Ability | V2 82 墙、soft-cap 实验 |
| R2 | 阻断码机器可读 | soft-cap、人工 review 成本 |
| R3 | context 分项计分，禁止单点 82 硬顶 | V2/V3.1 |
| R4 | migration 多台阶独立分 | GPT-5.5 vs 5.4、82 团内部差 |
| R5 | voice bridge 独立项 | V3.1 |
| R6 | mixed sleep CSV | V3.1 |
| R7 | ESP static / build 分家 | V2 报告 3.4 |
| R8 | 信任类 hard cap 保留 | M2.5 反例 |
| R9 | Channel 强制 | 工具噪声 |
| R10 | 行为 oracle 优先 | 反出题偏置 |
| R11 | V2 seed 手术增强 | 实施成本 |
| R12 | 历史可重标注 | 语料资产保护 |
| R13 | 默认强流程提示，弱提示另轨 | V1/V2 能力维度不同 |

## 7. 明确不继承的东西

- V3.1 作为默认主榜  
- V3.1 的 cap 78/84/88/92 阶梯主导 overall  
- 「hidden 通过率 ≈ 最终分」  
- 要求 flash/monitor/真机  
- 把效率强行揉进唯一总分（效率只进剖面与可选性价比榜）  

## 8. 设计约束（实施时）

1. 候选始终只见 `workspace/`。  
2. public 对干净 temp 环境必须可过（seed 不是废墟）。  
3. 脏库与 migration 陷阱不得导致「未改代码 public 必红」除非有意设计且文档说明——V4 默认 **public 用干净 DB**。  
4. 新增 hidden 必须挂 `item_id` 与 `blocker` 映射。  
5. 任何新 hard cap 必须通过 `08` 清单中的「会不会造新墙」检查。  

---

下一篇：[02_SCORING_SYSTEM.md](./02_SCORING_SYSTEM.md)
