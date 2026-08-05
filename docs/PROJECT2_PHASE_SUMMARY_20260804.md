# Project2 模型评测阶段性总结

**总结日期：** 2026-08-04  
**当前正式基线：** V4.1b (`project2-v4.1b`)  
**阶段状态：** 本轮评测收工；新模型只在有明确选型需求时追加，不再全量重跑

## 0. 结论先行

这个项目已经从“给模型跑几道代码题”发展成了一套相当完整的工程交付评测：它同时观察
最终代码能力（Ability）、发布风险（Ship/Class）、过程和证据可信度，以及成本与执行效率。

截至 V4.1b，评测已经回答了当前最重要的问题：

- **Ability >= 95 且没有严重 Ship blocker**：对当前个人日常开发，通常已经是可靠完成档。
- **Ability >= 90**：可以承担实现工作，但要按失败 family 和 Ship 结果做终审。
- **低于 90，或 Ship 明显低于 Ability**：不能只看总分，安全、迁移崩溃、构建证据和
  隐私边界需要人工接管。

这些阈值只适用于本项目、本题面和当前工具环境，不是跨项目的模型认证。

最重要的工程结论不是“谁永远第一”，而是：**模型能把主线功能做出来以后，真正拉开差距的
是隐私边界、历史数据迁移、跨模块收口、真实构建和报告可信度。**

## 1. 评测是怎样演进到这里的

### V1：主动发现

V1 使用较弱提示，要求模型自己读项目、找问题、跑测试并完成修复。它更接近“用户只给一句
模糊需求时，模型能否主动进入系统性排查”，中游大量集中在 48--55 分。

### V2：现象驱动的 debug

V2 给出更明确的症状和工程约束，测的是“知道问题在哪里以后，能不能真正修完并交付”。平均分
和中位数明显上升，但新的拥挤点变成 80--82 分。这里暴露出：很多模型并非不会写代码，而是
不会主动发现高风险边界，或者不会完成最后的工程收口。

### V4.0：建立正式尺子

V4 保留 V2 的工程壳，重做了题库和证据链，正式建立：

- Ability 与 Ship/Class 双轨；
- F1--F12 细粒度 family；
- ambient/context、reason semantics、migration、voice bridge、ESP static 和真实 build
  的独立观测；
- Gold 100/A；
- result-local 的 ESP build log、固件、size 和 SHA256 证据；
- 候选隔离和正式 meta。

V4.0 的核心修正是取消旧版 ambient 的 82 分硬墙，并把“做了多少”和“能不能发布”分开。

### V4.1a：修复迁移连坐和单次成绩幻觉

V4.1a 为 F6 migration 建立独立 fixture，使旧库启动崩溃不再抹掉列补齐、timestamp 回填、
幂等初始化和混合排序等其它能力；同时引入 `run_group_id`、`run_index` 和
`thinking_level`，正式承认一次运行只是“模型 + provider + harness + trajectory”的观测。

### V4.1b：收口为稳定基线

V4.1b 只做一个必要修正：ambient 泄漏只在 F3-05 扣分，F5-05 改为只测授权 care wiring。
这样“隐私策略偏松”和“授权业务链路没接上”不再重复扣分。V4.1b 于 2026-07-19 冻结，
不再计划 V4.1c。

## 2. 当前评分体系真正测什么

正式 100 分由 12 个 family 构成：

| Family | 主要问题 |
|---|---|
| F1 | 诊断、最终验证、构建记录和事实一致性 |
| F2 | 密码、cookie、admin API、身份边界 |
| F3 | 未认证、跨患者、过期 session、无 actor、ambient context |
| F4 | voice 与显式 session/context 桥接 |
| F5 | care_event 创建、过滤、排序、归一化和授权上下文 |
| F6 | 旧 schema、补列、timestamp 保真、幂等和混合排序 |
| F7 | sleep CSV 的默认床位、first/skip/all 和混合输入 |
| F8 | ESP 依赖、Wi-Fi/MQTT、topic、payload、缓冲和 ready 契约 |
| F9 | 真实 ESP-IDF build 及 result-local 证据 |
| F10 | legacy API、ESP/set 和 worker/identity 回归 |
| F11 | 文档同步、模块边界和可维护性 |
| F12 | reason code 等语义精度；只影响 Ability，不制造行为硬墙 |

