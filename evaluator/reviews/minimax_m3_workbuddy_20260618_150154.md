# Minimax M3 (WorkBuddy, medium thinking) Evaluation - 2026-06-18

Result directory: `evaluator/results/20260618_150154`

Final strict/cap score: **82 / 100**

Soft-cap entertainment score: **84.0 / 100**

Channel note: this was run in WorkBuddy with the visible/default thinking budget shown as **medium**. Treat the result as a WorkBuddy medium-budget channel sample rather than a clean full-strength API baseline. It is still a materially stronger WorkBuddy submission than the Kimi K2.6 WorkBuddy run.

Cost/channel note: this run cost about **900 points** despite a low visible **0.25x** multiplier. Normalized by multiplier, its rough base usage is `900 / 0.25 = 3600` units, about **5x** the Kimi K2.6 WorkBuddy base usage (`~714`). The low unit multiplier therefore did not translate into low total cost; M3 expanded the work much more aggressively.

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 27 / 34 passed, 7 failed, 0 errors.
- ESP-IDF static tests: 6 / 8 passed.
- Changed files: 25.
- PR template: present, detailed, and passes process-contract checks.
- Real ESP-IDF build: candidate report records `Project build complete`; this review did not independently rerun the WSL build and the user did not separately confirm the build for this scoring turn.

## Score Breakdown

- Debug process and reporting: 9 / 10
- Admin/auth boundary: 13 / 14
- Session/context policy: 9 / 14
- care_event full chain: 13 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 12 / 14
- DB migration compatibility: 5 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 5 / 6
- Docs and maintainability: 4 / 4

Subtotal: 86 / 100

Cap applied: sensitive targeted context can still be authorized without an explicit request `session_id` by falling back to `get_current_session()` when the ambient session is already authenticated. The privacy cap limits the final strict score to **82 / 100**.

## Strengths

The visible workflow is complete. Public tests and the debug probe pass, and the PR report is detailed enough to reconstruct the initial failures, changed files, verification path, ESP-IDF build claim, and residual risks.

The care-event implementation is substantially better than the WorkBuddy Kimi K2.6 run. Hidden care-event tests pass 5 / 6: admin write gate, fresh-schema CRUD, room/bed filtering, case normalization, limit, and descending order are all handled. The remaining care-event failure is caused by the broader context/session policy leak, not by missing CRUD or HTTP route work.

Sleep CSV ownership is fully solved. Explicit room/bed, configured default bed, unscoped `first`, explicit `all`, and `skip` all pass.

The ESP32-S3 work is broad and structured. It splits protocol packet helpers, MaixSense parsing, NVS device config, MQTT payload construction, and network backhaul into separate modules, preserves USB CDC, and adds ToF/MLX MQTT mirroring with lowercase `tof1/tof2/mlx1/mlx2` topics and `payload_b64` JSON. The static score is only 6 / 8, but this is real implementation work, not keyword padding.

The old-database migration path is improved compared with the earlier Minimax M3 Opencode/API result. It no longer crashes before migration. Missing columns are added before indexes are created.

## Main Failures

The high-impact privacy bug remains. `build_chat_context_v3()` still calls `get_current_session()` when no explicit `session_id` is supplied. It only clears the ambient session if that ambient session is not authenticated. If the previous/current session is valid, a targeted patient-context request without explicit `session_id` can still become authorized. This is the release-blocking issue and the reason for the 82 cap.

Several hidden failures are reason-code compatibility failures. The code returns strings such as `not_authenticated:identity_unknown`, `not_authenticated:expired`, and `not_authenticated:no_session`, while the contract expects `not_authenticated`. It also classifies a no-actor session as `not_authenticated:no_actor` instead of `not_authorized_for_target`. These are less dangerous than data leaks, but they are still API contract mismatches.

Old database migration is incomplete. The migration adds the new `ts` column, but it leaves old rows at `ts = 0` instead of backfilling from `created_ts`. Hidden migration fails with `0 not greater than 0`. This is a fidelity bug rather than a startup-crash bug, so it is not as severe as the earlier M3 result, but it still breaks old-data ordering/metadata expectations.

ESP static misses two contract points. The active `idf_component.yml` no longer declares `espressif/mqtt` because the submission vendors `components/mqtt` into the tree, and the static readiness check does not recognize the readiness helper because it is moved into `device_config.cpp` as `network_config_complete()`. The vendoring choice may help offline builds, but it is noisy and deviates from the benchmark's expected managed-component shape.

The PR template is mostly useful but a little too confident. It claims the sensitive context and legacy migration behavior are fully handled; hidden evidence shows the ambient-session privacy bug and `ts` backfill gap remain.

## Comparison

Compared with **Minimax M3 Opencode/API**, this WorkBuddy medium-budget run is a tradeoff rather than a clean win or loss. It has worse hidden count, mostly because of exact reason-code mismatches, but it improves the old-DB migration from a crash-class failure to a timestamp-fidelity failure. The ESP shape is similarly broad but still not statically clean.

Compared with **Kimi K2.6 WorkBuddy**, this is clearly stronger final code. Both runs show 27 / 34 hidden and 6 / 8 ESP static, but Kimi misses more of the care-event/API/context/migration chain. M3's failures are more concentrated in context policy, reason-code exactness, and migration fidelity.

Compared with the best 82-cluster runs, it still sits below GLM-5.1 Qoder, Kimi K2.7 Code, Mimo v2.5 Pro, and DeepSeek V4 Flash because those runs either had cleaner ESP static/build evidence, stronger hidden totals, or better migration/report shape.

## Judgment

Record the strict score as **82 / 100**. The model clears the upper-middle threshold and is not merely a public-test patch. The privacy cap is deserved, though: the explicit-session boundary is exactly the kind of realistic security bug this benchmark is meant to catch.

For the entertainment soft-cap ranking, I would put it at **84.0 / 100**. Once reason-code mismatches are treated as smaller compatibility deductions rather than full hidden-test equivalents, this run separates itself from the 78-80 group, but the remaining sensitive-context leak, `ts` migration fidelity bug, and ESP component-shape issue keep it below the stronger 85-88 entertainment results.
