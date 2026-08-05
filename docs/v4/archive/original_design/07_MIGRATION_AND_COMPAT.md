# V4 迁移、历史兼容与 rollout

## 1. 原则

1. **不毁掉 V2 语料**：`evaluator/results/*`、`reviews/*`、archives 只读保留。  
2. **新模型默认 V4**（实施完成后）。  
3. **旧结果不强制全量重跑**；提供重标注模式。  
4. **分数不可与 V1/V3.1 硬横比**；与 V2 可「叙事对照 + 重标注近似」。

## 2. 仓库布局演进

| 阶段 | 动作 |
|------|------|
| 设计（当前） | 仅 `docs/v4/**` |
| 实施 | 改 evaluator/workspace seed；tag `project2-v4-broken-seed` |
| 切换 | README 声明主线 V4；V2 设计笔记保留 |
| 归档 | 可选：`archives/second_round_v2_*` 已存在，不必再拷 |

**禁止**：删除 `archives/禁止删除_评测结果和归档.md` 所保护内容。

## 3. V2 → V4 结果重标注

### 3.1 适用

已有完整 review + hidden_summary + 静态/构建记录的 V2 run。

### 3.2 步骤

1. 读取 V2 正式分、ability note、blockers 叙述、hidden 失败列表。  
2. 按 `03_ITEM_BANK` 将失败映射到 F1–F12 扣分（附录有示例）。  
3. 计算 Ability 近似值。  
4. 套用 Ship 信任 cap 与 F3 门槛。  
5. 写入 `evaluator/reports/v4_relabel_from_v2.md`（实施后），标注 `relabel:true`、`not_rerun:true`。  

### 3.3 误差

重标注 **不是** 新评测。允许 ±3 分误差带。  
用于：验证 V4 是否拉开原 82 团；**不用于**宣称「历史模型官方 V4 分」。

### 3.4 校准重跑（推荐）

实施后选 4–5 个锚点真跑 V4：

| 锚点类型 | 例子 |
|----------|------|
| 顶部 | GPT-5.5 或 Grok-4.5 级 |
| 近顶 | GLM-5.2 API |
| 原 82 强 | Kimi K2.7 / Mimo Pro / LongCat |
| 原 82 弱或渠道样本 | Composer / WorkBuddy 某模型 |
| 信任失败 | Minimax M2.5 类 |

校准后微调 family 权重（若系统性偏差）。

## 4. 与 V3.1 的关系

| V3.1 资产 | 处理 |
|-----------|------|
| 题：mixed CSV、voice、脏库、buffer | **吸收进 V4 题库** |
| 评分：cap 78/84/88/92 | **丢弃** |
| answer.md | 不采用；PR 模板强化 |
| 分数榜 | 归档只读 |

## 5. 与 V1 的关系

- V1 弱提示轨可选保留为研究。  
- 协议：同一 seed 可配 weak prompt，分数前缀 `discovery_score`，**禁止**并进 V4 主榜。  

## 6. Rollout 检查清单（实施阶段用）

- [ ] seed 重置 public 绿  
- [ ] hidden 在 broken 上预期失败集合符合设计  
- [ ] frozen gold（已知完成版）Ability ≥ 95、Ship ≥ 95、Class A  
- [ ] 故意 ambient 漏的金残血：Ability 高、Ship≈Ability、有 `S-ambient` + Class B+  
- [ ] 故意 reason-only 错误：F3 行为分保留，只扣 F12，不生成 S-* 行为 blocker  
- [ ] 故意 public 红：Ship≤68  
- [ ] Ship/Ability 双视图 scoreboard 都可生成；Ship 同 gate 组内按 Ability 排序  
- [ ] score_draft 与人工差在可接受范围  
- [ ] score_draft_confidence 能标出 relabel / missing evidence / unscored items  
- [ ] 文档 README 指向 V4  
- [ ] 交叉审核意见关闭或记录偏差  

**frozen gold 锚点（MiniMax-M3 S2 增补）**：

V2 当前没有"已知完成版项目"作为 ground truth。V4 实施时必须保留一份 `archives/v4_gold/project2_task/`，与 broken seed 对照做：

- Ability ≥ 95、Ship ≥ 95、Class A 的 baseline
- 包含完整 admin/auth、context、sleep、care_event、ESP helper 模块拆分、real ESP build 通过、PR 模板完整
- frozen gold **不进入公开候选包**，仅供 evaluator 内部使用
- 位置：`archives/v4_gold/project2_task/`（与 `archives/third_round_v3.1_20260615/workspace_v3.1/project2_task/` 同级但独立）
- PR-A 落地后第一个自测夹具就是 frozen gold 跑通

**frozen gold 创建方式（Qwen3.7 Max S3）**：

1. 以 V2 顶部样本（优先 Grok-4.5；若 artifact 不完整则用 GPT-5.5）为基础，而不是从零手写。
2. 人工补齐 V4 新增/强化项：F4 voice bridge、F6 多台阶 migration、F7 mixed CSV、F8-07 buffer/static 等。
3. 用当前 V2 evaluator 先确认基础样本没有 public/debug/ESP 静态退化，再用 V4 PR-A 管线确认 score draft 与人工评估一致。
4. 写 `archives/v4_gold/README.md` 记录来源结果目录、人工补齐项、未验证硬件项和 build log 位置。
5. 不允许把 frozen gold 的实现 diff 暴露给候选可见包；它只服务内部自测和回归。