Ability 是工程完成度；Ship/Class 额外表达明文密码、session spoof、migration crash、
构建 overclaim 等发布风险。效率、价格和 harness 摩擦只进副榜，不进入 Ability。

这个分层已经证明必要：例如 Ability 90 的 Grok run1 因 session spoof 变成 Ship 65/D；
Kimi K2.7 Ability 94 但 migration crash 使 Ship 88；Minimax M2.7 的 Ability 73 因明文
密码降到 Ship 60/D。

## 3. V4.1b 正式榜的阶段性画像

主列对 n>=2 取已观测 worst formal；n=1 标记为 single-observation，不能把它当成与 n=2
同等强度的稳定性证据。

| 模型/路由 | Main Ability | Ship/Class | 阶段性画像 |
|---|---:|---|---|
| GPT-5.6-sol Codex high | 98 | 98--99 / B+--A | 当前最稳定的近顶样本，主要剩 marker/reason 细节 |
| DeepSeek-V4-Pro 灰度正式 | 96 | 96--99 / B+--A | 能力近顶，CPI 极强；路由与缓存有特殊性 |
| GPT-5.6-terra high | 94 | 94 / B+ | 两枪锁定，ambient 是稳定短板 |
| Kimi-K2.7-Code WorkBuddy | 94 | 88 / B+ | 主线广泛完成，但 migration crash 影响发布 |
| Kimi-K3 | 92 | 92 / B+ | F6 较完整，但贵、慢，单枪证据 |
| GLM-5.2 WorkBuddy xhigh | 91 | 91 / B+ | 工程能力中上，仍有隐私/收口细节 |
| GPT-5.6-luna high | 90 | 90--96 / B+ | 上限不低，但方差大、预算和轨迹依赖明显 |
| Grok-4.5 | 90 | 65--88 / D--B+ | Ability 90--91；Ship 受一枪 spoof 严重影响；API 很快 |
| Doubao Evolving-0714 | 90 | 90 / B+ | F6 较好，voice/ambient 仍有缺口 |
| Qwen-3.8-Max-Preview | 87 | 87--89 / B+ | 双枪主缺口同构，较 3.7 有提升 |
| Gemini-3.5-Flash | 87 | 87--88 / B+ | voice 满，但 migration crash 双枪复现 |
| HY-3 | 86 | 86 / B+ | ambient/no-actor 短板，F6 部分完成 |
| Mimo-v2.5-Pro | 83 | 83 / B | 价格接近 DeepSeek，但隐私、voice 和 crash 拉低交付 |
| LongCat-2.0 | 82.5 | 72--94 / B--B+ | 三枪/追加观测显示方差很大，不能用最好一枪代表平台 |
| Gemini-3.1-Pro | 82 | 60 / D | 明文密码是硬伤，Ability 不能掩盖发布风险 |
| Qwen-3.7-Max | 81 | 81 / B | voice 和 ESP 契约仍弱 |
| Minimax-M2.7 | 73 | 60 / D | 下沿负对照；明文密码和多项基础缺口 |

DeepSeek 的 gray 和 preview 必须分轨：正式灰度两枪为 96--99，而 preview 为 78/72；
这说明 provider/route 差异可以大到超过很多模型代际差异，不能把“DeepSeek V4”当成一个
无条件统一的交付物。

## 4. 反复出现的能力结构

### 4.1 ambient 是最稳定的分水岭

很多模型能实现认证、care_event 和大部分业务，但仍会把当前 ambient session 当成目标
患者授权。V4.1b 之后它只扣一次 5 分，但仍然是最有诊断价值的失败：它同时测试了隐私
边界、session provenance 和“不要因为上下文方便就越权”。

### 4.2 migration 是工程成熟度探针

旧库启动不崩只是第一步。补列、旧数据保真、timestamp 回填、重复初始化和新旧记录混排
共同测试“能否安全演进已有系统”。许多模型能修新代码，却在真实历史数据上漏最后一层。

### 4.3 ESP static 不等于真实可构建

