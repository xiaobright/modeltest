# 固定规划执行评测：实施交接设计

**状态：** Draft for implementation and review  
**实施者建议：** GPT-5.6 Luna high  
**新项目目标路径：** `E:\Desktop\mytests\modeltest-planexec`  
**当前 V4 只读来源：** `E:\Desktop\mytests\modeltest`  
**真实项目只读题源：** `E:\Desktop\myproject\project`

> 本文是一份“评测方案的实施设计”，用于让实现者搭建可重复的固定规划执行评测。
> 实现者本轮的表现可以作为一次非正式的“规划 -> 实施 -> 审查”观察，但不能进入正式
> 榜单：框架、seed、oracle 和规则尚未冻结，而且实现者能看到完整设计。

## 1. 要回答的问题

V4 已证明 GPT-5.6 Luna high 在当前真实改造任务中接近 Sol xhigh，而成本明显更低。
新评测不再重复比较“模型能否自己发现所有问题”，而要回答：

1. 给定同一份高质量工程计划后，较便宜模型首次交付能达到什么质量？
2. 计划能否降低 migration 等高方差问题的失败率？
3. 收到同一标准的专家级、症状级审查意见后，还需要多少返修？
4. 达到 B+、A 或指定 Ability 阈值的总时间和总成本是多少？
5. Sol 的主要价值是否可以收缩为一次性规划/审查，而无需承担全部实施工作？

正式比较单位是：

```text
scenario version
+ fixed plan version
+ model
+ provider / endpoint product / billing tier
+ harness
+ thinking level
+ run trajectory
```

一次运行是交付样本，不直接等同于模型的稳定水平。

## 2. 范围与非目标

### 2.1 MVP 必须完成

- 建立独立同级项目 `modeltest-planexec`，不得修改 V4 frozen 项目。
- 实现场景化、可重置、候选隔离的两阶段工作流。
- 落地首个正式候选场景 `v4-plan-replay`。
- 冻结一份候选可见的专家实施计划。
- 首次交付后保存 P0 不可变快照并独立评分。
- 根据 hidden 结果生成确定性的症状级审查包。
- 同一候选在审查包基础上返修，保存 P1 快照并再次评分。
- 分阶段记录质量、时间、成本、token/cache 元数据和人工介入。
- 生成 run report 与跨重复运行的稳定性视图。
- 用 broken seed、Gold 和至少两个合成提交验证工作流。
- MVP 只实现 evaluator 控制流；具体模型由操作者在 Codex、Qoder、WorkBuddy、Cursor 等
  外部 harness 中运行，不建立统一模型/provider 调用层。

### 2.2 MVP 只搭骨架，不完成正式出题

- `freshness-chain` 高耦合场景只建立 authoring 文档、manifest 草案和目录占位。
- 不在本轮实现完整 ESP/QEMU/真机测试。
- 不把 `E:\Desktop\myproject\project` 整仓复制进候选 seed。
- 不把 V5 高耦合 capstone 或 V5 HIL 真机验证与本评测合并。

### 2.3 非目标

- 不动态调用 Sol 生成每次计划或审查。
- 不把质量、价格和速度压成一个缺乏解释力的总分。
- 不将 plan-guided 成绩与 V4 autonomous Ability 混排。
- 不通过暴露 hidden 测试、Gold diff、准确行号或补丁答案降低任务难度。
- 不为了框架通用性引入数据库、Web 服务、容器编排等额外运行依赖。

## 3. 设计原则

### 3.1 固定规划，不固定代码实现

计划应明确：当前状态、目标行为、模块范围、实施顺序、兼容边界、风险和验证方式。
计划不得给出完整函数、准确补丁、hidden 输入值或唯一代码结构。

候选仍需完成：

- 阅读现有代码并定位真实边界；
- 将计划映射到当前实现；
- 选择数据结构和函数组织；
- 处理计划没有逐行展开的局部细节；
- 运行工具、调试失败并完成全仓收口。

