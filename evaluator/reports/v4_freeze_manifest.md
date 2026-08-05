# Project2 V4.0 Freeze Manifest

**Frozen:** 2026-07-11  
**Status:** V4.0 frozen  
**Canonical scoreboard:** `evaluator/reports/v4_scoreboard.md`  
**Gold verification:** `evaluator/results/20260711_222515`

本清单是 V4.0 正式成绩、元数据和冻结实现的规范入口。历史 result 保持原样；
其中 5 个 result 的原始 `meta.json` 为空，下面的 canonical meta 来自对应人工 review，
不回填旧目录，也不把事后规范化伪装成原始采集。

**2026-07-18 勘误：** Composer-2.5 的 channel/harness 曾误记为 `cursor`；实际全程在
**Grok Build CLI** 运行。已统一改为 `grok-cli`（含 scoreboard、reviews 文件名、result meta）。
Ability/Ship 数值未改。

## 1. Formal Results

`Delta = final Ability - recalculated machine Ability`。机器分使用修复 F11
模板误判后的当前 scorer 重算；所有差值均在冻结回滚线 `±5` 内。

| Result | Canonical model | Channel | Harness | Meta source | Recalculated machine | Final Ability / Ship | Class | Delta | F9 evidence |
|---|---|---|---|---|---:|---:|---|---:|---|
| `20260711_214016` | gpt-5.6-sol | codex | codex | result meta | 96 | 99 / 99 | A | +3 | `operator_attested_legacy` |
| `20260711_182425` | composer-2.5 | grok-cli | grok-cli | review canonicalization | 89 | 92 / 92 | B+ | +3 | `operator_attested_legacy` |
| `20260711_193355` | minimax-m3 | workbuddy | workbuddy | review canonicalization | 82 | 84 / 84 | B | +2 | `operator_attested_legacy` |
| `20260711_210538` | grok-4.5 | grok-cli | grok-cli | result meta | 79 | 82 / 82 | B | +3 | `operator_attested_legacy` |
| `20260711_190659` | glm-5.2 | workbuddy | workbuddy | review canonicalization | 78 | 81 / 81 | B | +3 | `operator_attested_legacy` |
| `20260711_204201` | glm-5.2 | qoder | qoder | review canonicalization | 79 | 81 / 81 | B | +2 | `operator_attested_legacy` |
| `20260711_195139` | minimax-m2.7 | qoder | qoder | review canonicalization | 62 / Ship 60 | 61 / 60 | D | -1 | `reported_failure_no_success_credit` |

### Evidence policy

- `operator_attested_legacy`：首轮运行时由操作者、PR 和共享 build 目录共同确认真实构建，
  但 bin 未随 result 归档；共享目录后来被覆盖，因此不得称为 result-local 可复现证据。
- `reported_failure_no_success_credit`：候选明确记录构建失败，F9 未获得成功满分。
- 自本冻结起，正式 F9=6 只接受本次 result 内的 `espidf_build.log`、
  `espidf_build_evidence.json` 和归档 bin（含 SHA256/size）。
- 原始 review 是人工终裁依据；本清单只规范元数据、修复后草稿和证据等级，不改写历史 review。

## 2. Gold Gate

| Field | Frozen value |
|---|---|
| Gold tree | `archives/v4_gold/project2_task` |
| Git commit | `6da2be71869b43b87f402c5d0fd7ed7513eebe27` |
| Working tree | clean |
| Direct verification result | `20260711_222515` |
| Meta | `gpt-5.6-sol-gold / gold / local`（complete） |
| public / probe | pass / pass |
| hidden / static | 45/45 / 9/9 |
| F9 | `real_pass` |
| Ability / Ship / Class | 100 / 100 / A |
| Behavior blockers | `[]` |
| Archived firmware | `espidf_build_artifacts/stdpro.bin` |
| Firmware size | 980944 bytes |
| Firmware SHA256 | `b22c89e82c7b0159dec28c0571ad954ece2f1b89c346faa7ce2ad7ce8f219959` |

Gold 的 log、manifest、bin、大小和哈希均位于同一 result，已复算一致。该验证直接针对
归档 Gold 树，不依赖当时的 live workspace。

## 3. Frozen Implementation Hashes

