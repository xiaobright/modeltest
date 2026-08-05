# Project2 V2 Soft-Cap Experimental Scoreboard

Updated: 2026-07-09

This file is an experimental, non-official re-ranking of the existing V2 results. It does **not** replace `v2_scoreboard_current.md` or the individual review files. It is meant to answer one question: if non-catastrophic hard caps are converted into large deductions plus release-blocker labels, how much separation appears inside the crowded 80-82 band?

No model was rerun for this file. Scores are inferred from the existing review records, hidden/static summaries, build evidence, and prior manual judgments.

## Scoring Rule

The official V2 rubric remains unchanged. This experimental rule changes only cap handling:

- Keep the original 100-point category rubric as the base.
- Use the review subtotal when a review had a subtotal above the hard-capped final score.
- Do not hard-cap ordinary high-risk bugs such as ambient-session context fallback. Instead, keep the category deductions and mark the result as a release blocker.
- Keep hard caps for result-trust failures: public tests failing in touched areas, broad admin/auth bypass, plaintext admin credentials, missing required work while claiming completion, real ESP-IDF build failure with unsupported success claims, or materially untrustworthy reports.
- Use small decimal tie-breaks only where the archived reviews already contained enough qualitative evidence to order tied results.

Release classes:

- **A**: Near-complete, no known release blocker or only small semantic issues.
- **B+**: Strong final code, but at least one release blocker or serious deployment risk remains.
- **B**: Broadly capable, visible workflow complete, but one or more important blockers remain.
- **C**: Partial but useful repair; multiple core areas incomplete or weak.
- **D**: Not reliably shippable; public/build/report trust is broken.

Blocker codes:

- **S**: Sensitive context/session authorization blocker.
- **M-crash**: Old database migration crashes on deployed schema.
- **M-fidelity**: Old data survives but migration fidelity/order/timestamp semantics are degraded.
- **E-build**: Required ESP-IDF build fails or is not trustworthy.
- **E-contract**: ESP firmware is buildable/attempted but misses static or protocol contract shape.
- **P-report**: PR/report overclaims, omits required verification, or has process trust issues.
- **F-public**: Public tests fail in touched/in-scope behavior.

## Experimental Leaderboard

| Soft Rank | Model | Tool / channel | Official score | Soft-cap score | Release class | Main blockers | Reason for movement |
|---:|---|---|---:|---:|---|---|---|
| 1 | GPT-5.5 | Codex | 96 | 96.0 | A | Minor context reason-code issue | Stays first; no meaningful cap pressure |
| 2 | Grok-4.5 | Current workspace channel | 96 | 95.7 | A | Minor context reason-code issue, report artifact nit | Top-tier entry: 33/34 hidden, 8/8 ESP static, and user-confirmed real build success |
| 3 | GLM-5.2 | Opencode/API | 95 | 95.0 | A | Minor reason-code issue, E-contract | Strongest pre-Grok non-GPT full-strength result |
| 4 | GLM-5.2 | Volcengine / Opencode | 89 | 88.9 | B+ | M-crash, E-contract, P-report | Strong channel sample; no sensitive-context cap, but old-DB migration still crashes |
| 5 | GPT-5.4 | Codex | 88 | 88.3 | B+ | M-crash, E-contract | Same score band as before; privacy boundary is cleaner than capped 82 runs |
| 6 | Kimi K2.7 Code | Opencode/API | 82 | 88.0 | B+ | S, M-fidelity | Biggest soft-cap riser: subtotal was 88, ESP static/build were clean |
| 7 | GLM-5.2 | WorkBuddy | 88 | 87.8 | B+ | M-crash, E-contract, P-report | Strong channel result, but below API and Volcengine/Opencode runs |
| 8 | doubao-seed-2.0-code | Opencode/API | 86 | 86.0 | B+ | M-crash, E-contract | Already escaped the sensitive-context cap; score unchanged |
| 8 | GLM-5.1 | Qoder | 82 | 86.0 | B | S, P-report/tool intervention | Final code was stronger than official cap suggests; complete migration and ESP static |
| 9 | Mimo v2.5 Pro | Opencode/API | 82 | 85.0 | B | S, M-fidelity, P-report | Efficient broad repair; climbs when sensitive-context cap becomes a blocker label |
| 10 | LongCat-2.0 | Current workspace channel | 82 | 84.5 | B | S, E-contract, P-report | Public/debug/build/DB migration all pass; loses to top 82 risers on context policy and ESP static contract |
| 11 | DeepSeek V4 Flash | Opencode/API | 82 | 84.0 | B | S, M-crash | Strong ESP/build result, but old DB migration crash keeps it below GLM/Mimo |
| 12 | Minimax M3 | WorkBuddy / medium thinking | 82 | 84.0 | B | S, M-fidelity, E-contract, reason-code noise | Lower hidden count, but many failures are exact reason-code mismatches; migration improves from crash to fidelity issue |
| 13 | Composer 2.5 | grok-cli | 82 | 83.5 | B | S, M-crash, E-contract, P-report | Fast run with credible ESP/build, but classic context fallback and missing `ts` migration keep it below LongCat/Mimo |
| 14 | GLM-5.1 | WorkBuddy | 82 | 83.0 | B | S, M-crash, E-contract | Tool process better than Qoder, final code weaker on migration |
| 15 | Minimax M3 | Opencode/API | 82 | 83.0 | B | S, M-crash, E-contract, P-report | Strong process/report, but final-code blockers are heavier |
| 15 | Gemini 3.1 Pro | Antigravity | 80 | 80.0 | B- | S, M-fidelity/schema, E-contract, care_event limit gap | Broad repair, but no-actor/context and migration gaps are larger |
| 16 | Kimi K2.6 | Qoder | 80 | 80.0 | B- | S, E-contract/process, Qoder compression issues | Cap was not the main limiter; tool stability and final verification hurt |
| 17 | Gemini 3.5 Flash | Antigravity | 79 | 79.0 | C+ | S, M-fidelity, care_event API gap, P-report | ESP was clean, backend subtlety weaker |
| 18 | Kimi K2.6 | WorkBuddy / medium thinking | 78 | 78.5 | C+ | S, M-crash, care_event gap, E-contract, P-report | Cheaper WorkBuddy sample, but weaker final code than Qoder K2.6 |
| 19 | DeepSeek V4 Pro | Opencode/API | 78 | 78.0 | C+ | S, M-crash, E-contract | Strong backend attempt, but ESP/migration looser than Flash run |
| 20 | Qwen3.7 Max | Qoder | 74 | 74.0 | C | S, M-crash, sleep/care gaps, E-contract | High effort but several core families incomplete |
| 21 | Mimo v2.5 Flash | Opencode/API | 72 | 72.0 | C- | S, M-crash/missing migration, E-build, P-report | Hard trust penalty remains because build success was overclaimed |
| 22 | Minimax M2.5 | Opencode/API | 66 | 66.0 | D | F-public, S, E-build, P-report | Hard caps remain appropriate: public failure plus failed build/report overconfidence |

