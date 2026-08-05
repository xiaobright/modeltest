# gpt5.5 Evaluation - 2026-06-13

Result directory: `evaluator/results/20260613_133751`

Final score: **96 / 100**

Note: this run was resumed from the older gpt5.5 quota snapshot, before the later visible ESP-IDF v6.0.0 guidance was added to the seed. That makes the ESP-IDF portion a little harder than the later runs with the short v6.0.0 note.

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 33 / 34 passed, 1 failed, 0 errors.
- ESP-IDF static tests: 8 / 8 passed.
- Changed files: 25 in working tree, including 6 new ESP32 helper files.
- PR template: present, detailed, and records the required visible commands.

## Score Breakdown

- Debug process and reporting: 9 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 13 / 14
- care_event full chain: 14 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 13 / 14
- DB migration compatibility: 8 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 5 / 6
- Docs and maintainability: 4 / 4

No cap applied.

## Strengths

This is the strongest v2 run so far by a clear margin. It passes every public check, the visible debug probe, all ESP32 static checks, and 33 of 34 hidden tests. The remaining hidden failure is a policy reason-code mismatch, not an observed patient-data leak.

The admin/auth boundary is essentially complete: admin setup is persisted, passwords are salted PBKDF2 hashes, HTTP sessions store token hashes rather than plaintext tokens, forged or missing cookies are rejected, logout invalidates the cookie, and local-loopback access no longer bypasses management APIs.

The v3 context policy is mostly correct. It requires an explicit valid `session_id` for sensitive targeted patient context, rejects unknown and expired sessions, preserves staff/admin access, and prevents a patient session from reading another patient. It also integrates care events without leaking them to unauthenticated callers.

The care-event chain is full-stack rather than superficial: schema creation, old-table migration, CRUD, room/bed normalization, limit/order behavior, HTTP auth gates, and chat-context integration all pass. The sleep CSV ownership fixes also cover explicit room/bed, default bed, `first`, `skip`, and explicit `all`.

The ESP32-S3 work is comparatively strong. It adds Wi-Fi STA, MQTT/Bemfa publishing, NVS config keys, lowercase topic construction, `payload_b64` JSON publishing, and preserves the USB packet contract. The helper split into `protocol_packet.*`, `maixsense_parser.*`, and `mqtt_payload.*` is a maintainable shape. The static contract passes completely, and the payload buffer sizing looks plausible for both ToF raw frames and MLX float payloads.

## Main Issues

The only hidden failure is in the no-actor session policy. A recognized, non-expired session with an empty `actor_subject_id` is denied, but the response reason is `not_authenticated`; the expected policy reason is `not_authorized_for_target`. This does not leak patient context in the tested path, but it shows the authorization model was not perfectly classified.

The PR template claims a real ESP-IDF WSL build succeeded and gives the wrapper command plus artifact path. I did not rerun the real ESP-IDF build during scoring, so this is treated as strong self-reported evidence plus static validation, not as independently reproduced build evidence. The `espressif/mqtt` `1.0.0` dependency/cache note is also something a real CI environment should verify.

## Judgment

This is a top-tier result for the current benchmark. It does not merely satisfy the obvious public tests; it fixes the cross-cutting security, migration, data-ownership, regression, and firmware-contract pieces in one coherent pass. The score stays below perfect because of the one context-policy semantic miss and because the real ESP-IDF build evidence is not independently replayed in the evaluator output.