| Path | SHA256 |
|---|---|
| `evaluator/scoring/rubric.md` | `e19dd768612c02509acc700ad6f434ac00a4b96c02af4d4dc537aee9545f0bb4` |
| `evaluator/scoring/reviewer_prompt.md` | `95d86076cf16059cd0afd8f0fd5ec68230e94def08d868e32fd8f102d9837950` |
| `evaluator/scoring/item_registry.json` | `42764a59230112cfb8319de8c6295485111a62ace407d47c86e364d7beaeb3a0` |
| `evaluator/scoring/score_model.py` | `752f4b3314300f3aae6f44da70659234ab256638392c0ed294e55b45d90f5bcc` |
| `evaluator/run_full_eval.py` | `efc5dbba5759553539962f55ed25c9f5a9e0aa32a70b7add7d406e0cd54568a6` |
| `evaluator/run_espidf_build.py` | `c7440a90a93f9e9fc21fb51f4efb7b54aa8353efb47591055024f65dd7776adc` |
| `evaluator/run_hidden_tests.py` | `887e83d7fbf413b0eefc37ceec27b64b61be23d403c639741c1f3e3e6190c3a0` |
| `evaluator/run_espidf_static_tests.py` | `14e180ec2c9ff477aecd7bda5ee8939d012d75357b8cf4d07b3a45dd10dd7512` |
| `evaluator/prepare_candidate_handoff.py` | `359c5c104e60e8917db622de0b1880305ad0d3c73a5c4a917d2d90fb615f4709` |
| `evaluator/tests/test_score_model.py` | `ead7b3f086f9c69f2c851cc84b1b1a68465fdebb7d2595435f1c4ce327d9796b` |
| `evaluator/tests/hidden/test_auth_boundary.py` | `2207153e761ad3da6d34439a3956f520ff4b3fe835f150d9bcbabf4ac0e201e4` |
| `evaluator/tests/hidden/test_context_policy.py` | `7d1557567b6d03dc1abe71a82447fd4178b3433e4bbd67cdeebc87efd8f0cec1` |
| `evaluator/tests/hidden/test_db_migration.py` | `e4e11a00fa447d643949424d3ed450b2105795cc2a2b83eea8299b3edecc9317` |
| `evaluator/tests/hidden/test_sleep_import.py` | `5168f02c53c93d004b78f8bc1a7af9b7e6c4270f2c612ca36097cb556ed8e539` |
| `evaluator/tests/hidden/test_voice_bridge.py` | `54ac8030b0fd7c51a0d44682b5010d416951e47e267ae74ea2c898bdb729790c` |
| `evaluator/tests/espidf_static/test_espidf_static_contract.py` | `84dff7ae3a0d9017095e4ba327b91c7f296fc3a7888fbdf6535ce16bf6760722` |

这些文件发生实质变化时应视为 V4.1+，重新跑 Gold gate，并评估是否需要重跑校准锚点。

2026-07-11 文档归档后，`rubric.md` 仅更新了历史设计说明的链接路径；评分内容、
registry、scorer 和测试均未改变，因此同步哈希但不提升版本。

## 4. Candidate Boundary

候选投放必须由 `evaluator/prepare_candidate_handoff.py` 创建项目外的新目录。顶层白名单仅为：

- `ONBOARDING_TODO.md`
- `reference/`
- `tests/`
- `tools/`
- `project2_task/`

live `workspace/terminals/` 中的历史日志继续保留，但不属于正式 handoff。`mcps/`、
`terminals/`、`evaluator/`、根 `docs/`、`archives/` 均不得进入候选工作区。
脚本还会拒绝包含多提交、额外 ref、非 HEAD reflog 或 unreachable Git object 的项目，
并在复制前完成审计，避免被 reset 隐藏的历史答案随 `.git` 进入候选包。

## 5. Freeze Decision

- Gold gate：PASS
- 7 个正式样本修复后草稿与终裁差：PASS（范围 -1 至 +3）
- 100 分 registry / scorer 口径：PASS
- behavior / semantic-only blocker 隔离：PASS
- result-local F9 新证据链：PASS
- F9 log/bin/size/SHA256 硬校验：PASS
- 正式 meta 强制：PASS（`--require-meta`）
- 候选 handoff 隔离：PASS

结论：**Project2 V4.0 可以冻结。**
