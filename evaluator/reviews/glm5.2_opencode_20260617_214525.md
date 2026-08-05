# GLM-5.2 Evaluation - 2026-06-17

Result directory: `evaluator/results/20260617_214525`

Final score: **95 / 100**

Ability-only ranking score: **95.0 / 100**

Ranking note: this is a top-tier V2 result, clearly above the 82-point cluster and above GPT-5.4 / Doubao in final code quality. It sits just below the recorded GPT-5.5 run because the ESP static contract is less clean and there is a real firmware concurrency risk in the MQTT payload buffer. Backend-wise, it is essentially complete except for one policy reason-code mismatch.

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 33 / 34 passed, 1 failed, 0 errors.
- ESP-IDF static tests: 6 / 8 passed.
- Evaluator-run ESP-IDF v6.0 build: passed in WSL `Ubuntu-22.04`; generated `stdpro.bin` around 898K.
- Changed files: 24.
- PR template: present, detailed, and passes process-contract checks.
- `answer.md`: not present; this V2 workspace uses `PULL_REQUEST_TEMPLATE.md` as the required final report artifact.

## Score Breakdown

- Debug process and reporting: 10 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 13 / 14
- care_event full chain: 14 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 12 / 14
- DB migration compatibility: 8 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 4 / 6
- Docs and maintainability: 4 / 4

Subtotal: 95 / 100

No cap applied. The sensitive targeted-context fallback that capped many 82-point runs is fixed here.

## Strengths

GLM-5.2 produced a very complete backend repair. Public tests and the visible debug probe pass. The admin/auth hidden family is complete: PBKDF2 password storage, exact token-hash cookie lookup, setup idempotency, login/logout behavior, local spoofing protection, management API gating, unknown identity rejection, and remote gallery privacy all pass.

The highest-value privacy issue is fixed. `build_chat_context_v3()` now requires an explicit `session_id` and no longer falls back to `get_current_session()`, so targeted patient context cannot inherit an ambient current session. Staff/admin and patient access behavior are preserved, expired/unknown sessions are denied, and unauthorized responses do not leak patient data.

The care-event chain is complete: old schema migration, CRUD, room/bed normalization, limit/ordering, HTTP auth gates, v3 context integration, and unauthorized non-leak behavior all pass hidden tests. DB migration compatibility is also complete; old `care_events` rows survive and `ts` is backfilled from `created_ts`.

Sleep CSV ownership is fully solved across explicit room/bed, configured default, unscoped `first`, explicit `all`, and `skip`. Legacy v2 and ESP API regression tests remain green.

The ESP32-S3 work is substantial and actually builds. It adds protocol helpers, MaixSense parsing, NVS-backed device config, payload/base64 helpers, Wi-Fi STA, ESP-IDF MQTT client startup, lowercase Bemfa topics, `payload_b64` JSON publishing, and preserves the USB packet contract. The evaluator reproduced a successful ESP-IDF v6.0 build.

## Main Issues

The one hidden failure is semantic rather than a data leak. A recognized, non-expired session without `actor_subject_id` is denied, but the policy reason is `not_authenticated` instead of `not_authorized_for_target`. That costs context-policy precision, but it does not expose patient context.

ESP static checks fail 2 / 8. One failure is mostly a V6.0 shape mismatch: `mqtt` is not listed in active CMake `REQUIRES` because ESP-IDF v6.0 resolves `espressif/mqtt` through `idf_component.yml`, and the real build confirms that works. The other is a static-marker mismatch: readiness lives in `device_config_backhaul_ready()` and does check `wifi_ssid` / `bemfa_uid`, but the evaluator expected the older `config_is_complete` marker.

There is a real ESP firmware risk beyond static-marker mismatch. `network_backhaul_publish()` uses a `static char body[16384]` and fills it before acquiring `s_mqtt_mutex`. ToF and MLX tasks can call the publish path concurrently, so one task can overwrite the JSON/base64 body while another is about to publish. This is unlikely to affect Python tests or compilation, but it is a realistic field bug for simultaneous USB/MQTT mirroring.

The PR template is detailed and mostly factual, but it slightly overstates ESP payload-buffer safety by treating the static buffer as effectively serial. It also presents the v6.0 Component Manager route as fully contract-equivalent while the static evaluator still expects a CMake `mqtt` marker. I treat the real build as stronger evidence than the static marker, but the mismatch and concurrency risk still cost report/firmware points.

## Judgment

This is the strongest non-GPT V2 result currently recorded, and it is close to the GPT-5.5 score. Compared with GLM-5.1, the jump is large: GLM-5.2 fixes the ambient-session privacy bug, completes old-DB migration, keeps process reporting clean, and passes a real ESP-IDF v6.0 build without user rescue.

I would record it as **95 / 100**. It belongs above GPT-5.4 and Doubao because the old-DB migration path is fixed, and below GPT-5.5 because GPT-5.5 had cleaner ESP static conformance and no observed MQTT buffer concurrency issue in the recorded review.
