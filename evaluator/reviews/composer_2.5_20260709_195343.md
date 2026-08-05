# Composer 2.5 Evaluation - 2026-07-09

Result directory: `evaluator/results/20260709_195343`

Final score: **82 / 100**

Ability-only ranking score: **81.45 / 100**

Channel note: this run used **Composer 2.5 on Grok Build CLI** (`channel`/`harness` = `grok-cli`). The user confirmed ESP-IDF real build passed and that the run was fast, so this review records build success without rerunning the long compile.

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 30 / 34 passed.
- ESP-IDF static tests: 7 / 8 passed.
- ESP-IDF real build: user-confirmed passed.
- Process/reporting hidden checks: passed.
- `answer.md`: missing.
- Untracked ESP helper files were preserved under `evaluator/results/20260709_195343/untracked_files/`.

## Score Breakdown

- Debug process and visible workflow: 10 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 8 / 14
- care_event full chain: 11 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/static/build: 12 / 14
- DB migration compatibility: 4 / 8
- Regression compatibility: 8 / 8
- PR/report factual consistency: 4 / 6
- Docs and maintainability: 4 / 4

Subtotal before cap: roughly **83 / 100**.

Strict cap applied: **82 / 100**, because the sensitive targeted-context path still authorizes through ambient/current-session state without an explicit session. This is the same release-blocking privacy class that capped many V2 mid-high runs.

## Strengths

Composer 2.5 clears the visible workflow: public tests pass, debug probe passes, and process-contract checks pass. That means it handled the explicit admin setup/auth probe, visible sleep importer behavior, care_event auth gate, and required PR-template structure well enough.

The admin/auth family is complete at 8 / 8 hidden. It correctly covers salted password/session storage, exact cookie validation, logout invalidation, management API protection, local spoofing resistance, remote gallery privacy, and unknown identity denial.

Sleep import is also complete at 6 / 6 hidden. It handles configured defaults, explicit room/bed targeting, explicit all, skip policy, and the default-first-not-all distinction.

The ESP32 work is materially useful. Static coverage is 7 / 8, the user confirmed real ESP-IDF build success, and the candidate added a maintainable split across `device_config`, `maixsense_parser`, `mqtt_payload`, and `protocol_packet`. Compared with weaker runs that only add markers or overclaim build success, this is a credible firmware contribution.

The run speed was good according to the user. That does not raise the strict score by itself, but it matters for practical usefulness: this is a much more pleasant channel/model shape than slow runs that spend huge context on the same final quality.

## Main Failures

The main blocker is still sensitive context authorization. Hidden tests show that a previous/current session can silently authorize a targeted context request without an explicit `session_id`. That also causes the care_event context integration failure: the unauthenticated/no-explicit-session path is still allowed.

A second context-policy failure is more severe than a simple reason-code mismatch: a session without `actor_subject_id` is allowed when it should be denied. That indicates the policy model still treats some incomplete identity state as sufficient authority.

DB migration is incomplete. The old `care_events` SQLite table is not migrated with the required `ts` column, so old deployed databases lose compatibility with the new care_event contract.

ESP static misses one contract point: network readiness does not explicitly check `wifi_ssid`. Because the real build passed and the rest of ESP static is strong, this is a moderate deduction rather than a build-trust failure.

The final report is usable through `PULL_REQUEST_TEMPLATE.md`, but the requested `answer.md` artifact is absent. I treat that as a consistency/reporting deduction, not a score cap, because the evaluator process-reporting checks still passed.

## Judgment

I would record Composer 2.5 as **82 / 100 strict** and **81.45 / 100 ability-ordering**.

Qualitatively, it belongs in the 82 cluster, around Minimax M3 / LongCat / GLM-5.1 WorkBuddy territory. It is stronger than many 78-80 partial repairs because public/debug/admin/sleep/ESP/build are all credible. It does not break into the 86+ band because it misses the exact bug that separates capped models from top models: no explicit-session boundary for targeted patient context. The old DB migration miss also keeps it below the strongest 82-cluster samples.