## 7. 风险

| 风险 | 缓解 |
|------|------|
| 权重调参争议 | 先冻结设计权重，校准跑后再动 |
| 历史对比党争议 | 明确 relabel 标签 |
| 实施范围膨胀 | 分 PR：评分管线 → 题库 → seed |
| 渠道政策执行松 | scoreboard 缺 channel 拒收录 |
| Ship 门槛形成新墙 | 强制双视图、同 gate 内按 Ability 排序、冻结前做门槛聚集审计 |
| F3/F12 拆分停在纸面 | 强制 PR-B 必须同步改 test runner；用 V2 历史样本（Grok-4.5 / GPT-5.5）做回归 |
| F8 static 改写过宽/过紧 | 用 V2 已知样本 8/8 / 5/8 / 5/8 做回归；uncertain 时人工 final |
| api_contracts 改写无验证 | 强制 V2 历史样本 7 行回归表（GLM-5.2/Grok-4.5/Doubao/K2.7/LongCat/Composer/DeepSeek V4 Flash） |

**V4 回滚条件（MiniMax-M3 S3 增补）**：

V4 改动非常大（评分结构、hidden、seed、test runner、rubric 全部动）。任一以下条件触发即冻结 V4 实施、回滚到 V2 seed 与当前 V2 rubric（**不是 V3.1**）：

| 条件 | 触发标准 | 含义 |
|------|----------|------|
| **回滚条件 1** | 校准 5 锚点与人工分差 > ±5 分 | 自动草稿不可信，必须回到 V2 的"自动汇总 + 人工终裁"模式 |
| **回滚条件 2** | top3 Ability 极差 < 1 | 双视图或 Ability 主序未生效，82 墙换皮复发 |
| **回滚条件 3** | F3/F12 拆分落地后，relabel 与重跑差 > ±3 | assertion-level mapping 噪音大，回滚到 V2 的 test-function 粒度 |

回滚流程：

1. 冻结 PR-B/C/D/E 的合并
2. 恢复 `evaluator/scoring/rubric.md` 为 V2 版本
3. 恢复 `evaluator/tests/hidden/test_context_policy.py` 为 V2 版本
4. 保留 `docs/v4/` 文档作为设计档（不删除），但 `evaluator/` 回到 V2 状态
5. 在 `evaluator/reports/v4_rollback_<date>.md` 写明回滚原因、触发的条件、未解决问题
6. V5 重新设计前必须先解决被触发的回滚条件

---

## 8. 建议实施 PR 切分（供后续）

1. **PR-A**：scoring 文档落地到 `evaluator/scoring/*` + registry + score_draft/置信度管线（测旧 hidden 仍跑）  
   - 输出 `score_draft.json`、`score_draft_confidence.json`、`blockers.json` 的空框架。
   - `score_draft_confidence.json` 必须包含 `overestimate_risk`。
   - PR-A 完成后先用 V2 seed + 旧 hidden 跑一次，确认 score_draft 与人工 review 差 < 5 分。
2. **PR-B1**：F3/F12 assertion-level mapping 最小闭环（必须先于所有其它 hidden 扩展）  
   - 实现 `item_registry.json` 的 F3/F12 条目、`scenario_id`、`test_method`、`semantic_only`。
   - 改 `test_context_policy.py`：推荐拆成 `*_behavior` / `*_reason` 两类测试。
   - 改 `run_hidden_tests.py`：按 item/scenario 输出 `hidden_summary.json`，而不是只按 test 函数输出。
   - 同步更新 `eval_helpers.py` 的 session/context fixture。
   - 回归验收：Grok-4.5 / GPT-5.5 的 reason-only 失败必须表现为 F3 行为分保留、F12 扣分、无 S-* behavior blocker。
3. **PR-B2**：其余 hidden 扩展（migration 多 case、mixed CSV、voice），并补 ambient-only / partial failure 夹具  
   - **关键风险**：`test_espidf_static_contract.py` 的 V4 改写是本 PR 最容易出错的环节。V2 的 static 检查器是死板关键词匹配，需按 `03_ITEM_BANK` 中的 `allowed_equivalents` 重写。
   - **过宽**：static 变好刷分，F8 虚高（V2 中 Mimo Flash static 7/8 但真实 build 失败、Minimax M2.5 static 8/8 但 build 失败）。
   - **过紧**：误杀合理实现（如 `std::string`/`malloc` 动态分配、间接宏定义 `#define TOF_BUF_SIZE`）。
   - **回归验证**：改写后用 V2 已知样本做回归——Grok-4.5（8/8）应仍为 8/8，DeepSeek Pro（5/8）应仍为 5/8，不应出现已知样本分数突变。
4. **PR-C**：seed + ONBOARDING + probe，验证 public 绿与症状级提示  
   - **去剧透**：改写 `reference/api_contracts.md` 第 49 行，避免剧透 ambient fallback 解法。
   - **脏库隔离**：脏库放在 `data/legacy_sample.db` 而非默认 DB 路径，确保 public TEMP 干净 DB 不受污染。
5. **PR-D**：scoreboard 双视图模板 + relabel 附录 + 锚点重跑  
6. **PR-E**：冻结前门槛聚集审计、frozen gold 自测与交叉审核意见关闭

---

下一篇：[08_CROSS_REVIEW_CHECKLIST.md](./08_CROSS_REVIEW_CHECKLIST.md)
