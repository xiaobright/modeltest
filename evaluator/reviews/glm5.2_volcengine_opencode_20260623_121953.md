# GLM-5.2 (Volcengine / Opencode) Evaluation - 2026-06-23

Result directory: `evaluator/results/20260623_121953`

Final score: **89 / 100**

Ability-only ranking score: **88.9 / 100**

Channel note: this is a Volcengine-channel GLM-5.2 run through Opencode. It should be kept separate from the earlier full-strength Opencode/API GLM-5.2 result (`95 / 100`) and the WorkBuddy GLM-5.2 result (`88 / 100`). This run is closer to GPT-5.4 / WorkBuddy GLM-5.2 than to the 95-point API baseline: strong overall, but still misses the old-database migration edge.

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 32 / 34 passed, 1 failed, 1 error.
- ESP-IDF static tests: 7 / 8 passed.
- ESP-IDF real build: user-confirmed Windows ESP-IDF v6.0.1 build passed.
- Changed files: 19 working-tree entries; 8 ESP helper files were untracked.
- Extra artifact: untracked helper files were copied to `evaluator/results/20260623_121953/untracked_files/` so the evidence survives workspace reset.
- PR template: present, detailed, and passes process-contract checks.
- `answer.md`: not present; this V2 workspace uses `PULL_REQUEST_TEMPLATE.md` as the required final report artifact.

## Score Breakdown

- Debug process and reporting: 10 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 13 / 14
- care_event full chain: 14 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 13 / 14
- DB migration compatibility: 2 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 4 / 6
- Docs and maintainability: 3 / 4

Subtotal: 89 / 100

No cap applied. The high-value ambient-session targeted-context leak is fixed; the remaining context-policy failure is a reason-code/semantic precision issue, not a patient-data leak.

## Strengths

This is a strong near-top result. The public tests and visible debug probe both pass. Admin/auth is complete across the hidden family: salted password storage, hashed admin-session tokens, exact cookie validation, logout invalidation, management API gating, local spoofing protection, and remote identity gallery protection all pass.

The main privacy boundary that capped many 82-point runs is fixed. Sensitive targeted context no longer silently falls back to an ambient current session when `session_id` is missing. Patient/staff/admin access checks mostly behave correctly, expired sessions are denied, and unauthorized responses do not leak patient data.

The care-event runtime path is complete for the normal schema: CRUD, HTTP auth gates, room/bed normalization, limit and descending ordering, query-by-subject/query-by-bed, and v3 chat context integration all pass hidden tests. Sleep CSV ownership is also fully solved across explicit room/bed, configured default, default `first`, explicit `all`, and `skip`.

The ESP32-S3 work is substantial and build-confirmed. It adds protocol helpers, MaixSense parsing, NVS-backed device config, MQTT JSON/base64 payload handling, Wi-Fi/MQTT startup, lowercase Bemfa topics, and preserves the USB packet contract. Static checks pass 7 / 8, better than the earlier WorkBuddy GLM-5.2 run.

## Main Failures

The serious miss is old SQLite migration compatibility. `init_management_db()` creates indexes on `care_events(ts)` before `_migrate_care_events()` runs. On an existing deployed table without `ts`, startup crashes with `sqlite3.OperationalError: no such column: ts`. This is a real deployment upgrade bug and is the main reason this result cannot approach the earlier 95-point GLM-5.2 API run.

The remaining context-policy failure is narrow: a recognized non-expired session without `actor_subject_id` is denied, but the policy reason is `not_authenticated` instead of `not_authorized_for_target`. The access decision is safe, but the policy model is still less precise than the contract expects.

ESP static misses one dependency-shape marker: active `CMakeLists.txt` does not list `lwip` in `REQUIRES`. Because the user confirmed the Windows ESP-IDF v6.0.1 build passes, this is not a build-blocker deduction, but it is still a contract/maintainability deduction.

The PR template is detailed, but it overclaims old-table migration success. It explicitly says legacy rows are preserved and `ts` is backfilled from `created_ts`; evaluator evidence shows the code crashes before that migration can run on an old table.

## Judgment

I would record this as **89 / 100**. It is slightly stronger than the WorkBuddy GLM-5.2 `88` because ESP static coverage is cleaner and the real build is confirmed, but it is still far below the earlier full-strength GLM-5.2 API `95` because old-DB migration is a deployment-class miss.

For ranking, this sits just above GPT-5.4 and GLM-5.2 WorkBuddy in the strict table, but the qualitative conclusion stays the same: the best GLM-5.2 evidence remains the 95-point API run; this Volcengine/Opencode sample is a strong but not full-ceiling channel result.
