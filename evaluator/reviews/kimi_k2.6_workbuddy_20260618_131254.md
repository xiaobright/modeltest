# Kimi K2.6 (WorkBuddy) Evaluation - 2026-06-18

Result directory: `evaluator/results/20260618_131254`

Final strict/cap score: **78 / 100**

Soft-cap entertainment score: **78.5 / 100**

Cost/channel note: this WorkBuddy run cost about **500 points** with a visible **0.7x** multiplier. Normalized by multiplier, its rough base usage is `500 / 0.7 = 714` units. That is a useful practical value note, but I did not fold price into the ability score. On ability, this run is below the earlier Kimi K2.6 Qoder result because the submitted final code misses more backend contract points.

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 27 / 34 passed, 7 failed, 0 errors.
- ESP-IDF static tests: 6 / 8 passed.
- Changed files: 10.
- PR template: present and detailed, but it does not record the required `run_espidf_wsl_build.ps1` result or a precise failure reason.
- Real ESP-IDF build: candidate report claims success, but this review did not independently rerun it and the user did not separately confirm it for this scoring turn.

## Score Breakdown

- Debug process and reporting: 8 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 9 / 14
- care_event full chain: 10 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 11 / 14
- DB migration compatibility: 2 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 4 / 6
- Docs and maintainability: 4 / 4

Subtotal: 78 / 100

Cap status: the sensitive targeted-context fallback is still present, so the usual **82-point privacy cap** would apply. It does not change the final score because the subtotal is already below 82.

## Strengths

The visible workflow is complete: public tests pass and the debug probe passes. This means the model did not merely edit around one failure; it fixed enough of the visible system for the normal evaluator entry points to go green.

The admin/auth repair is the best part of this submission. Hidden admin/auth passes 8 / 8: admin setup/login, salted password hashing, exact session-token lookup, logout invalidation, missing/forged cookie rejection, local management API spoofing protection, unknown identity rejection, and remote gallery protection all work.

Sleep CSV ownership is also fully solved. Explicit room/bed import, configured default bed, unscoped `first`, explicit `all`, and `skip` all pass.

The ESP32 work is substantial rather than marker-only. It adds Wi-Fi STA, MQTT client setup, Bemfa connection shape, `payload_b64` JSON publishing, and ToF/MLX MQTT mirroring while preserving USB CDC. Static coverage is only 6 / 8, but the attempted implementation is real work.

## Main Failures

The highest-impact remaining issue is still the sensitive context boundary. `build_chat_context_v3()` falls back to `get_current_session()` when no explicit `session_id` is supplied. A targeted patient-context request can therefore inherit an ambient current session. This fails both the sensitive-target hidden case and the no-actor-subject authorization case.

The care-event chain is incomplete despite looking broad in the PR text. The hidden suite shows three failures: the HTTP create path does not satisfy the expected `/api/v3/care/events` behavior, care events are not wired into the v3 context modalities, and `list_care_events()` does not accept the required `limit` keyword. Fresh-schema module CRUD works, but the full API/context contract is not closed.

Old-database migration is effectively not handled. The code updates the new `CREATE TABLE` schema, but it does not migrate an existing old `care_events` table to add `severity`, `source`, `created_by`, or equivalent compatibility columns. This is a real deployment upgrade bug.

ESP static misses two contract points: `lwip` is missing from active CMake `REQUIRES`, and the source does not expose the expected `tof2` topic suffix marker. The topic helper also builds a `tof1` string and then replaces the suffix, which is a brittle shape even if it can work at runtime.

The PR template is long and useful, but it overclaims. It says the care-event context, old schema compatibility, and ESP build path are all fully handled; the evaluator evidence does not support that. It also records a raw `wsl.exe` build-style command rather than the benchmark's required `tools/run_espidf_wsl_build.ps1` record or an explicit reason for not using it.

## Comparison

Compared with **Kimi K2.6 in Qoder**, WorkBuddy appears to be the nicer and cheaper channel, but this submitted final code is weaker. Qoder K2.6 reached 29 / 34 hidden and 7 / 8 ESP static; WorkBuddy K2.6 is 27 / 34 hidden and 6 / 8 ESP static, with larger care-event and migration gaps. I would not treat this as proof that WorkBuddy is bad, only that this particular run did not beat the earlier K2.6/Qoder final code.

Compared with **Kimi K2.7 Code through Opencode/API**, the gap is much clearer. K2.7 had the same broad privacy cap problem, but its ESP static/build evidence and overall contract closure were much stronger. This K2.6 WorkBuddy result is more of a competent middle result than a near-82-cluster breakout.

## Judgment

Record the strict score as **78 / 100**. In the entertainment/soft-cap ranking, I would place it at **78.5 / 100**: a bit above the old 78-point backend-strong-but-loose results because admin/auth and sleep are clean and the WorkBuddy cost is attractive, but below Gemini 3.5 Flash and below Kimi K2.6 Qoder because too many real contract edges remain open.
