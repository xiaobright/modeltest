# GLM-5.1 (WorkBuddy) Evaluation - 2026-06-18

Result directory: `evaluator/results/20260618_000535`

Final score: **82 / 100**

Ability-only ranking score: **81.6 / 100**

Channel note: this is a WorkBuddy run of GLM-5.1. Compared with the earlier Qoder GLM-5.1 run, the tool/process behavior is clearly better: the model reached the ESP-IDF build stage before context compression, and after compression it continued the PR/reporting work normally instead of forgetting the workspace or build environment. The final submitted code, however, is not stronger than the Qoder run because it regresses old-database migration compatibility and misses one ESP static dependency marker.

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 30 / 34 passed, 3 failed, 1 error.
- ESP-IDF static tests: 7 / 8 passed.
- User-confirmed ESP-IDF build: completed successfully before final PR/report writing.
- Changed files: 14.
- PR template: present, detailed, and passes process-contract checks.

## Score Breakdown

- Debug process and reporting: 10 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 9 / 14
- care_event full chain: 12 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 13 / 14
- DB migration compatibility: 2 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 4 / 6
- Docs and maintainability: 3 / 4

Subtotal: 83 / 100

Cap applied: a targeted sensitive-context request can still inherit an ambient current session when no explicit `session_id` is provided, so the sensitive-context cap limits the final score to **82 / 100**.

## Strengths

The normal visible workflow is complete. Public tests and the debug probe pass, and the PR template records the initial failures, the final checks, and the ESP-IDF build result in useful detail.

Admin/auth is fully repaired. The submitted code fixes password hashing, admin existence checks, admin session token lookup, local management bypass, forged/missing cookie handling, expired/unknown identity rejection, and management endpoint authorization. The full hidden admin/auth family passes 8 / 8.

The care-event runtime path is mostly solid for a fresh database: create/query, admin write gate, room/bed normalization, ordering/limit behavior, room/bed filtering, and context integration scaffolding are implemented. Sleep CSV ownership is fully solved across explicit room/bed, configured default, `first`, `all`, and `skip` policies. Legacy API and ESP API regression checks remain green.

The ESP32-S3 work is substantial and credible. The implementation adds protocol helpers, MaixSense parsing, NVS-backed device config, Wi-Fi STA, Bemfa MQTT publishing, lowercase topic generation, `payload_b64` JSON construction, and preserves the USB path. Static coverage is 7 / 8, and the user confirmed the real ESP-IDF build completed.

## Main Failures

The high-impact remaining bug is still the sensitive context boundary. `build_chat_context_v3()` uses `get_current_session()` when no explicit `session_id` is provided. That means a targeted patient-context request can be authorized by an ambient previous session. This causes both the context-policy hidden failure and the care-event context integration failure.

The old SQLite migration path is broken. `_migrate_care_events_table()` exists and attempts to add `severity/source/created_by/ts`, but `init_management_db()` creates indexes on `care_events(ts)` before the migration runs. On an existing old table without `ts`, startup crashes with `sqlite3.OperationalError: no such column: ts`. This is a real deployment compatibility bug.

There is a smaller policy precision issue: a session without `actor_subject_id` is denied, but the reported reason is `not_authenticated` rather than `not_authorized_for_target`. The access decision is safe, but the authorization model is not clean.

ESP static misses one contract point: `mqtt` is present through `idf_component.yml`, but not in the active `CMakeLists.txt` `REQUIRES` list expected by the static contract. Since the real build passed, this is mostly a maintainability/shape deduction rather than a functional build failure.

The PR template overstates migration safety. It says old `created_ts` rows are automatically mapped into `ts`, but the index-before-migration ordering prevents that from working on real old databases.

## Comparison With GLM-5.1 Qoder

WorkBuddy is clearly the better tool channel in this run. It did not show Qoder's compression failure pattern, and it completed the build/report sequence with much less manual steering.

For final code quality, Qoder's GLM-5.1 submission is still slightly cleaner: it passed all 8 ESP static checks and preserved old-DB migration compatibility. WorkBuddy's version has smoother process evidence but worse migration closure. I would therefore keep Qoder GLM-5.1 at **82.0 ability**, and place WorkBuddy GLM-5.1 at about **81.6 ability**, while noting that the WorkBuddy experience is more reliable as an interactive coding environment.

## Judgment

Record this as **82 / 100**. It is a capable upper-mid result with strong admin/auth, sleep import, fresh-schema care-event behavior, and a real firmware build. It still cannot break out of the 82 cluster because the sensitive targeted-context fallback remains, and unlike the Qoder GLM-5.1 run it also misses the old-database migration edge case.
