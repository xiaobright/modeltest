# PlanExec Luna P0 实现审查

**审查日期：** 2026-07-13  
**被审项目：** `E:\Desktop\mytests\modeltest-planexec`  
**结论：** 主骨架可继续，当前为 implemented / pre-freeze；P0/P1 修复完成前不得投放真实候选。

## P0：冻结前必须修复

### 1. Gold 被复制进正式 handoff 根

`prepare_run.py --synthetic-source gold` 会把完整 Gold 复制到与真实候选相同的外部 handoff
根。当前已经存在：

- `E:\Desktop\mytests\modeltest_planexec_handoffs\synthetic_gold\workspace\project2_task`
- `E:\Desktop\mytests\modeltest_planexec_handoffs\smoke_gold2\workspace\project2_task`
- `E:\Desktop\mytests\modeltest_planexec_handoffs\gold_build_verify\workspace\project2_task`

MVP 明确不是 OS sandbox，后续候选若越过提示边界搜索相邻目录即可读到 Gold。正式
prepare CLI 也允许操作者误带 `--synthetic-source gold`。

必须改为：

- Gold/broken/synthetic 校准只在 control plane 内运行，不经过正式 handoff 根；
- 正式 prepare 不暴露 Gold source 选项；如保留校准入口，使用独立命令和强制
  `run_kind=calibration`，且目标必须位于 control plane；
- aggregate 默认排除 calibration；
- 对现有外部 Gold handoff 只列清理清单，未经用户逐路径确认不得删除。

### 2. Scenario 哈希只记录、不验证，且当前 seed 哈希已经漂移

prepare 只检查 manifest 哈希字段非空，没有重算 seed、plan、catalog、evaluator、scoring
并比对。evaluate/review/finalize 又直接读取当前 scenario private 文件，因此同一 run 在
不同阶段可能使用不同 evaluator/catalog。

实测 manifest `seed_sha256` 为：

```text
a1b92bdd7c0be199e6f4e415ca19ff423e6c39a4d0b6dae6854c8351ca435baf
```

当前重算为：

```text
cac9df1be4c234ae03f5e6736a8e1a2b5bffe1760511d76248ea55a0d72e7d9d
```

原因之一是 `sha256_tree()` 把 `.git` 纳入内容哈希，而 Git audit/status 本身可能更新 Git
内部文件。工作树 clean 也会导致 tree hash 漂移。

必须改为：

- 内容树哈希排除 `.git`，Git commit/status 作为独立证据；
- prepare 前重算全部 manifest 哈希并 fail closed；
- 每个 run 固化 evaluator/scoring/catalog，或在每一阶段重算并与 run manifest 比对；
- evaluate 前重算 snapshot 内容哈希，finalize 前验证 evaluation manifest；
- 添加篡改 seed/plan/catalog/snapshot 后必须拒绝的自动测试。

## P1：首个真实候选前修复

### 3. 缺少分阶段时间与费用，无法回答实验主问题

`record_usage.py` 只有整次 run 的平铺 usage，没有 P0 implementation、review delivery、P1
repair、evaluator/build 和 plan authoring 的独立时间/费用/token/cache。状态机在 freeze
时才自动进入 active，也没有可靠的阶段开始时间。

必须增加：

- `run_kind=calibration|official`；
- plan/P0/review/P1/evaluator 分阶段 usage；
- wall time 与 active model time；
- 实付、估算、积分及换算公式分字段，未知保持 null；
- final report/aggregate 的 total、达到 B+/A 的成本和一次性/摊销计划成本。

### 4. P0/P1 快照是逻辑只读，不是可验证不可变

freeze 复制项目并写 tree hash，但 evaluate 只读取 `snapshot.json`，没有重算项目树。冻结后
修改 snapshot，系统会评分修改后的代码，却继续引用旧 hash。evaluation 结果在 finalize
前也没有完整性复核。

必须在 evaluate/finalize 边界 fail closed，并测试：

- freeze 后改代码，evaluate 拒绝；
- evaluate 后改 summary/score artifact，finalize 拒绝；
- P1 修改 candidate workspace 不改变 P0 snapshot/evaluation hash。

### 5. Review packet 覆盖和变化归因不完整

