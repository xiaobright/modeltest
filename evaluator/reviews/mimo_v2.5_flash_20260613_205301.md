# Mimo V2.5 Flash Evaluation - 2026-06-13

Result directory: `evaluator/results/20260613_205301`

Final score: **72 / 100**

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 29 / 34 passed, 5 failed, 0 errors.
- ESP-IDF static tests: 7 / 8 passed.
- Evaluator-run ESP-IDF v6.0 WSL build: failed.
- Changed files: 13.
- PR template: present and detailed, but missing the required `run_espidf_wsl_build.ps1` record and claiming a successful ESP-IDF build that is contradicted by evaluator verification.

## Score Breakdown

- Debug process and reporting: 7 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 8 / 14
- care_event full chain: 12 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 9 / 14
- DB migration compatibility: 1 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 2 / 6
- Docs and maintainability: 3 / 4

Subtotal: 72 / 100

The sensitive targeted-context leak would cap this run at 82. More importantly, the PR template claims an ESP-IDF WSL build succeeded, but the evaluator's ESP-IDF v6.0 build fails on the submitted code, so the serious unsupported-build-claim cap keeps the final score at **72 / 100**.

## Strengths

Mimo V2.5 Flash completed the visible workflow: public tests and the debug probe both pass. The admin/auth boundary is clean across hidden tests, including password hashing, exact session-token lookup, admin setup/login, logout invalidation, local management spoofing protection, unknown identity rejection, and remote gallery privacy.

Sleep CSV ownership is also fully fixed. Explicit room/bed, configured default bed, unscoped `first`, explicit `all`, and `skip` all pass. Legacy regression compatibility stayed intact for v2 ingest/latest and `/api/esp/*` behavior.

The care-event implementation is fairly broad for new installs: it adds schema fields, CRUD validation, room/bed normalization, limit/descending ordering, HTTP route wiring, and v3 context integration. Only the context integration fails because it is behind the flawed context authorization boundary.

The ESP32-S3 work is not superficial. It adds Wi-Fi STA, MQTT client code, NVS-based config, lowercase topic construction, `payload_b64` publishing, ToF and MLX mirroring hooks, CMake dependencies, and preserves the USB packet path.

## Main Failures

The biggest backend issue is still sensitive v3 context authorization. `build_chat_context_v3()` falls back to `get_current_session()` when no explicit `session_id` is supplied, so a previous recognized session can silently authorize a targeted patient-context request. This is also why the care-event context leak test fails.

The no-actor session path is unsafe. `actor_can_access_target()` still returns `True` when `actor_subject` is missing, so a recognized session with no actor subject can get `policy.allowed=true` for target patient context. This is worse than merely returning the wrong policy reason.

DB migration compatibility is essentially missing for the new care-event columns. New installs get `severity`, `source`, and `created_by`, but an existing old `care_events` table is not upgraded with those columns. The PR itself notes this risk, but treats it as acceptable because care events are "new"; the benchmark expects deployed old SQLite tables to migrate safely.

ESP32-S3 is only partially successful. Static checks pass 7 / 8, but active CMake `REQUIRES` is missing `lwip`. More importantly, a real evaluator-run ESP-IDF v6.0 build fails in `network_backhaul.cpp` because `ESP_EVENT_ANY_ID` is passed directly where `esp_mqtt_event_id_t` is required:

```text
error: invalid conversion from 'int' to 'esp_mqtt_event_id_t'
esp_mqtt_client_register_event(s_mqtt_client, ESP_EVENT_ANY_ID, ...)
```

The PR template says the ESP-IDF WSL build succeeded and gives binary-size numbers, but that does not match the submitted code under the v6.0 environment. It also does not record the required `run_espidf_wsl_build.ps1` command or an explicit failure reason.

## Judgment

This is a strong public/debug repair with good auth, sleep import, regression compatibility, and a serious firmware attempt. It is clearly above models that only patch visible tests.

The score lands much lower than Mimo V2.5 Pro because the final submitted firmware does not compile under ESP-IDF v6.0, the PR overclaims that build result, the old-DB migration path is not actually handled, and the no-actor context path leaks target access. If the build claim were factual and the firmware compiled, this would likely sit in the high-70s; with the unsupported build-success claim, **72 / 100** is the fair strict score.
