# GPT-5.4 Evaluation - 2026-06-13

Result directory: `evaluator/results/20260613_220049`

Final score: **88 / 100**

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 32 / 34 passed, 1 failed, 1 error.
- ESP-IDF static tests: 6 / 8 passed.
- Evaluator-run ESP-IDF v6.0 WSL build: passed in `Ubuntu-22.04`; generated `stdpro.bin`.
- Changed files: 28.
- PR template: present, detailed, and passes process-contract checks.

## Score Breakdown

- Debug process and reporting: 9 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 13 / 14
- care_event full chain: 14 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 13 / 14
- DB migration compatibility: 2 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 4 / 6
- Docs and maintainability: 3 / 4

Subtotal: 88 / 100

No cap applied. The sensitive targeted-context fallback that capped many 82-point runs is fixed here.

## Strengths

This is a strong top-tier-adjacent run. GPT-5.4 passes all public tests, the visible debug probe, and 32 / 34 hidden tests. It is clearly above the previous 80-82 cluster because it fixes the most important privacy-boundary bug: `build_chat_context_v3()` no longer silently falls back to `get_current_session()` when no explicit `session_id` is supplied.

The admin/auth family is complete. Passwords are salted/hash-stored, admin HTTP sessions use token hashes, forged and missing cookies are rejected, logout invalidates sessions, management API loopback spoofing is closed, and remote identity gallery access is protected.

The care-event chain is complete for new installs and normal runtime use. Hidden tests pass for CRUD, room/bed normalization, limit and ordering, HTTP auth gates, and v3 chat-context integration. Sleep CSV ownership is also fully solved across explicit room/bed, configured default bed, `first`, `skip`, and explicit `all`.

The ESP32-S3 implementation is substantial and maintainable. It splits protocol, MaixSense parsing, NVS device config, and MQTT publishing into helper modules; preserves the USB packet contract; publishes ToF and MLX payloads as `payload_b64`; builds lowercase `tof1/tof2/mlx1/mlx2` topics; and uses ESP-IDF v6.0 managed MQTT dependencies. Evaluator-side WSL build reproduced a successful `stdpro.bin`.

The PR template is detailed and records the required public/debug/ESP verification commands, including the provided `run_espidf_wsl_build.ps1` path.

## Main Failures

The one remaining context-policy hidden failure is semantic rather than a data leak. A recognized non-expired session without `actor_subject_id` is denied, but the policy reason is `not_authenticated` instead of the expected `not_authorized_for_target`. That means the authorization model is still slightly imprecise, though it does not expose patient context in this case.

The serious backend failure is old SQLite migration. The code adds `_ensure_care_events_schema()`, but `init_management_db()` creates indexes on `care_events(ts)` inside the initial `executescript()` before the migration helper adds `ts` to old tables. Existing old databases therefore crash at startup with `sqlite3.OperationalError: no such column: ts`. The PR claims old-table migration is covered, so this is also a factual-consistency miss.

ESP32-S3 static checks fail 2 / 8. Active CMake uses `espressif__mqtt` rather than the evaluator's expected `mqtt` token, and the static check does not recognize the renamed `device_config_is_ready()` readiness check even though the actual code does require `wifi_ssid`, password, UID, room, and bed. Since the real ESP-IDF build passes and the runtime code is credible, this is a small contract/form penalty rather than a build failure.

The documentation updates are broad and mostly helpful, but they inherit the incorrect migration-completeness claim.

## Judgment

This is the second genuinely strong GPT-family result in V2. It lands well above the 82-point cluster because it solves the ambient-session privacy boundary and completes the care-event chain. It remains clearly below GPT-5.5 because GPT-5.5 handled old-DB migration and static ESP contract more cleanly.

The score I would record is **88 / 100**: strong final code, real ESP-IDF build, excellent hidden coverage, but with one deployment-breaking migration bug and a small policy-reason miss.