静态 marker 能观察契约覆盖，但必须和真实 ESP-IDF build 分开。V4 的 F9 result-local 证据
要求 log、固件、size、SHA256 同时存在；共享目录里“曾经编过”不算可复核满分。

### 4.4 报告可信度是能力的一部分，但不能替代代码分

常见问题包括：公共测试失败却宣称完成、只看 marker 就声称协议完整、没有记录最终验证命令、
把构建失败解释成环境问题。F1/F11/Ship 把这些风险显式化，避免漂亮总结掩盖未验证状态。

### 4.5 高思考预算不保证更高交付

早期 GPT-5.6 单次数据已出现 high 到 xhigh 只加 1 分、甚至增加时间和成本却掉分的情况。
因此“多想”应视为额外计算预算，而不是能力等级；真正重要的是新增预算是否转化为有效编辑、
测试覆盖和最终验证。

## 5. 最近 v4f / luna 思考预算对照

这两枪属于阶段性附录，不改正式主榜。

| 模型 | 配置 | Ability | 观察 |
|---|---|---:|---|
| DeepSeek-V4-Flash 正式 | 开思考，多渠道 | 92--95 | 结构性能力稳定，部分渠道修住 ambient |
| DeepSeek-V4-Flash 正式 | reasonix，关闭思考 | 92 | ESP 9/9、真实 build、migration 保持；ambient/PR/reason 细节掉分 |
| GPT-5.6-luna | high，两枪 | 90--96 | 能达到较高上限，但轨迹方差大 |
| GPT-5.6-luna | low，单枪 | 84 | voice session、ESP 契约、ts backfill、报告收尾缺失；F12-04 反而首次通过 |

这组对照最支持的解释是：

1. v4f 的基础工程能力和后训练执行习惯在关闭思考时仍然保留；
2. luna 更依赖额外推理预算完成跨文件检查、隐含契约和最后收口；
3. 可见的“草稿式思考”主要是 API reasoning channel、后训练格式和 harness 行为，不能
   直接拿来推断参数量；
4. 参数量可能影响低预算鲁棒性，但本实验同时混入了模型家族、provider、harness、随机
   轨迹和预算，不能据此反推参数规模。

从失败形态看，luna low 不是基础能力全面崩溃，而是“主线做了，闭环没关”。这比单纯的
总分差更有解释力。

## 6. 成本与效率：应该怎样读

成本副榜已经足够支持日常选型，但不能把不同计价体系硬合成一个绝对排名：真实账单、订阅
积分、标价等价、缓存命中和中断恢复必须分开记录。

阶段性 CPI 画像：

- **DeepSeek gray**：约 $0.12/枪、主列 96，观测上是 CPI 王；但 miss 只有约 3k、上下文
  可达 200k+，存在特殊缓存/路由条件，不能外推为冷启动价格。
- **GPT-5.6-terra high**：约 $2.04、13 分钟、94，稳定且轻量。
- **GPT-5.6-luna high**：约 $1.93、22 分钟、主列 90，单价低但 token 用量和方差较大。
- **GPT-5.6-sol high**：约 $8.18、25 分钟、98，顶端能力但成本显著更高。
- **Grok-4.5**：约 $1.2--1.6/枪，API 约 6--7 分钟，卖点是速度与 harness 手感，不是
  纯 CPI 击穿 DeepSeek。
- **Kimi-K3**：实付 $6.13（去换号缓存税约 $5.63）、约 48 分钟，分数中上但偏贵慢。

成本和时间不进 Ability 的决定是正确的：否则会把“更便宜”误当成“更会做”，也会把工具
摩擦误判成模型代码能力。

## 7. 评测设计上已经被验证的原则

### 已验证有效

- Ability/Ship 双轨确实比单一总分诚实。
- 把 ambient、reason、migration、ESP static/build 拆开，能解释模型为什么失分。
- F6 独立 fixture 消除了单一启动错误造成的全家 0 分。
- multi-run 证明单次最高分不可靠：luna 96→90、DeepSeek gray 99→96，而 terra 两枪
  锁 94。
- Gold 100/A、真实 build 和哈希证据让满分有可验证上限。
- 候选隔离、强制 meta、result-local artifact 减少了环境和历史状态污染。
- 历史 V1/V2/V4 分数不强行换算，保留版本边界，是避免伪精确的必要条件。

