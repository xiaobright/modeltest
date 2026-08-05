# PlanExec Control-Plane Reliability 场景实施交接

**状态：** Draft for implementation  
**目标项目：** `E:\Desktop\mytests\modeltest-planexec`  
**建议实施者：** GPT-5.6 Luna high  
**基底提交：** `92b5398`  
**新场景 ID：** `control-plane-reliability`  
**赛道：** `plan_repair_capstone`，与 `v4-plan-replay` 分榜

> 本场景取材于 PlanExec 框架首次实现与返修中真实出现的缺陷。它测试给定完整计划后的
> Python 控制面、证据链、状态机和经济口径执行能力，不测试模型能否猜到需求。

## 1. 要回答的问题

1. 模型能否在多阶段工作流中保持来源、版本和证据不可变？
2. 模型能否隔离 official/calibration，避免 Gold 或 synthetic 证据污染正式结果？
3. 模型能否把计时起点放在真实业务事件，而不是方便编码的位置？
4. 模型能否正确处理 P0/P1 累计成本、首次达标、null/0 和计划摊销？
5. 模型能否同时关闭生产 bug、测试 fixture、报告与聚合，而不是局部改绿？

该场景是独立 capstone。不得与 V4 Plan Replay Ability 相加，也不得用来重算任何历史
成绩。

## 2. 本轮实施范围

### 2.1 必须完成

- 将现有 workflow 从 V4 硬编码改为最小 manifest-driven scenario adapter。
- 保持 `v4-plan-replay` 行为、分值、Gold 和现有结果解释不变。
- 新建一个小型、纯 Python、无外部服务的 candidate seed。
- 新建固定实施计划、public smoke、private hidden、item registry、review catalog 和 Gold。
- 新场景覆盖 evidence、mode isolation、state/timing、economics、aggregate/report。
- 新增 broken、Gold、两种 partial 和 regression 校准。
- full evaluation 在普通 host 环境可重复运行，目标单次不超过 60 秒。
- 输出独立 scoreboard/report，不进入 V4 Plan Replay aggregate。

### 2.2 非目标

- 不加入 ESP-IDF、QEMU、Docker、数据库服务或网络 provider。
- 不把当前 `modeltest-planexec` 整仓直接交给候选。
- 不让候选看到当前实现 commit、P0/P1 review、Gold diff 或 hidden tests。
- 不重写现有 workflow 为大型插件框架；只增加第二场景所需的最小适配层。
- 不删除旧 runs、reports 或外部 handoff。
- 不在本轮运行真实候选或宣布 frozen。

## 3. 为什么使用独立场景

这组问题与 Project2 业务代码不同：它主要考 Python 基础设施、生命周期和证据真实性。
若混入 V4 Plan Replay 总分，会同时改变题域、权重和历史解释。正确结构是：

```text
v4-plan-replay
  测固定规划下的真实 Project2 修复执行

control-plane-reliability
  测固定规划下的控制面/证据链 capstone
```

模型可分别报告两条成绩。只有 V4 Plan Replay 达到预设门槛的模型才需要运行 capstone，
以控制成本。

## 4. 最小多场景适配

现有代码仍隐含 `project2_task`、V4 evaluator 和 benchmark 名称。新增场景前先建立以下
最小契约。

### 4.1 Manifest 新字段

每个场景至少声明：

```json
{
  "scenario_id": "control-plane-reliability",
  "scenario_version": "0.1.0-calibrating",
  "status": "draft|calibrating|frozen|retired",
  "track": "plan_repair_capstone",
  "candidate_project_relpath": "flowbench_task",
  "evaluation_driver": "evaluator/scenario_driver.py",
  "score_contract_version": "1.0",
  "thresholds": {"b_plus": 90, "a": 95}
}
```

所有 scenario/public/private/evaluator/scoring/Gold 哈希仍进入 run control snapshot。

### 4.2 标准 stage score contract

场景 driver 接收 candidate project、results 目录和 meta，写出统一结构：

```json
{
  "ability_draft": 0,
  "ship_draft": 0,
  "release_class_hint": "D",
  "family_draft": {},
  "behavior_blockers": [],
  "semantic_only_codes": [],
  "item_results": []
}
```

