# Kimi K2.7 Code (Opencode/API) Evaluation - 2026-06-17

Result directory: `evaluator/results/20260617_131242`

Final score: **82 / 100**

Ability-only ranking score: **81.8 / 100**

Ranking note: this should not be compared 1:1 with the earlier Kimi K2.6 Qoder run because the toolchain is different. On final code quality, K2.7 is clearly stronger than that K2.6/Qoder result: ESP static is clean, the real ESP-IDF v6.0 build passes, and there is no Qoder compression/workdir instability in the evidence. It still lands in the same 82-point capped cluster because the sensitive targeted-context fallback remains.

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 29 / 34 passed, 5 failed, 0 errors.
- ESP-IDF static tests: 8 / 8 passed.
- Evaluator-run ESP-IDF v6.0 build: passed in WSL `Ubuntu-22.04`; generated `stdpro.bin` around 957K.
- PR template: present and detailed.
- `answer.md`: not present; v2 primarily used `PULL_REQUEST_TEMPLATE.md` as the required final report artifact.
- Git diff artifacts: unavailable because the current restored `workspace` is not a git repository.

## Score Breakdown

- Debug process and reporting: 9 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 10 / 14
- care_event full chain: 12 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 14 / 14
- DB migration compatibility: 5 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 5 / 6
- Docs and maintainability: 3 / 4

Subtotal: 88 / 100

Cap applied: targeted sensitive context can still be authorized without an explicit request `session_id` by falling back to `get_current_session()`. The rubric's sensitive-context cap limits the final score to **82 / 100**.

## Strengths

Kimi K2.7 Code produced a broad, credible repair. Public tests and the debug probe pass. The admin/auth hidden family is complete: password/session token hashing, exact valid-cookie lookup, logout invalidation, management API gating, local spoofing protection, remote gallery protection, admin setup/login, and unknown identity rejection all pass.

Sleep CSV ownership is fully solved. Explicit room/bed, configured default bed, unscoped `first`, explicit `all`, and `skip` all pass. Regression compatibility is also clean for the legacy v2 ingest/latest paths, voice context, `/api/esp/status`, and `/api/esp/set`.

The ESP32-S3 implementation is one of the stronger parts of this run. Static ESP checks pass 8/8 and evaluator-side ESP-IDF v6.0 WSL compilation completed successfully. The firmware adds Wi-Fi STA, ESP-IDF v6 compatible MQTT dependency handling, NVS keys, lowercase `tof1/tof2/mlx1/mlx2` topics, dynamic base64 JSON `payload_b64` allocation, ToF/MLX MQTT mirroring, and preserves the USB packet path.

The care-event module is mostly complete: CRUD, HTTP auth gate, room/bed normalization, subject/bed validation, limit/ordering, and chat-context integration all exist. The implementation is modular rather than a public-test-only patch.

## Main Failures

The high-impact remaining bug is still in `build_chat_context_v3()`: when the request does not include an explicit `session_id`, it falls back to `get_current_session()`. A previously recognized staff/admin session can therefore silently authorize a new targeted patient-context request. This also causes the hidden care-event context leakage failure.

The no-actor session path is rejected, but with the wrong policy reason: `not_authenticated` instead of `not_authorized_for_target`. That is less dangerous than a data leak in that path, but it shows the authorization model was not fully reasoned through.

Old SQLite migration compatibility is incomplete. The code adds missing `care_events` columns, but because the column snapshot is taken before `ALTER TABLE`, the `ts` backfill does not run when `ts` was newly added. Old rows survive, but their `ts` remains `0`, so event ordering and old-data fidelity are degraded.

The PR template is detailed and mostly factual, and its ESP build claim is supported by evaluator verification. However, it misses the exact final-verification wording expected by the process contract, and it is a bit too confident about old-table migration compatibility.

## Judgment

This is a strong upper-middle V2 result. Compared with Kimi K2.6 in Qoder, K2.7 Code looks meaningfully better on firmware/build reliability and process stability, though the tools are different enough that I would avoid treating the delta as a pure model-only improvement.

Within the existing 82-point cluster, I would place it around DeepSeek V4 Flash and slightly above Mimo v2.5 Pro on firmware confidence, but below GLM-5.1's best final-code result because GLM had complete old-DB migration compatibility. The unresolved sensitive-context fallback is exactly the kind of realistic privacy bug this benchmark was designed to catch, so **82** is the right ceiling for this run.