review 只读取 hidden/static 原始失败。V4 registry 有 49 个正分 scenario，catalog 只有 30
个；缺少 19 个，包括 process、部分 auth/sleep/ESP 和 `esp_real_build`。F9/F11 等 heuristic
不会进入 review。finalize 同样只从 hidden/static 提取 item，导致 synthetic regression 中
F11 从 4 降到 0.5，却未列入 introduced regressions。

此外 packet 被写到 `<run_id>\REVIEW_PACKET.md`，而候选唯一可见根是
`<run_id>\workspace`；按当前投放规则候选看不到该文件。

必须改为：

- 以 canonical `score_draft` scored-item 状态生成 review 和 P0/P1 attribution；
- catalog 覆盖全部 candidate-fixable scored scenario，并显式标记
  `candidate_fixable|environment|evaluator|not_reviewable`；
- public/code-attributable build/report heuristic 也能生成 finding；环境缺失不投放；
- packet 放入 candidate workspace 内固定位置；
- `resolved_finding_count` 与 behavior blocker 数量分开命名；
- 增加 catalog coverage、F9/F11 regression 和 packet visibility 测试。

### 6. 未实现 no-repair 分支与统一澄清规则

当前状态机强制所有 run 进入 P1，`finalize_run.py` 永远写 `repair_cycles=1`。P0 无 finding
时仍复制和评测相同 P1，制造了不存在的返修。公开 task 也没有说明正式运行不提供内容
答疑、模型必须记录假设并继续。

必须增加：

- `review_released -> p1_not_required -> finalized`；
- no-findings packet 保留，P1 引用 P0 hash/score，repair time/cost=0，不再次调用模型；
- candidate task 写明无内容答疑；环境状态在 prepare 前固化；
- 非预期题面歧义使 run non-comparable，并升级 scenario version，不临场补答案。

## P2：冻结维护项

### 7. Calibration 与正式聚合未隔离，演示不可重复运行

`aggregate_runs.py` 无条件聚合所有 final report，当前报告中的 5 个样本全部是 synthetic。
`demo_synthetic.py` 又使用固定 run ID；README 要求的验证命令第二次运行会因 run 已存在而
直接失败。

应增加 run kind 过滤；demo 使用唯一临时 ID 或实现只读验证模式。校准报告与正式榜放在
不同输出中，不删除已有证据。

### 8. 项目自身无 Git，自动测试覆盖不足

`modeltest-planexec` 根不是 Git repository，无法可靠审查 Luna P1 相对 P0 的变更。当前
自动测试仅 4 项，均通过，但没有覆盖完整 prepare/freeze/evaluate/review/finalize、哈希
漂移、Gold 隔离、分阶段 usage、no-repair 或 aggregate 过滤。

应初始化项目自身 Git 并建立 baseline commit；保留来源树为只读。补齐上述关键路径测试
后再进行真实候选校准。

## 已验证通过

- V4 broken seed：45.5。
- V4 Gold 无 build：97，F9 skipped/partial 语义正确。
- V4 Gold Windows EIM build：100/A，hidden 45/45、static 9/9，并归档固件证据。
- 四个现有 workflow unit tests 全部通过。
- V4 workspace seed、broken backup、Gold 子项目均 clean，commit 与 provenance 一致。
- 真实题源项目仍只有原有 `dependencies.lock` 修改和未跟踪 `审查结果.txt`，本轮未新增改动。
- 模型调用保持在 evaluator 外部；状态正确标为 implemented / pre-freeze，未误称 frozen。

## P1 交付验收

1. 全部 P0/P1 条目关闭或写明设计方接受的残余风险。
2. unit + integration tests 可重复运行，不依赖删除旧 run。
3. Gold 不再进入正式 handoff 根；现有 Gold handoff 清理另走用户确认流程。
4. manifest、snapshot、evaluation 篡改测试均 fail closed。
5. synthetic Gold/broken/partial/regression 校准结果仍保持 V4 语义。
6. 提供一个 no-repair 演示和一个 review 后真实改善的 synthetic 演示。
7. 提供分阶段 usage 的示例 JSON 与 aggregate 输出。
8. 不宣布 frozen；返回设计方进行第二轮审查。