### 已明确不做

- 不用 V4.1b 规则重算 V4.0/V4.1a 正式分。
- 不为区分 95、98、99 继续堆 marker、reason 或报告措辞题。
- 不把效率、价格、原始思维链猜测混入 Ability。
- 不因顶部拥挤就启动 V5 或全量复测。

## 8. V5 为什么暂缓

V4.1b 已足以支持当前模型选型；继续开发新题的即时收益低于实施、校准和复测成本。
V5 只有在真实开发中出现“V4.1b 无法预测或解释”的系统性失败时才重启。

未来如果重启，方向应是一个独立的高耦合 capstone，而不是把更多零散 marker 塞进 100 分：

- 数据新鲜度与 provenance 真值链；
- 显式 session 和跨患者/跨模块的隐私闭环；
- sensor → gateway → care_event → context → voice 的端到端闭环；
- 离线重放幂等、故障降级摘要；
- QEMU 与少量 HIL 真机验证。

V5 HIL 还需要先证明测试台健康、Gold 可重复通过，并且能清晰区分 `candidate_fail`、
`bench_fail` 和 `skipped_env`。当前不具备启动条件。

## 9. 当前操作决策

1. 把 V4.1b 作为项目正式稳定基线。
2. 新模型只在有实际选型需求时追加新行，记录完整 model/provider/channel/harness/
   thinking/cost meta。
3. 单次结果标为 single-observation；有重复运行时继续报告 best/worst/range，不把
   worst-of-2 伪装成统计学下界。
4. 日常使用优先看失败 family 和 Ship，而不是只看榜单名次。
5. 遇到真实 bug 时先保存最小复现、日志和修复前后证据，不立即把它加工成 V5 题目。
6. 继续保留 V1/V2/V4/V4.1b 归档，不覆盖历史结果。

## 10. 资料与证据索引

### 当前主文档

- [`docs/v4.1/FINAL_ASSESSMENT_20260719.md`](./v4.1/FINAL_ASSESSMENT_20260719.md)
- [`docs/v4.1/ROUND_SUMMARY_20260719.md`](./v4.1/ROUND_SUMMARY_20260719.md)
- [`docs/v4.1/DESIGN.md`](./v4.1/DESIGN.md)
- [`docs/v4.1/MULTI_RUN_PROTOCOL.md`](./v4.1/MULTI_RUN_PROTOCOL.md)
- [`evaluator/reports/v4.1b_scoreboard.md`](../evaluator/reports/v4.1b_scoreboard.md)
- [`evaluator/reports/v4.1b_freeze_manifest.md`](../evaluator/reports/v4.1b_freeze_manifest.md)
- [`evaluator/reports/v4.1_efficiency_board.md`](../evaluator/reports/v4.1_efficiency_board.md)

### 历史版本与设计依据

- [`docs/v4/CURRENT_STATE_VS_ORIGINAL_DESIGN.md`](./v4/CURRENT_STATE_VS_ORIGINAL_DESIGN.md)
- [`evaluator/reports/v4_v2_comparison_final.md`](../evaluator/reports/v4_v2_comparison_final.md)
- [`evaluator/reports/v4_freeze_manifest.md`](../evaluator/reports/v4_freeze_manifest.md)
- `docs/v4/archive/original_design/00`--`08`、评分体系、题库、流水线、反偏置和交叉评审
- [`docs/V5_DESIGN_DIRECTION.md`](./V5_DESIGN_DIRECTION.md)

### 模型评审

模型逐枪证据保存在 `evaluator/reviews/`；V4.1b 正式索引和 result_id 以
`evaluator/reports/v4.1b_scoreboard.md`、`v4.1b_freeze_manifest.md` 为准。最新思考预算
对照为：

- `v4.1b_DeepSeek-V4-Flash_reasonix_nothink_20260803_222134.md`
- `v4.1b_GPT-5.6-luna_codex-low_20260803_224030.md`

## 最终一句话

Project2 这一阶段已经收工：**V4.1b 足够做日常模型选型，榜单只是入口，失败类型和证据链
才是结论；V5 等真实开发盲区出现后再做。**
