# V4 Gold Verification

## Meta
- result_id: `20260711_214920`
- artifact status: historical live result removed after freeze cleanup; exact artifact copy retained at `archives/v4_gold/verification_20260711_214920/`
- model: gpt-5.6-sol-gold
- channel/harness: gold / local
- tree: `archives/v4_gold/project2_task`（评测时用 workspace 同内容 + 保留 broken-seed git baseline）
- base: gpt-5.6-sol `20260711_214016` + F12 reason 一行级修复

## Evidence
- public / debug_probe / hidden / static: **all pass**
- hidden: **45 / 45**
- static: **9 / 9**
- ability_draft / ship_draft: **97.0 / 97.0**
- class: **A**
- behavior_blockers: **[]**
- f9_mode: skipped_env（F9=3 机器分；历史 Codex bin 可人工记 real_pass → Ability **100**）

## Gate
- Ability ≥ 95: **PASS (97)**
- Class A: **PASS**
- no behavior blockers: **PASS**

## Note
Gold 是冻结自检标准，不是参赛样本。本次运行已由最终 result
`20260711_222515`（真实 build、100/A）替代；本文件仅保留历史审计说明。
