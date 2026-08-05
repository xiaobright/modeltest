# LongCat-2.0 Evaluation - 2026-07-07

Result directory: `evaluator/results/20260707_112431`

Final score: **82 / 100**

Ability-only ranking score: **81.5 / 100**

Channel note: the user identified this run as Meituan **LongCat-2.0**. The exact provider/tool channel was not separately labeled in the prompt, so this review records it as the current V2 workspace run rather than treating it as a controlled API/channel baseline.

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 30 / 34 passed.
- ESP-IDF static tests: 5 / 8 passed.
- ESP-IDF real build: rerun locally with Windows ESP-IDF v6.0.1 and passed.
- Changed files: 12 working-tree entries in the evaluator summary.
- Untracked ESP helper files preserved under `evaluator/results/20260707_112431/untracked_files/`.
- PR template: present and detailed, but failed the hidden process-contract check for missing explicit final verification wording.

## Score Breakdown

- Debug process and reporting: 9 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 9 / 14
- care_event full chain: 12 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 10 / 14
- DB migration compatibility: 8 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 4 / 6
- Docs and maintainability: 4 / 4

Subtotal before cap: roughly **86 / 100**.

Strict cap applied: **82 / 100**, because the sensitive targeted-context path still authorizes through ambient/current-session state when an explicit session is required. This is the same class of release-blocking privacy bug that capped several earlier V2 runs.

## Strengths

LongCat-2.0 gets the visible workflow right. Public tests and the debug probe both pass, including the admin setup path, missing/forged-cookie rejection, unknown/expired session rejection in the visible probe, care_event auth gate, care_event normalization, and sleep importer policy behavior.

The admin/auth hidden family is complete at 8 / 8. It handles salted admin password storage, exact cookie validation, logout invalidation, management API protection, local spoofing resistance, remote gallery protection, and unknown identity denial.

DB migration is a real strength in this run. Unlike many 82-point or 88-point samples, the old `care_events` SQLite table migration passes the hidden old-schema compatibility test without data loss. That is a meaningful deployment-quality point.

Sleep CSV ownership is complete at 6 / 6 hidden. The model handles explicit room/bed, configured defaults, default-first behavior, explicit all, skip policy, and the "first not all" distinction.

The ESP32 work is not just decorative. The firmware was rerun with Windows ESP-IDF v6.0.1 and builds successfully to `stdpro.bin`. This avoids the harsh build-trust penalty that hurt several lower-scoring runs.

## Main Failures

The biggest failure is still context authorization. Hidden tests show that a sensitive targeted context can be allowed without the explicit session boundary required by the contract. That is a real privacy bug, not a cosmetic reason-code issue, so the strict 82 cap is appropriate.

There is also one narrower context-policy semantic failure: a recognized but incomplete session without `actor_subject_id` is denied, but the reason is `not_authenticated` instead of `not_authorized_for_target`. That is less severe than leaking data, but it shows the policy model is still not fully precise.

care_event context integration is incomplete. CRUD, auth gate, ordering, room/bed query, and normalization mostly work, but the hidden context integration test still observes an allowed path where it should be denied.

ESP static coverage is weaker than the real build result suggests. The static contract misses `mbedtls` in active `CMakeLists.txt` `REQUIRES`, the `mbedtls_base64` marker, and the explicit `tof1` stream suffix marker. The build passes because the implementation avoids some of those exact shapes, but from a benchmark-contract standpoint this is still weaker than the 7/8 or 8/8 ESP runs.

The PR template is long and useful, but the process-contract test fails because it does not explicitly record final verification after fixes with the expected wording. This is minor compared with context leakage, but it matters because the benchmark uses the final report as part of evaluation consistency.

## Judgment

I would record LongCat-2.0 as **82 / 100** strict and **81.5 / 100** for ability-only ordering inside the 82 cluster.

Qualitatively, this is a competent mid-high V2 run: public/debug pass, admin/auth pass, sleep pass, DB migration pass, and real ESP-IDF build pass. It is better than a superficial "tests look green" submission.

It does not break into the 86+ strict band because the high-value sensitive-context bug remains. Compared with the crowded 82 group, it is cleaner than many runs on DB migration, but weaker on ESP static contract and process-report precision. I would place it around the middle of the 82 cluster, below GLM-5.1 Qoder / Kimi K2.7 / DeepSeek Flash / Mimo Pro, but above lower 78-80 partial repairs.