### 3.2 首次交付与返修必须隔离

P0 评分完成前不得向候选暴露 hidden 结果或审查包。P0 快照生成后不可覆盖。P1 必须
从 P0 工作树继续，不得换用 Gold、其他模型提交或重新从 seed 开始。

### 3.3 审查包确定、可复用、不过度剧透

不为每次运行调用真实 Sol。每个 hidden `scenario_id` 对应一条预先冻结的症状级 review
模板。P0 失败后只发出适用模板，例如：

```text
旧版本数据库升级路径仍可能在服务初始化阶段失败。请验证 schema 变更、数据回填与
依赖新列的索引创建顺序，并用旧数据重复初始化确认兼容性。
```

不得输出失败测试名、测试源码、准确异常行、Gold 代码或直接 patch。该阶段必须标为
`deterministic_oracle_review`，不能伪称真实 Sol review，也不用于衡量 reviewer 假阳性。

### 3.4 质量与经济性分开报告

- P0/P1 使用各场景自己的 Ability、Ship、Class、family、blockers。
- 经济性单列 implementation、review delivery、repair 和 total。
- 可以计算达到阈值的成本，但不得用低价给 Ability 加分。
- 固定计划的作者成本同时报告 `one_off` 与按 N 次运行摊销后的 `amortized`。

### 3.5 V4 冻结边界

`v4-plan-replay` 必须复用 V4.0 frozen 的 seed、hidden、scoring 和 Gold 语义。不得顺手
修正 F6 权重或重算 V4 历史榜。F6 的 fixture 解耦属于 V5 远期设计；本场景的意义之一
正是观察明确计划是否能降低现有 F6 的随机性。

Ability、Ship、Class 必须完全使用 V4.0 的 100 分 registry、权重和 blocker 规则。本文
后述的“约 80% 计划明确、约 20% 局部细节”只是计划 authoring 的覆盖目标，不创建新
分值、不调整权重，也不参与评分计算。

### 3.6 运行时澄清协议

框架实现者在 pre-freeze 阶段应主动提出会改变数据结构、评分或运行语义的设计歧义；
正式候选运行开始后，不接受针对单个模型的内容答疑。候选若认为信息不足，应记录假设
并按固定计划、兼容约束和现有代码继续实施。

操作者只可使用预注册答复：

- 题目内有意保留的工程判断：`请依据已提供计划、兼容约束和现有代码自行判断并继续。`
- 已在公开材料中回答的问题：只引用同一公开章节，不增加解释。
- 环境事实：可提供预先定义的工具链/路径状态，必须写入 run intervention log。
- 真正的非预期歧义：中止该 run，修订 scenario version；不得只向当前模型补充答案后
  继续与旧 run 比较。

所有模型在同一 scenario version 下必须看到相同公开材料和可用答复集合。

## 4. 新项目建议结构

```text
E:\Desktop\mytests\modeltest-planexec\
  README.md
  DESIGN_STATUS.md
  .gitignore
  docs\
    ARCHITECTURE.md
    AUTHORING_GUIDE.md
    OPERATOR_GUIDE.md
    SCORING_AND_METRICS.md
    SOURCE_PROVENANCE.md
  scenarios\
    v4-plan-replay\
      manifest.json
      public\
        task.md
        implementation_plan.md
        reference\
        tests\
        tools\
      private\
        seed\
        evaluator_tests\
        scoring\
        review_catalog.json
        gold\
        provenance.json
      authoring\
        design_notes.md
        acceptance_matrix.md
    freshness-chain\
      manifest.draft.json
      authoring\
        design_brief.md
        source_evidence.md
        acceptance_matrix.draft.md
  evaluator\
    workflow.py
    prepare_run.py
    evaluate_stage.py
    generate_review_packet.py
    finalize_run.py
    aggregate_runs.py
    common\
    tests\
  runs\
    <run_id>\
      run_manifest.json
      p0\
      review\
      p1\
      final_report.md
  workspace\
    staging\
  archives\
    frozen_scenarios\
```

