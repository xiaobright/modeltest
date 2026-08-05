# GLM-5.2 (WorkBuddy) Evaluation - 2026-06-17

Result directory: `evaluator/results/20260617_225512`

Final score: **88 / 100**

Ability-only ranking score: **87.8 / 100**

Channel note: this is a WorkBuddy run of the same model family as the earlier GLM-5.2 Opencode/API result. The final code is strong and the ESP-IDF v6.0 build is real, but it does not reproduce the API run's old-database migration success. Treat it as a useful channel cross-check, not as a replacement for the Opencode/API baseline.

Tie-break note: this run has the same integer score as GPT-5.4: 32 / 34 hidden, 6 / 8 ESP static, real ESP-IDF build passed, and the same deployment-class old-DB migration crash. If decimals are used only to order tied results, GPT-5.4 is slightly ahead on final-code and ESP shape, so I place GPT-5.4 at about **88.3** and GLM-5.2 WorkBuddy at about **87.8**. This does not contradict the model-body conclusion: the GLM-5.2 Opencode/API run reached **95**, so the model's full-strength ceiling is clearly higher than this WorkBuddy channel result.

## Automated Evidence

- Public tests: passed.
- Debug probe: passed.
- Hidden tests: 32 / 34 passed, 1 failed, 1 error.
- ESP-IDF static tests: 6 / 8 passed.
- Evaluator-run ESP-IDF v6.0 build: passed in WSL `Ubuntu-22.04`; generated `stdpro.bin` around 957K.
- Changed files: 19.
- PR template: present, detailed, and passes process-contract checks.
- User-reported WorkBuddy equivalent cost: about RMB 41.4.

## Score Breakdown

- Debug process and reporting: 10 / 10
- Admin/auth boundary: 14 / 14
- Session/context policy: 13 / 14
- care_event full chain: 14 / 14
- Sleep CSV ownership: 8 / 8
- ESP32-S3 protocol/build: 12 / 14
- DB migration compatibility: 2 / 8
- Regression compatibility: 8 / 8
- PR template factual consistency: 4 / 6
- Docs and maintainability: 3 / 4

Subtotal: 88 / 100

No cap applied. The sensitive targeted-context fallback that capped many 82-point runs is fixed here.

## Strengths

This is still a high-quality run. Public tests and the visible debug probe pass. The admin/auth family is complete: password storage is upgraded to salted PBKDF2, admin HTTP sessions use token hashes, forged and missing cookies are rejected, logout invalidates sessions, management APIs no longer accept local spoofing, and remote gallery/template access is protected.

The highest-value privacy bug is fixed. `build_chat_context_v3()` no longer falls back to `get_current_session()` when no explicit `session_id` is provided, so targeted patient context cannot inherit an ambient current session. That is the key step that separates this result from the crowded 80-82 cluster.

The care-event normal runtime path is broad and correct for new schemas: create/query, room/bed normalization, limit and descending order, HTTP auth gates, and v3 chat-context integration all pass. Sleep CSV ownership is also fully solved across explicit room/bed, configured default, unscoped `first`, explicit `all`, and `skip`. Legacy v2 and ESP API regression tests remain green.

The ESP32-S3 work is substantial and actually builds. The implementation adds protocol helpers, MaixSense parsing, NVS-backed configuration, Wi-Fi STA, MQTT publishing, lowercase Bemfa topics, `payload_b64` JSON publishing, and preserves the USB packet path. The evaluator reproduced a successful ESP-IDF v6.0 build in WSL.

## Main Failures

The remaining context-policy hidden failure is semantic rather than a data leak. A recognized, non-expired session without `actor_subject_id` is denied, but the response reason is `not_authenticated` instead of `not_authorized_for_target`. The access decision is safe; the policy model is still slightly imprecise.

The serious backend failure is old SQLite migration. The code defines `_migrate_care_events_schema()` and it would add `severity/source/created_by/ts`, but `init_management_db()` creates indexes on `care_events(ts)` before that migration helper runs. On an existing old table without `ts`, startup crashes with `sqlite3.OperationalError: no such column: ts`. This is a real deployment compatibility bug, not just a hidden-test wording issue.

ESP static checks fail 2 / 8. Active CMake is missing the explicit `lwip` dependency marker expected by the evaluator, and the static readiness check does not recognize the current `is_network_ready()` naming even though the code does check `wifi_ssid` and `bemfa_uid`. Since the real ESP-IDF build passes, this is mostly a contract/form deduction, but it still means the submitted shape is less clean than the best firmware results.

The PR template is detailed, but it overstates old-table migration completeness. It explicitly claims legacy rows are preserved and `ts` is backfilled from `created_ts`; evaluator evidence contradicts that claim for real old tables because the index creation order crashes before the migration can execute.

## Judgment

I would record this as **88 / 100**. It is clearly above the 82-point cluster because it fixes the ambient-session privacy boundary and completes the visible/debug/backend/firmware workflow. It is also clearly below the Opencode/API GLM-5.2 run because that run passed the old-database migration hidden test and reached 33 / 34 hidden.

For the channel question, this does not prove WorkBuddy is broadly quantized or unusable. It completed a large repair and produced buildable firmware. But compared with the same model through Opencode/API, this sample is meaningfully weaker: roughly similar equivalent cost, lower final score, and a missed deployment migration edge case. The practical reading is: WorkBuddy may still be a good low-cost/free-credits tool channel, but this result should not be used as the full-strength GLM-5.2 ability baseline.
