# GLM-5.1 (Qoder) Evaluation - 2026-06-13

Result directory: `evaluator/results/20260613_153623`

Final score: **82 / 100**

Ability-only ranking score: **82.0 / 100**

Ranking note: among the 82-point cluster, this is the strongest final-code result. It keeps the same sensitive-context cap as the others, but has complete old-DB migration compatibility and passes all ESP32-S3 static checks. Qoder/process instability is noted separately and is not counted into this ability-only ordering.

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 30 / 34 passed, 4 failed, 0 errors.
- ESP-IDF static tests: 8 / 8 passed.
- Changed files: 18.
- PR template: present and detailed.
- User-confirmed ESP-IDF build: eventually passed using the Python build path after user intervention.

## Score Breakdown

- Debug process and reporting: 7 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 9 / 14
- care_event full chain: 12 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 13 / 14
- DB migration compatibility: 8 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 4 / 6
- Docs and maintainability: 3 / 4

Subtotal: 86 / 100

Cap applied: a targeted sensitive-context request can still fall back to a previous current session when no explicit `session_id` is supplied. The sensitive-context-leak cap limits the final score to **82 / 100**.

## Strengths

This is a broad and technically substantial repair. The admin/auth family is complete: salted password hashing, exact token-hash cookie lookup, logout invalidation, setup idempotency, management API gating, local spoofing protection, and remote gallery privacy all pass.

The care-event implementation covers schema, old-database migration, validation, normalization, ordering, limits, HTTP routes, and chat-context integration. Sleep CSV ownership passes every hidden case, including explicit room/bed, configured default, first, skip, and explicit all. Legacy API compatibility also remains intact.

The ESP32-S3 work is strong. All eight static checks pass, the implementation adds modular protocol/config/MQTT helpers, Wi-Fi STA, NVS configuration, lowercase topic suffixes, JSON `payload_b64`, and preserves the USB packet path. The user confirmed that a real ESP-IDF build eventually passed.

## Main Failures

The largest remaining bug is in `build_chat_context_v3()`: when `session_id` is absent it calls `get_current_session()`. A previously recognized staff session can therefore silently authorize a new targeted patient-context request. The same path causes the hidden care-event context leakage failure.

A recognized session without `actor_subject_id` is also not handled as a strict authorization failure. The authentication check succeeds, and authorization behavior depends on later actor lookup rather than requiring a valid actor subject as part of the session boundary.

Process compliance was weaker than the final implementation. The model first encountered an error through the PowerShell ESP-IDF path and skipped the build instead of debugging it. Only after the user required the Python script did it continue debugging until the build passed. The PR report also does not record the required `run_espidf_wsl_build.ps1` result or its explicit failure; it describes a temporary `build_helper.py` that is not part of the submitted diff.

The firmware deliberately skips MQTT publication for payloads larger than 8192 bytes, which may exclude full ToF frames. Compilation and static markers are good, but real end-to-end sensor/MQTT behavior remains unverified.

## Judgment

GLM-5.1 in Qoder produced an upper-tier result after intervention. Its final code is stronger than the 82-point cap might suggest, especially in migration compatibility and ESP32 coverage. However, the unresolved privacy boundary is a genuine high-impact bug, and the build workflow shows weaker autonomous persistence: it reached the successful result only after the user redirected it to the required debugging path.

For later comparison with WorkBuddy GLM-5.1, keep two numbers in mind: **82 final quality score**, and **assisted build completion rather than fully autonomous process compliance**.
