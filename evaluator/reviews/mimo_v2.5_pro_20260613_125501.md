# mimo v2.5 pro Evaluation - 2026-06-13

Result directory: `evaluator/results/20260613_125501`

Final score: **82 / 100**

Ability-only ranking score: **81.7 / 100**

Ranking note: this sits just below GLM in the 82-point cluster. The final implementation is broad and the ESP32-S3 contract is strong, but the old `care_events` migration loses timestamp fidelity and one fewer hidden family case passes. Speed/context efficiency was impressive, but this ability-only ordering does not count cost or tool-channel differences.

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 29 / 34 passed, 5 failed, 0 errors.
- ESP-IDF static tests: 8 / 8 passed.
- Changed files: 10.
- PR template: present and detailed.

## Score Breakdown

- Debug process and reporting: 8 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 10 / 14
- care_event full chain: 12 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 13 / 14
- DB migration compatibility: 5 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 4 / 6
- Docs and maintainability: 3 / 4

Subtotal: 85 / 100

Cap applied: sensitive targeted context can be authorized without an explicit request session by falling back to the current session, so the rubric's sensitive-context-leak cap limits the final score to **82 / 100**.

## Strengths

mimo v2.5 pro produced a broad, practical repair. It passed all visible tests and the debug probe, fixed the admin authentication boundary cleanly, preserved legacy API compatibility, and completed the sleep CSV ownership behavior including explicit bed, default bed, first, skip, and all-policy cases.

The ESP32-S3 work is one of the stronger parts of this run. It added Wi-Fi STA, MQTT/Bemfa backhaul, NVS configuration keys, lowercase topic handling, `payload_b64` JSON publishing, CMake and component-manager dependencies, while preserving the USB packet contract. Static ESP checks all passed. The user confirmed it did perform a real WSL ESP-IDF build, but it did not use or record the required wrapper script, so process compliance is not full credit.

The implementation is reasonably maintainable: care event CRUD is kept in a module, gateway code is mostly routing and policy glue, and the final PR report is detailed enough to understand what changed.

## Main Failures

The largest issue is the v3 context policy. `build_chat_context_v3()` still falls back to `get_current_session()` when no `session_id` is supplied, so a previous recognized staff session can silently authorize a targeted patient context request. This also leaks care-event content in the no-explicit-session path. That is why the sensitive-context cap applies.

The no-actor session boundary is semantically off. A recognized session with an empty `actor_subject_id` is treated as `not_authenticated`; the expected policy is `not_authorized_for_target`. It does not appear to leak patient data in that case, but it shows the authorization model was not fully reasoned through.

DB migration compatibility is incomplete. Old `care_events` tables get the missing columns, but `ts` is added with default `0` and is not backfilled from `created_ts`, so old rows lose their meaningful event timestamp and ordering semantics.

The PR template is useful but misses the required `run_espidf_wsl_build.ps1` command/result. Since the user confirmed a real WSL build happened, this is a workflow-contract miss rather than a false build claim.

## Judgment

This is a strong middle-to-upper run for the v2 benchmark. It separates clearly from models that only satisfy public tests and from runs that skip firmware. The remaining mistakes are concentrated in privacy/session semantics, migration fidelity, and process discipline rather than broad implementation failure. It is below the top tier because the sensitive context bug is exactly the kind of realistic boundary issue this benchmark is meant to catch.