候选可见 handoff 不放在上述 control plane 内。默认输出到：

```text
E:\Desktop\mytests\modeltest_planexec_handoffs\<run_id>\workspace\
```

实现者可以调整 Python 模块拆分，但必须保留 control plane / candidate handoff 的物理
隔离，以及 scenario public/private 的边界。

## 5. 场景 manifest

每个 frozen 场景至少包含以下字段：

```json
{
  "scenario_id": "v4-plan-replay",
  "scenario_version": "1.0.0",
  "status": "draft|calibrating|frozen|retired",
  "track": "plan_replay|feature_implementation",
  "seed_sha256": "...",
  "public_plan_sha256": "...",
  "review_catalog_sha256": "...",
  "evaluator_version": "...",
  "scoring_version": "...",
  "candidate_project_relpath": "project2_task",
  "public_commands": [],
  "evaluation_commands": [],
  "thresholds": {"b_plus": 90, "a": 95}
}
```

准备运行时把 manifest 的所有哈希复制进 `run_manifest.json`。运行过程中发现源文件漂移
必须中止，不得静默继续。

## 6. 工作流状态机

唯一合法状态序列：

```text
prepared
-> implementation_active
-> p0_frozen
-> p0_evaluated
-> review_released
-> repair_active -> p1_frozen -> p1_evaluated -> finalized

或在 P0 无候选可修复 finding 时：

review_released -> p1_not_required -> finalized
```

失败可进入 `aborted`，但不得从后续状态倒退或覆盖旧快照。

### 6.1 Prepare

建议命令：

```powershell
python evaluator\prepare_run.py `
  --scenario v4-plan-replay `
  --model MODEL --provider PROVIDER --channel CHANNEL `
  --harness HARNESS --thinking LEVEL