`generate_review_packet.py`、`finalize_run.py` 和 aggregate 只依赖该标准结构，不依赖 V4
测试文件名。V4 可保留自己的 driver，但公共 workflow 不得按 scenario ID 写分支。

### 4.3 回归要求

- V4 broken 仍为 45.5。
- V4 Gold 无 build 仍为 97；有真实 build 仍为 100/A。
- V4 review catalog、no-repair 和 economics 结果不突变。
- 现有 finalized run 不迁移、不改写。

## 5. Candidate seed

### 5.1 形态

创建一个约 500-1000 行的纯 Python 小项目 `flowbench_task`：

```text
flowbench_task/
  flowbench/
    paths.py
    state.py
    artifacts.py
    prepare.py
    freeze.py
    review.py
    economics.py
    aggregate.py
  fixtures/
    public_packet/
    candidate_seed/
    calibration_gold/
  README.md
  CHANGE_REQUEST.md
  PULL_REQUEST_TEMPLATE.md
```

它模拟一个两阶段发布检查器，不包含 Project2、ESP 或当前 evaluator 的完整实现。public
smoke 在 broken seed 上通过；严格语义由 hidden mutation tests 验证。

### 5.2 Broken seed 保留的真实缺陷模式

seed 应自然呈现以下问题，但不要用 `BUG_1`、`TODO_FOR_TEST` 等标签暴露答案：

- manifest 记录 hash，但 prepare 不重算；
- 内容树 hash 受 `.git` 内部状态影响；
- official CLI 可以选择 calibration Gold；
- calibration workspace 与 official handoff 共用根；
- snapshot hash 写入后，evaluate 不重新验证；
- review 只读 raw test failure，漏 heuristic scored item；
- no-findings 仍强制 P1；
- P1 计时从 freeze 才开始；
- P0 threshold cost 使用最终全流程 total；
- null 与 verified zero 混淆；
- default aggregate 混入 calibration；
- 状态文档仍显示旧 calibration 数字。

这些缺陷来自真实实现历史，但 seed 需重新整理为自包含代码，不能复制 candidate 可通过
Git 历史恢复的修复提交。

### 5.3 Git 与泄漏边界

- candidate seed 只保留一个 commit，无 tags/reflog/unreachable Gold。
- Gold 位于 private control plane，永不经过 official handoff。
- 公开计划可以描述所有行为要求，但不得包含当前项目路径、commit 或 patch。

## 6. 固定公开计划

候选计划按依赖顺序明确以下工作包：

1. 内容 hash、Git commit/status 与 runtime metadata 分层。
2. 完整 public packet、seed、driver、scoring、catalog 的版本化和 prepare fail-closed。
3. official/calibration 路径和 CLI 模式隔离。
4. P0/P1 snapshot、evaluation artifact 与 control snapshot 的不可变验证。
5. scored item 作为 review/attribution 唯一来源，catalog 完整性和 deterministic packet。
6. no-repair 状态分支与 packet 可见位置。
7. review 发布、repair freeze、operator override 的计时边界。
8. phase/stage usage、P0/P1 cumulative、首次达标、plan one-off/amortized。
9. official/calibration aggregate、重复运行、报告真值与异常恢复。
10. 回归测试、状态文档和诚实 PR 报告。

每个工作包写目标、涉及模块、依赖和行为验收，不给函数实现、测试方法名或准确代码行。
正式候选不提供内容答疑；遇到局部设计选择应记录假设并继续。

## 7. 评分设计（100 分）

### F1 Process And Truthful Report：8

| Item | 分值 | 行为 |
|---|---:|---|
| baseline/final checks | 2 | 记录初始与最终 public/self-test |
| changed scope | 2 | 修改范围与 diff 一致 |
| evidence claims | 2 | 不谎称 hash、隔离或恢复验证 |
| no test tamper | 2 | 不修改候选可见测试制造 pass |

### F2 Official/Calibration Isolation：16

| Item | 分值 | 行为 |
|---|---:|---|
| official rejects Gold | 5 | official 无法选择或复制 Gold |
| calibration stays internal | 4 | calibration workspace 仅在 control plane |
| handoff content isolation | 4 | official handoff 无 private/Gold/hidden |
| aggregate isolation | 3 | default report 只含 official |