## What Changes

The main change is the old 82 cluster spreading into roughly **83-88**:

- Grok-4.5 enters directly into the top tier. It does not need a soft-cap boost: the old ambient-session privacy blocker is fixed, hidden is 33/34, ESP static is 8/8, and the real ESP-IDF build was user-confirmed twice.
- Kimi K2.7 Code rises the most because its archived subtotal was already 88: the model had clean ESP static, real ESP-IDF build evidence, complete admin/auth, sleep ownership, and broad care_event work. Its remaining sensitive-context bug is still a release blocker, but no longer erases the rest of the work.
- GLM-5.1 Qoder rises to 86 because its final code preserved old-DB migration compatibility and passed all ESP static checks. The official score hid that because the sensitive-context cap was absolute.
- Mimo v2.5 Pro rises to 85 because it had efficient, broad coverage and strong ESP static evidence, but still loses to GLM-5.1 Qoder on migration fidelity.
- LongCat-2.0 lands at 84.5 because public/debug/build and old-DB migration are all good, but the sensitive-context blocker remains and ESP static coverage is only 5/8.
- DeepSeek V4 Flash rises to 84 because its firmware/build evidence was excellent, but the old DB migration crash is harsher than Mimo's timestamp-fidelity miss.
- Composer 2.5 lands at 83.5 in the soft-cap view: faster and stronger on ESP than many mid-table runs, but below LongCat/Mimo because it misses old DB `ts` migration and leaves the explicit-session context leak.
- WorkBuddy GLM-5.1 and Minimax M3 sit at 83-84: both are broad, but both keep important blockers. WorkBuddy has better channel/process evidence; Minimax has stronger reporting shape, so they remain close.

The new Volcengine/Opencode GLM-5.2 sample does not change the soft-cap philosophy much because it already escapes the sensitive-context cap. It mainly adds channel evidence: GLM-5.2 can still land near the GPT-5.4 band outside the best API run, but old-DB migration is the difference between "strong" and "top-tier complete".

## Interpretation

This soft-cap view is better for ranking nearby models, but worse for release readiness. A model can score 88 here and still be blocked from deployment because of an unresolved sensitive-context bug.

The official strict scoreboard is better for "can this be accepted as-is?" The soft-cap scoreboard is better for "how much useful engineering work did the model actually complete?"

For this project, the two views together are more informative than either one alone:

- Strict score highlights release blockers and prevents serious security issues from being hidden by broad implementation work.
- Soft-cap score reveals that several 82-point runs were not equally strong; they were compressed by one high-value cap.
- Release class preserves the practical warning: high soft score does not mean shippable.

## Channel Notes

WorkBuddy has better continuity evidence than Qoder in the GLM-5.1 comparison: it did not lose the workspace/build context after compression. However, the submitted WorkBuddy GLM-5.1 code was not stronger than the Qoder GLM-5.1 code because it lost old-DB migration compatibility.

GLM-5.2 now has three useful V2 samples. The full Opencode/API run remains the ceiling at 95. The Volcengine/Opencode run reaches 89 with cleaner ESP static than WorkBuddy but the same old-DB crash. WorkBuddy reaches 88 and remains a practical low-cost/free-credit channel, but not the best ability baseline.

Kimi K2.6 WorkBuddy is now recorded as a channel-audit sample. It was cheaper in this run, costing about 500 points at 0.7x, or roughly 714 normalized base-usage units. The submitted final code was weaker than the Qoder K2.6 run: 27/34 hidden and 6/8 ESP static versus 29/34 and 7/8. Treat it as evidence that WorkBuddy can be cost-effective, not as evidence of Kimi's model ceiling.

Minimax M3 WorkBuddy is also recorded as a medium-thinking channel sample. Its strict hidden count is lower than the Opencode/API M3 run, but several failures are reason-code exactness issues rather than missing functionality, and old-DB migration improves from crash-class to timestamp-fidelity failure. It is therefore ranked higher in the soft-cap view than in the strict evidence table. Its cost shape is the opposite of Kimi's: 900 points at 0.25x, or roughly 3600 normalized base-usage units, so the low multiplier was overwhelmed by a much larger run.