```

必须完成：

- 校验 frozen manifest 与哈希；
- 创建唯一 `run_id`；
- 从私有 seed 生成全新 git workspace；
- 只复制 public allowlist；
- 写入模型、渠道、harness 和强度元数据；
- 输出候选可见绝对路径；
- 验证 handoff 不含 `private`、hidden、Gold、review catalog、旧结果或控制侧文档。

### 6.2 P0 实施与冻结

候选只接收 task、固定 plan、public reference/tests/tools 和项目目录。操作者记录开始/结束
时间与费用。结束后 evaluator：

- 保存候选 git diff、status、log 和报告；
- 复制完整项目快照或生成可校验 bundle；
- 记录 snapshot SHA-256；
- 将 P0 目录设为只读语义，不再覆盖；
- 使用 evaluator-owned tests 对快照评分。

### 6.3 确定性审查包

`generate_review_packet.py` 读取 P0 结构化结果，以 `scenario_id` 匹配冻结 review catalog。
输出包含：

- 已确认的发布阻断；
- 症状级行为描述；
- 建议验证的边界；
- 明确声明没有提供代码答案。

catalog 覆盖所有可由候选修改解决的评分项：行为、semantic-only、文档/报告，以及可
归因于候选代码的 public/static/build 失败。工具链缺失、外部服务故障、纯 evaluator
错误和无法归因项只进入环境/置信度记录，不投放为候选 finding。

同一组 P0 结构化失败必须生成 byte-for-byte 相同的审查正文。正文只包含排序后的固定
finding；`run_id`、路径、生成时间和环境状态放入外层 manifest。确定性以正文 SHA-256
验证。排序按冻结 priority + scenario_id，避免字典顺序或时间戳造成内容漂移。

如果没有候选可修复 finding，仍生成固定的 no-findings `REVIEW_PACKET.md`，但不再次
调用模型、不制造空返修阶段。P1 在结构化结果中记为 `not_required`，引用 P0 snapshot
hash 与分数，repair time/cost 为 0，并保留“未执行第二次候选调用”的事实。

### 6.4 P1 返修与冻结

审查包加入原 handoff 的固定位置，例如 `REVIEW_PACKET.md`。候选继续修改同一项目。
冻结与评分规则和 P0 相同，并额外计算：

- resolved blockers；
- remaining blockers；
- introduced regressions；
- Ability/Ship delta；
- repair time/cost；
- 每条 review finding 的 resolved / partial / unresolved / regressed 状态。

### 6.5 Finalize

生成结构化 JSON 和人类可读 Markdown。报告不得只展示最终 P1，必须并列 P0、P1 与
变化来源。

## 7. `v4-plan-replay` 首个场景

### 7.1 来源

- seed：当前 V4 `project2-v4-broken-seed` 的独立复制；
- evaluator、rubric、item registry、Gold：从 V4.0 frozen 复制并记录文件哈希；
- public candidate shell：沿用当前 allowlist handoff 思路；
- 历史 direct-run V4 成绩只作为对照，不写入候选包。

禁止使用软链接或运行时直接引用当前 V4 live 文件。新项目一旦导入，应以来源清单、
commit/hash 和复制日期固化，避免未来修改当前项目影响新评测。

### 7.2 固定计划必须覆盖的工作流

公开计划应按依赖顺序说明以下工作包，但不得给完整补丁：

1. 基线检查、模块地图与不得修改的测试/工具边界。
2. 管理员账户、密码哈希、随机会话 token、过期和撤销链。
3. actor/session/target 的 context 授权矩阵，包含无 actor、过期、跨患者和 ambient。
4. voice 获取 current session 并在同一调用链显式传给 context，禁止静默 ambient fallback。
5. care_event schema、CRUD、HTTP、context 集成和旧数据库兼容。
6. migration 顺序：补列、回填、约束/索引、读写验证、重复初始化；强调旧库不能只因
   新安装通过就视为完成。
7. sleep CSV 的逐行 ownership 与 mixed row 策略。
8. ESP32 Wi-Fi/MQTT/NVS/协议/static/build 契约及 host/firmware 两端一致性。
9. 回归、真实 build 证据、报告诚实性和未验证风险。

计划应给出每个工作包的“目标、涉及模块、依赖、验收行为、建议验证命令”，但不写
准确实现行号。计划作者需要维护一份私有 `acceptance_matrix.md`，证明每个公开计划项
对应至少一个可观察 oracle，同时标记哪些 hidden 项只属于模型自行补齐的局部工程细节。

### 7.3 信息比例

该场景是 plan replay，可比通常的自主任务更明确。建议：

- 约 80% 分值由计划明确点名的行为覆盖；
- 约 20% 保留为实现细节、兼容组合和回归边界；
- 不再用“模型是否猜到有旧库”作为主要区分，而测它能否按计划真正完成。

以上比例只用于审查 `implementation_plan.md` 的信息覆盖，不改变 V4 registry、100 分
总分或任一 family 权重。实际分数仍由原 V4.0 evaluator 完整计算。

### 7.4 直接对照的解释边界

Plan Replay 与历史 V4 direct run 使用相同代码 oracle，但提示信息不同，因此只能报告：

```text
direct autonomous run
vs
fixed-plan run P0
vs
fixed-plan + deterministic review run P1
```

不得把三者混成同一主榜。对历史单次成绩的提升只能称 observed uplift，不得在没有重复
样本时称模型能力提升。

## 8. `freshness-chain` 后续场景骨架

该场景未来从健康 seed 增加一个真实高耦合功能，而不是植入一组无关旧 bug。真实题源
来自 `E:\Desktop\myproject\project` 的 `b35cef1^ -> b35cef1`，但只能提炼行为，不直接
复制完整修复 diff。

建议业务目标：

> ESP 上报设备/传感器状态、序号和采样时间；Gateway 正确处理重复、乱序、断连、未来
> 时间和部分传感器失败；Context 只使用仍有效的数据；Voice 不得把缺失或过期数据说成
> 当前事实；旧协议仍可兼容。

authoring 草案至少记录：

- 固件/协议字段与 legacy compatibility；
- receive time、sample time、freshness 和 sequence 的不同语义；
- duplicate、out-of-order、future timestamp、disconnect、partial sensor failure；
- Gateway store/prune/context/voice 的纵向链路；
- fake adapter 或协议 replay 边界；
- host tests、ESP static/build 与未来 QEMU 的证据等级；
- 可独立计分的子行为，避免一个入口 crash 级联归零。

本轮不得把 RKLLM、视觉、LoRA、双 ESP 和所有硬件模块一起搬入。等 V4 Plan Replay
证明框架有效后，再决定是否投入完整 Gold、hidden 和校准。

## 9. 指标与结果结构

### 9.1 每阶段质量

- Ability、Ship、Class；
- family breakdown；
- behavior blockers / semantic-only；
- public、hidden、static、build；
- changed files、diff size、测试修改/越界行为；
- 报告完整性与 overclaim。

### 9.2 工作流变化

- `p0_to_p1_ability_delta`；
- blocker resolution rate；
- review finding resolution matrix；
- introduced regression count；
- repair cycles，MVP 固定最多一次正式 P1；
- human intervention count 与内容。

### 9.3 时间与成本

至少分开记录：

- plan authoring one-off cost/time；
- P0 implementation；
- deterministic review delivery，通常接近零模型成本；
- P1 repair；
- evaluator/build wall time；
- total wall time 与 active model time；
- USD/积分、输入、输出、cache read/write，未知字段必须为 null 而非 0。

不同渠道账单口径不得伪装成可直接比较的美元。原始账单值、换算公式和估算值应分字段。

### 9.4 重复性

聚合报告至少包含：

- runs；
- best、worst、range；
- mean/median，仅在样本数允许时展示；
- 各 family pass rate；
- P0 达到 B+/A 的概率；
- P1 达到 B+/A 的概率；
- 返修成本分布。

不得把极差写成方差。`n=1` 时明确标 single observation；`n=2` 只报告观测区间，避免
过度统计推断。

框架和 scenario 可以在 Gold/broken/synthetic 校准通过后进入 pre-freeze，不要求为了
冻结工具先批量调用真实模型。真实模型 `n=1` 只能发布 run-level 样本；同配置至少两次
后才展示 observed range，至少三次后才讨论稳定性趋势。是否为昂贵模型执行第三次及
以上运行，由正式测试预算另行决定。

## 10. 安全、隔离与数据完整性

- 当前 `modeltest`、真实项目和所有 archives/results 均为只读来源。
- `E:\Desktop\myproject\project` 当前存在用户修改：
  `esp32/testpro3/dependencies.lock` 已修改、`审查结果.txt` 未跟踪；不得改动、清理或提交。
- 不删除任何来源文件、历史结果、handoff 或 run。清理必须另行列绝对路径并取得确认。
- seed、Gold、hidden、review catalog 不得进入候选 handoff。
- evaluator 必须使用自己的测试副本，不信任候选可编辑的 public tests/tools。
- 所有快照、计划、review catalog、结果 JSON 和关键 build artifact 都记录 SHA-256。
- 候选不得读取 handoff 外路径；投放提示词明确此边界，操作者也不得把 control plane
  目录直接作为候选工作区打开。
- MVP 提供的是 physical handoff data isolation + policy boundary + evaluator leak scan，
  不是 Windows OS sandbox；不得宣称能够从进程权限上阻止候选访问其他磁盘路径。
- 路径检查使用 `Path.resolve()` 并验证目标位于新项目或 handoff 根内；任何 reset/clean
  都不得作用于来源项目或父目录。

## 11. 实施顺序

### PR-A：仓库骨架与边界

- 创建新项目、文档、scenario manifest schema 和路径 guard。
- 实现 public/private allowlist 检查与 handoff leak test。
- 实现 run ID、状态机、原子 JSON 写入和哈希工具。

验收：构造故意泄漏的 handoff 时测试必须失败；非法状态跳转必须拒绝。

### PR-B：V4 frozen 导入

- 从当前 V4 复制必要 seed、public shell、evaluator、scoring 和 Gold。
- 生成 provenance 与内容哈希。
- 删除运行时缓存和构建产物，但不得删来源中的任何文件。
- 保持 V4 Gold 100/A、broken seed 45.5 的基线语义。

验收：在新项目中对导入 Gold/broken seed 复跑，分值和关键 family 与 frozen 记录一致。

### PR-C：P0/P1 工作流

- prepare、freeze、evaluate、review release、repair、finalize 全链路。
- P0/P1 独立不可变证据目录。
- 候选修改 public tests 不得影响正式评分。

验收：同一个合成候选可完成完整状态机；重复 finalize 不覆盖已有结果。

### PR-D：固定计划与审查目录

- 编写 `implementation_plan.md` 和私有 acceptance matrix。
- 为 V4 behavior scenario 建 review catalog。
- 建立 no-leak lint：review 模板不得含测试方法名、Gold 路径、准确代码行和 patch 片段。

验收：相同失败集合生成 byte-for-byte 相同的 review packet。

### PR-E：指标、报告与聚合

- 实现 P0/P1 比较、成本时间录入和 run report。
- 实现 run-level 榜与 model/provider/harness 聚合视图。
- 不生成单一性价比总分；提供达到阈值的成本表。

### PR-F：校准与交付

- Gold、broken seed、合成 partial、合成 regression 至少四个样本。
- Windows 路径、无 ESP-IDF、存在 ESP-IDF 三种状态有明确结果。
- 写 `IMPLEMENTATION_STATUS.md`，状态只能是 implemented/pre-freeze，不能直接 frozen。
- 输出已知限制、未完成项和下一步冻结清单。

### PR-G：Freshness authoring skeleton

- 只提交题源证据、业务设计、风险矩阵和 draft manifest。
- 不写正式 hidden/Gold，不计入 MVP 完成门槛。

## 12. 验收清单

实现者交付前必须证明：

1. 新项目位于指定同级目录；记录 V4 broken seed 与 Gold 子项目的 commit/status，记录
   真实题源项目的 `git status`；明确 `modeltest` 根目录是 non-git source tree，并用
   来源清单/哈希证明未因本轮改变。
2. 候选 handoff 只含 allowlist，自动扫描无 private/hidden/Gold/review 泄漏。
3. V4 Gold 与 broken seed 基线复现。
4. P0 评分后即使 P1 修改同一工作树，P0 diff、snapshot 和结果仍保持不变。
5. review packet 由冻结 catalog 确定性生成，且只描述症状和验证边界。
6. P1 能识别解决、未解决和新引入回归。
7. 费用未知时保存 null；缓存、输入、输出和估算/实付分开。
8. 同一模型的两次运行能聚合出 best/worst/range/family pass rate。
9. 任一 reset/clean 路径都经过根目录 guard，无法触及父目录和来源项目。
10. 全部自动化测试通过，README 给出从 prepare 到 finalize 的 PowerShell 示例。

## 13. 给实现者的最终输出要求

实现者应直接在 `E:\Desktop\mytests\modeltest-planexec` 落地，不要只写建议。结束时提交：

- 变更摘要与目录地图；
- 实际执行过的测试和输出摘要；
- V4 Gold/broken seed 一致性结果；
- 一次完整合成 P0 -> review -> P1 演示的 run ID；
- 未完成或需要设计方裁决的事项；
- V4 broken seed、V4 Gold 和真实题源项目的 commit/status，以及 `modeltest` 根目录
  non-git source tree 的来源哈希说明，证明没有修改来源。

不要自行宣布正式冻结。完成后由设计方进行第二轮代码审查、边界审计和首次真实候选
校准，再决定是否标记 `1.0 frozen`。