### F3 Scenario And Control Provenance：16

| Item | 分值 | 行为 |
|---|---:|---|
| content hash ignores Git internals | 2 | `.git` 变化不改变内容 hash |
| source content mutation detected | 4 | 代码/seed 改动使 prepare fail closed |
| complete public packet hash | 3 | task/plan/reference/tests/tools 均受保护 |
| control snapshot bound to run | 3 | driver/scoring/catalog/manifest 固化 |
| per-stage control verification | 4 | evaluate/review/finalize 均验证 |

### F4 Stage Evidence Integrity：16

| Item | 分值 | 行为 |
|---|---:|---|
| snapshot mutation rejected | 4 | freeze 后改代码，evaluate 拒绝 |
| evaluation mutation rejected | 4 | result 改动，finalize 拒绝 |
| legal state transitions | 3 | 跳步、回退和重复覆盖被拒绝 |
| P0/P1 independence | 3 | P1 不覆盖 P0 证据 |
| path containment | 2 | run_id/path traversal 不能越界 |

### F5 Review And Repair Attribution：14

| Item | 分值 | 行为 |
|---|---:|---|
| canonical scored-item source | 3 | review 不依赖 raw test 偶然结构 |
| catalog coverage | 3 | 正分 scenario 全覆盖并分类 |
| deterministic visible packet | 3 | 同失败集同正文，packet 在 workspace |
| no-repair branch | 3 | 无 finding 时 P1=not_required、成本为 0 |
| heuristic regression | 2 | 非 unittest item 退化也能归因 |

### F6 Timing And Economics：20

| Item | 分值 | 行为 |
|---|---:|---|
| repair timing boundary | 4 | review 发布到 P1 freeze |
| measured/operator separation | 3 | 自动值不覆盖手填值 |
| phase/stage usage | 2 | P0/review/P1/evaluator 独立 |
| P0/P1 cumulative | 4 | 未来阶段不倒灌 P0 |
| first threshold cost | 3 | B+/A 取首次达到阶段 |
| plan one-off/amortized | 2 | operational 与计划成本分开 |
| null vs zero | 2 | 未知不伪装为免费 |

### F7 Aggregate, Recovery And Docs：10

| Item | 分值 | 行为 |
|---|---:|---|
| rerunnable calibration | 2 | 重复运行不撞固定 ID |
| run identity/concurrency | 2 | 同秒运行仍唯一 |
| interrupted-run recovery | 2 | 半完成状态可安全恢复或明确 abort |
| report from structured truth | 2 | 报告不保留旧数字 |
| operator/docs completeness | 2 | no-repair、usage、限制写清 |

## 8. Ship Blockers

Ability 按 item 累加；Ship/Class 单独表达发布风险：

| Blocker | 条件 | Ship/Class |
|---|---|---|
| `T-gold-leak` | official 可获得 Gold/private | Ship max 60，Class D |
| `T-path-escape` | candidate/run 路径可越界 | Ship max 60，Class D |
| `T-evidence-tamper` | snapshot/result 篡改仍被接受 | Ship max 70，Class D |
| `T-control-drift` | 同版本使用漂移 driver/scoring | Ship max 78，Class C |
| `M-economics` | 首次达标或累计成本错误 | Class B+ 或更低，不做 Ability 硬墙 |
| `R-state` | 状态跳转/覆盖不安全 | Class B 或更低 |

每个 blocker 仍只扣对应 item 分。不得用 hard cap 抹平其余完成量。

## 9. Hidden Oracle

hidden tests 使用临时目录、fake clock 和最小 fixture，按行为拆分：

- 改 `.git/logs` 与改源码得到不同预期；
- 修改 task/reference/driver/scoring/catalog 后分别验证正确 gate；
- official + Gold 参数、calibration 路径、相邻 handoff 扫描；
- freeze 后 mutation、evaluation artifact mutation、P0/P1 hash 独立；
- raw test 全过但 heuristic item 失败；
- no-findings packet 与 P1 not-required；
- fake clock 验证 review release -> freeze 的时间；
- operator wall time 不被 measured 覆盖；
- 示例成本：plan=10、P0=1、eval0=2、review=3、P1=4、eval1=5；
  P0 Ability=91、P1=95 时，B+ 成本应停在 P0，A 成本到 P1；
