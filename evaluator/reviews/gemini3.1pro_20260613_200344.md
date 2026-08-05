# Gemini 3.1 Pro Evaluation - 2026-06-13

Result directory: `evaluator/results/20260613_200344`

Final score: **80 / 100**

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 29 / 34 passed, 5 failed, 0 errors.
- ESP-IDF static tests: 7 / 8 passed.
- Changed files: 13.
- PR template: present and passes the process-contract checks, including final public/debug verification and ESP-IDF WSL build record.

## Score Breakdown

- Debug process and reporting: 9 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 8 / 14
- care_event full chain: 10 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 12 / 14
- DB migration compatibility: 4 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 4 / 6
- Docs and maintainability: 3 / 4

Subtotal: 80 / 100

The sensitive-context cap would limit this run to 82, but the subtotal is already below that cap.

## Strengths

Gemini 3.1 Pro completed the visible workflow cleanly. Public tests and the debug probe both pass, and the PR template records the required public/debug verification and ESP-IDF WSL build evidence in a way the evaluator accepts.

The admin/auth boundary is complete across hidden tests: admin setup/login, password/session token hashing, exact cookie lookup, logout invalidation, local management spoofing, unknown identity rejection, and remote identity gallery protection all pass.

Sleep CSV ownership and regression compatibility are also complete. Explicit room/bed, configured default bed, unscoped `first`, explicit `all`, `skip`, legacy v2 ingest/latest, and `/api/esp/*` compatibility all pass.

The ESP32-S3 work is substantial. It adds MQTT/Base64 payload helpers, Wi-Fi STA startup, ESP-IDF v6 managed MQTT dependency, `payload_b64`, `mbedtls_base64`, active `mqtt`/`esp_wifi`/`esp_netif`/`esp_event`/`lwip`/`mbedtls` dependencies, and ToF MQTT publishing while preserving the USB path.

## Main Failures

The largest remaining backend issue is still the v3 sensitive context policy. `build_chat_context_v3()` falls back to `get_current_session()` when no explicit `session_id` is supplied, so a previous recognized session can silently authorize a new targeted patient-context request.

The no-actor session path is also unsafe. `actor_can_access_target()` still returns `True` when `actor_subject` is missing, so a session without `actor_subject_id` can get `policy.allowed=true` for target context. This is more serious than merely returning the wrong policy reason.

`care_event` is incomplete. `list_care_events()` does not accept the required `limit` keyword, causing the descending-order/limit contract to fail. The context integration also leaks via the flawed authorization path.

DB migration compatibility is weak. The new schema adds `severity/source/created_by`, but it does not add a real `ts` column on old tables. Instead, the code maps `created_ts` to `ts` in returned dictionaries. That helps new API responses but fails the old-database migration contract and leaves the persistent schema incompatible with callers expecting a migrated `ts` column.

ESP32-S3 is close but not complete. Static checks fail on the `mlx1/mlx2` topic contract, and source inspection confirms the firmware only mirrors `tof1/tof2` to MQTT. The MLX sender task still has a TODO for network backhaul, so this is a real missing stream rather than just a marker issue.

The PR template is process-complete, but it overstates migration smoothness and describes the MQTT work as covering ToF and MLX when MLX publish is not actually wired.

## Judgment

This is a solid 80-point run. Compared with Gemini 3.5 Flash, 3.1 Pro has slightly better hidden coverage and noticeably better process reporting, but its ESP implementation is one stream family less complete. Compared with Kimi K2.6, it has better reporting discipline but weaker context/session correctness because the no-actor case is allowed rather than merely misclassified.

Overall it sits in the lower edge of the strong middle tier: broad, credible, and much better than visible-test-only repair, but still missing the subtle privacy and migration guarantees needed to enter the 82+ cluster.
