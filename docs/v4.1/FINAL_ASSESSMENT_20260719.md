# Project2 V4.1 最终评估

**日期：** 2026-07-19  
**正式基线：** V4.1b (`project2-v4.1b`)  
**状态：** 锚点轮次闭环，规则与正式结果冻结  
**详细终榜：** `evaluator/reports/v4.1b_scoreboard.md`

## 1. 最终结论

V4.1b 已足以承担当前个人开发场景中的模型选型，不再需要为了区分顶部模型继续增加
题目或启动 V5：

- **Ability >= 95 且 Ship 无严重硬伤：** 对当前日常项目可视为可靠完成档，剩余问题
  通常是可局部审查和收尾的细节。
- **Ability >= 90：** 可用执行档，适合实现、测试和常规改造，但应根据 Ship、blocker
  与失败 family 决定是否需要强模型终审。
- **Ability < 90 或 Ship 明显低于 Ability：** 需要更强监督；安全、迁移 crash、构建
  overclaim 等问题不能由总分掩盖。

这些阈值是本项目、本题面和当前工具环境下的工程经验，不是对所有代码库的通用能力
认证。实际使用仍优先看失败类型，而不是只看一分之差。

## 2. V4.1 相对 V4 的真实进步

### 2.1 F6 不再被单一启动错误全家连坐

V4.1 为迁移子能力构造独立 fixture。旧库完整升级 crash 仍通过 `M-crash` 限制 Ship，
但列补齐、回填、幂等和混排可以独立观测。Kimi K2.7 的 94 Ability / 88 Ship 是代表
样本：多数工程能力完成，但旧库升级仍不足以发布。

### 2.2 Ambient 不再在 F3 与 F5 重复扣分

V4.1b 将未授权 ambient 泄漏只计入 F3-05，F5-05 只测试授权 care 接线。Terra 两次
均为 94，且均只缺 ambient 与 reason，说明当前分数能表达“工程稳定、默认隐私策略偏
松”，不再混入 care 正向能力的重复损失。

### 2.3 Ability 与 Ship 的职责更清晰

- Grok run1：Ability 90，但 session spoof 使 Ship 65 / D。
- Kimi K2.7：Ability 94，但 migration crash 使 Ship 88。
- Minimax M2.7：Ability 73，明文密码使 Ship 60 / D。

局部完成度与发布风险不再被压成同一个数字。

### 2.4 重复运行揭示了单次成绩无法表达的稳定性

| 模型 | n | Ability 观测 | 解释 |
|---|---:|---:|---|
| GPT-5.6-sol high | 2 | 98-99 | 稳定近顶 |
| GPT-5.6-terra high | 2 | 94-94 | 稳定 ambient 短板 |
| GPT-5.6-luna high | 2 | 90-96 | 轨迹方差较大 |
| DeepSeek V4 Pro gray | 2 | 96-99 | 近顶，但属于特殊路由 |
| Grok-4.5 | 2 | 90-91 | Ability 稳定，Ship 65-88 波动 |

## 3. 不应误读为“模型整体进步”

跨版本分差混合了评分去级联、思考等级、provider、route、harness 和单次轨迹：

| 模型 | V4 -> V4.1b | 主要解释 |
|---|---|---|
| sol high | 98 -> 98 worst | 基本稳定 |
| terra high | 97 -> 94 | 重复运行暴露稳定 ambient |
| luna high | 98 -> 90 worst | 单次高分不能代表稳定下界 |
| Grok | 91 -> 90-91 | 基本稳定 |
| HY | 92/82 -> 86 | 去级联后得到更合理的中间值 |
| Qwen | 76 -> 81 | 主要来自迁移能力可独立观测 |
| DeepSeek | preview 78；gray 96-99 | 路由差异远大于评分变化 |

因此本轮最可靠的结论是“尺子进步了”，不是“所有模型升级了”。

## 4. 当前边界

### 4.1 顶部仍不是复杂能力区分

Sol run2 的 98 分只缺 `tof1` marker 与 reason-only；99 分只缺 reason。当前 98 与 99
主要表示细节命中，不足以证明复杂工程上限差异。V4.1 改善了中游测量和风险解释，
没有提升顶部任务难度。

### 4.2 Worst-of-n 只作为保守下界

V4.1b 保留既定规则：n>=2 的主列取 worst。但 n=1 与 n=2 混排存在样本数偏差，少测
的模型天然更不容易暴露低分轨迹。因此：

- n=1 一律视为 provisional single observation；
- worst 用于描述已观测可靠性下界，不解释成模型真实分布下界；
- 未来若重启新基准，应固定正式重复次数，并将单次能力与可靠性分榜。

### 4.3 成本不是完全同口径

实际账单、订阅积分、标价等价、灰度 cache 和中断恢复不能混为一种成本。DeepSeek gray
的约 $0.12 伴随特殊路由和异常高缓存命中，只能作为本次观测，不能外推为稳定冷启动
价格。效率继续作为副榜，不进入 Ability。

## 5. 最终决策

1. V4.1b 作为当前正式稳定基线；V4.0 与 V4.1a 保持历史冻结，不重算。
2. 不开发 V4.1c，不为 95-99 增加 marker、reason 或报告措辞题。
3. 不再全量重跑模型；新模型只在有真实选型需求时新增单行。
4. V5 保持远期 memo，不再以“区分顶部模型”为立项目标。
5. 只有真实开发出现 V4.1b 无法预测的系统性失败，才重新评估 V5。
6. 新鲜度、显式 session、provenance、QEMU 与 HIL 继续保留为题源，不进入近期施工。

## 6. 文件索引

| 文件 | 用途 |
|---|---|
| `docs/v4.1/ROUND_SUMMARY_20260719.md` | 本轮事实与成本终稿 |
| `evaluator/reports/v4.1b_scoreboard.md` | 正式成绩与样本索引 |
| `evaluator/reports/v4.1_efficiency_board.md` | 成本/时间副榜 |
| `evaluator/reports/v4.1b_freeze_manifest.md` | 规则与正式 summary 哈希 |
| `docs/V5_DESIGN_DIRECTION.md` | 远期题源与重启条件 |

