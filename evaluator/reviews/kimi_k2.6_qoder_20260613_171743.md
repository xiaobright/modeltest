# Kimi K2.6 (Qoder) Evaluation - 2026-06-13

Result directory: `evaluator/results/20260613_171743`

Final score: **80 / 100**

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 29 / 34 passed, 5 failed, 0 errors.
- ESP-IDF static tests: 7 / 8 passed.
- Changed files: 11.
- PR template: present and detailed, but missing the required `run_espidf_wsl_build.ps1` record.

## Score Breakdown

- Debug process and reporting: 6 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 10 / 14
- care_event full chain: 12 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 11 / 14
- DB migration compatibility: 5 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 3 / 6
- Docs and maintainability: 3 / 4

Subtotal: 80 / 100

The sensitive targeted-context fallback would also cap this run at 82, but the subtotal is already below that cap.

## Strengths

Kimi K2.6 produced a broad repair rather than a public-test-only patch. Public tests and the visible debug probe both pass. The admin/auth boundary is complete across the hidden suite: admin setup/login, exact cookie token hashing, logout invalidation, management API gating, local spoofing protection, unknown identity rejection, and remote gallery privacy all pass.

Sleep CSV ownership is also fully solved. Explicit room/bed, configured default bed, unscoped `first`, explicit `all`, and `skip` all pass. Legacy regression compatibility is preserved for v2 ingest/latest, voice context, `/api/esp/status`, and `/api/esp/set`.

The ESP32-S3 work is substantial. It adds Wi-Fi STA, MQTT client setup, NVS keys, `payload_b64` JSON publishing, CMake/component dependencies, and keeps the USB path alive. It is not a superficial marker-only change, even though the static contract is not fully clean.

## Main Failures

The largest remaining issue is still the v3 sensitive context boundary. `build_chat_context_v3()` falls back to `get_current_session()` when no explicit `session_id` is supplied, so a previous/current recognized session can silently authorize a targeted patient context request. This also causes the care-event context integration leakage failure.

A session without `actor_subject_id` is rejected, but it is classified as `not_authenticated` instead of `not_authorized_for_target`. That does not appear to leak data in that specific path, but the authorization model is still not fully precise.

DB migration compatibility is incomplete. Old `care_events` rows survive, but the newly added `ts` column is left empty/zero instead of being backfilled from `created_ts`, so old event ordering/metadata compatibility is degraded.

ESP32-S3 is close but not complete. The static contract reports the `tof1` topic suffix as missing because the source builds ToF topic names dynamically with `"tof%d"` rather than carrying explicit `tof1`/`tof2` contract markers. The implementation also uses a fixed 256-byte JSON buffer after base64 encoding, which is risky for full sensor payloads even if compilation succeeds.

The PR template is detailed, but it records a `python tools/build_helper.py` build path instead of the required `tools/run_espidf_wsl_build.ps1` command/result or an explicit failure reason. In the Qoder run, the user also observed context compression forgetting stable task facts such as the working directory, existing build script, and ESP-IDF v6.0.0 environment. I treat that as mostly a Qoder/tooling issue, but it still lowers process autonomy for this run.

## Judgment

This is a strong middle-to-upper result. Kimi K2.6 clearly clears the baseline and solves the main visible product bugs, with complete admin/auth and sleep-import behavior. It lands slightly below Mimo/GLM in this V2 set because firmware contract compliance is one notch weaker, the migration fix is incomplete, and the Qoder process required more manual stabilization after compression.

For model-body comparison, this run suggests Kimi is capable. For actual agent-use comparison in Qoder, the context-compression instability is a real practical drag.
