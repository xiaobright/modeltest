# qwen3.7max Evaluation - 2026-06-13

Result directory: `evaluator/results/20260613_123517`

Final score: **74 / 100**

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 24 / 34 passed, 9 failed, 1 error.
- ESP-IDF static tests: 6 / 8 passed.
- Changed files: 19.
- PR template: present and detailed.

## Score Breakdown

- Debug process and reporting: 8 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 9 / 14
- care_event full chain: 12 / 14
- Sleep CSV ownership: 3 / 8
- ESP32-S3 protocol/build: 11 / 14
- DB migration compatibility: 2 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 4 / 6
- Docs and maintainability: 3 / 4

Subtotal: 74 / 100

## Strengths

qwen3.7max completed the visible workflow well: public tests and debug probe pass, and the final report is detailed. The admin/auth boundary is the strongest part of the submission: password hashing, token-hash cookies, logout invalidation, management API gating, local spoofing, and remote identity gallery protection all pass hidden tests.

It also made a serious ESP32-S3 attempt rather than ignoring firmware. The solution added MQTT backhaul, payload base64 markers, protocol packet code, MaixSense parser files, NVS-style config files, and ESP-IDF v6.0 managed MQTT dependency handling.

Regression compatibility is good. Legacy v2 ingest/latest and `/api/esp/*` hidden checks passed.

## Main Failures

The context policy still has sensitive-boundary bugs. `build_chat_context_v3()` falls back to `get_current_session()` when no `session_id` is provided, so a previous recognized staff session can silently authorize a targeted patient context request. That leaks care-event context in the no-session path.

Sleep CSV ownership is weak despite the intended policy code. State persists across imports via a `sys.modules` shared sensor store, and `replace_items()` only touches target beds, leaving stale sleep rows on non-target beds. This causes first/default/skip/explicit-room cases to return data for beds that should be empty.

DB migration compatibility is incomplete. Old `care_events` tables lacking `ts` fail because the code creates indexes using `ts` before adding the missing column, so old installs raise `sqlite3.OperationalError: no such column: ts`.

ESP32-S3 static checks are mostly satisfied but not complete: `lwip` is missing from active CMake `REQUIRES`, and config readiness does not require `wifi_ssid`, so MQTT runtime can be treated as ready with incomplete network credentials.

The PR template is useful but misses the required provided ESP-IDF WSL script name/result (`run_espidf_wsl_build.ps1`), using direct `idf.py build` wording instead.

## Judgment

This is a competent, high-effort run with real debugging and broad implementation coverage. It clearly separates from models that only patch public tests. The remaining bugs are not superficial: they sit in privacy boundaries, migration order, data ownership, and deployment readiness. Those are exactly the places a stronger model should catch after public tests pass.