- unknown、verified zero、provider-native only、actual/estimate 混合；
- calibration 默认不进 official aggregate；
- 中途写出部分 artifact 后的 resume/abort 行为；
- 状态报告与结构化结果不一致时扣 report item。

测试不得依赖唯一函数名或要求候选复制当前 PlanExec 结构。一个根因造成多个场景不可达时
仍按可独立 fixture 测试，避免新的 0/20 双峰。

## 10. Review Catalog

每个正分 scenario 必须有 catalog entry：

- `candidate_fixable`：进入 P1 packet；
- `environment`：只记录，不要求候选修；
- `evaluator`：标记 run 非可比；
- `not_reviewable`：例如明确 test tamper，只保留信任记录。

finding 只描述症状和验证边界，不写 hidden test 名、准确行号或 patch。packet 正文不得含
run_id/time/path，确定性以正文 SHA-256 验证。

## 11. 校准矩阵

至少构造：

1. **Broken seed**：public 绿，严格分建议 35-60，存在 Gold/evidence/economics blocker。
2. **Gold**：100/A；no-repair；重复运行 byte-stable（时间字段除外）。
3. **Integrity partial**：hash/snapshot 正确，但 economics 错，Ability 约 70-85。
4. **Economics partial**：成本正确但 official 泄漏 Gold，Ability 可较高，Ship 60/D。
5. **Regression**：从 Gold 破坏 report heuristic 或 timing，必须准确列出 item。

分数区间是校准目标，不得为了命中数字修改行为 oracle。若 broken/partial 聚集，再调整独立
item，而不是新增 hard cap。

## 12. 实施顺序

### PR-A：保护现有主线

- 从 `92b5398` 建工作分支并记录 baseline。
- 为 V4 broken/Gold/no-repair/economics 建回归测试。
- 禁止改写现有 finalized runs。

### PR-B：Manifest Driver

- candidate project relpath 不再硬编码。
- 新增标准 stage score contract 与 manifest driver。
- V4 迁移到 driver 后结果必须完全一致。

### PR-C：新 seed/public shell

- 建立小型 flowbench seed、单 commit Git、public task/plan/reference/smoke。
- 建立 Gold，但不进入 candidate handoff。

### PR-D：Hidden/Scoring/Review

- 落地 F1-F7 registry、mutation tests、blockers 和 catalog。
- 自动检查 registry/catalog 100% 覆盖。

### PR-E：Calibration

- 跑 broken、Gold、两种 partial、regression。
- 生成独立 `control_plane_scoreboard.md` 和 calibration report。

### PR-F：Pre-freeze Audit

- handoff leak scan、hash drift、snapshot/result tamper、重复运行、路径 guard。
- 更新状态为 implemented / pre-freeze，不宣布 frozen。

## 13. 验收标准

1. 现有 9 项 PlanExec tests 与新增 tests 全过。
2. V4 Plan Replay broken/Gold 分数和 report 不变。
3. 新场景 Gold 100/A，broken/partial 有可解释梯度。
4. 新场景单次 full eval 在普通 host 下目标 <=60 秒。
5. official/calibration、private/public 和 P0/P1 物理与逻辑隔离均通过。
6. registry/catalog 无遗漏；review packet deterministic 且不剧透。
7. fake-clock economics/timing 全部通过。
8. interrupted run 不产生可误认的 finalized 结果。
9. source 项目与真实题源项目无新增修改。
10. Git clean，提交 hash、测试命令、校准 run IDs 和未决项写入状态报告。

## 14. 给 Luna 的执行要求

- 直接在 `E:\Desktop\mytests\modeltest-planexec` 实施，不只写建议。
- 不删除任何历史 handoff、run、report 或 archive。
- 不修改 `E:\Desktop\mytests\modeltest` 与 `E:\Desktop\myproject\project`。
- 实现细节有多种合理选择时按本文不变量自行决定并记录，不等待内容答疑。
- 若 manifest driver 会迫使 V4 结果变化，停止该部分并保留证据，不用兼容 hack 掩盖。
- 完成后提交 commit，状态保持 implemented / pre-freeze，等待设计方复审。
