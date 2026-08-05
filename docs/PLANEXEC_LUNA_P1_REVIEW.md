# PlanExec Luna P1 二审

**日期：** 2026-07-13  
**结论：** P0 安全/完整性问题已基本关闭；完成以下两个 P1 后可进入首次 official 校准。

## P1-1：返修 wall time 计时起点错误

`freeze_stage.py` 在收到 `--stage p1` 时才调用
`mark_phase(..., "p1_repair", "start")`，随后立即复制 snapshot 并结束计时。真实模型是在
review packet 发布后、调用 freeze 之前完成返修，因此当前 `p1_repair.wall_time_sec` 只测到
snapshot copy。

现有 synthetic repair 报告中的 P1 wall time 为 4 秒，正是复制耗时，不是返修耗时。

修复要求：

- 有 selected finding 时，在 review packet 发布完成、进入 `review_released` 时启动 P1；
- P1 freeze 时结束；
- operator 手填 wall time 与自动 measured wall time 分字段，finalize 不得覆盖手填值；
- `record_usage.py` 应允许在 `p0_frozen` / `p1_frozen` 等合理的未 finalized 状态补录；
- 增加时间边界测试。

## P1-2：threshold cost 使用了错误的累计成本

`finalize_run.py` 先计算所有阶段的最终 `total`，再把同一个 total 写给 P0/P1 的 B+/A
threshold。结果是 P0 已达 B+ 时，`p0_b_plus` 仍包含后续 review/P1 repair/evaluator P1。

当前实现还把 `evaluator_p0` / `evaluator_p1` timing 临时加入 `phase_usage`，导致 total 完整性
判断要求这些 timing-only 项也提供 usage；通常最终 total 会保持 null。计划 one-off 成本也
直接计入每个 run total，而不是分别报告 one-off、operational 和 amortized。

修复要求：

- `p0_cumulative`：P0 implementation + evaluator P0；
- `p1_cumulative`：P0 cumulative + review delivery + P1 repair + evaluator P1；
- plan 分别报告 one-off 和 amortized share，不默认重复计入 operational total；
- `cost_to_b_plus` / `cost_to_a` 选择首次达到阈值的阶段及其累计成本；
- 区分 `operational`、`with_plan_one_off`、`with_plan_amortized`；
- timing-only 子阶段不得破坏 usage completeness；
- 增加“P0 达 B+、P1 才达 A”的成本单元测试。

## P2：冻结文档与场景内容哈希

1. scenario hash 当前只覆盖 `implementation_plan.md`，没有覆盖 `task.md`、reference、public
   tests/tools。应增加完整 candidate-visible public packet hash，并在 run control snapshot
   保存可复现副本。
2. README 的标准流程仍无条件要求 P1；应说明 `p1_not_required` 时直接 finalize。
3. `IMPLEMENTATION_STATUS.md` 仍写旧的 `synthetic partial: 45.5 -> 45.0`，应改为当前
   synthetic repair 91 -> 97，并区分旧 pre-fix 证据。
4. Operator guide 增加分阶段 `record_usage.py --phase ...` 示例。

## 二审已验证通过

- Git clean，7/7 unit tests 通过。
- scenario seed/plan/catalog/evaluator/scoring 五类 hash 全部匹配。
- review catalog 49/49，48 个 candidate-fixable、1 个 not-reviewable。
- snapshot/evaluation tamper fail closed。
- 新跑 Gold no-repair：97 -> 97，`repair_cycles=0`、无 P1 snapshot。
- official aggregate 为 0；calibration aggregate 与正式结果隔离。
- 新 Gold calibration workspace 位于 run control plane，没有新增外部 Gold handoff。
- V4 与真实题源项目状态没有新增修改。

修复后继续保持 implemented / pre-freeze，不宣布 frozen；二审只需复跑 unit、economics
fixture、Gold no-repair 和一次 91 -> 97 repair 即可。
