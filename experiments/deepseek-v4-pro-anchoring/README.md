# DeepSeek V4 Pro First-request Tool-schema Anchoring

**独立复现者：** [@NineThoughts0521](https://github.com/NineThoughts0521) · **证据角色：** 面向 `xiaobright/modeltest` 的第三方独立复现；本目录的 runs 不并入维护者原有 formal `n`、排名、worst、均值或样本索引。

本目录保存 Project2 V4.1b 独立复现、Minimal-Full full-task 消融、OpenCode exploratory harness comparison 的预注册、运行器与可公开派生证据。结果见 [`RESULTS.md`](./RESULTS.md)，机器可读汇总见 [`artifacts/comparison.json`](./artifacts/comparison.json)。

本阶段按固定顺序串行完成 Project2 Anchored、Project2 Standard、Project2 Minimal-Full。原 OpenCode 正式枪因外层进程生命周期中断而保留为不计分 partial；经批准后只修复 detached/background 生命周期并完成一次 replacement。DeepSWE pair 与 Terminal-Bench 均未在本阶段执行。

Project2 evaluator 保留 public/debug/hidden/ESP static 与 frozen scorer，但省略 optional real ESP-IDF build，因此四个有效结果的 F9 均按 frozen scorer 的 `skipped_env` 计 3/6。比较使用原始 Ability/Ship/Class，不构造调整分数。DSH 三枪属于机制消融；OpenCode replacement 仅作 post-preregistered exploratory comparison。

`private/` 和 `jobs/` 只保存在本机且被 Git 忽略。Git 中只保留预注册、runner、原 verifier 的可公开结果、派生统计、工具目录快照与原始证据 SHA-256；完整 reasoning、session JSONL、credential 和私人绝对路径不进入 Git。哈希索引由 `scripts/build_evidence_manifest.py` 零成本生成。
