# Project2 V2 Current Scoreboard

Updated: 2026-07-09

This is the compact scoreboard for the second-round V2 benchmark. The main long-form report remains `second_round_v2_report.md`.

| Rank | Model | Tool / channel | Score | Ability note | Hidden | ESP static | ESP build evidence | Main note |
|---:|---|---|---:|---:|---:|---:|---|---|
| 1 | GPT-5.5 | Codex | 96 | 96.0 | 33/34 | 8/8 | Strong report/static evidence, not evaluator-rerun | Best closure; only minor context reason-code issue |
| 2 | Grok-4.5 | Current workspace channel | 96 | 95.7 | 33/34 | 8/8 | User-confirmed ESP-IDF build passed twice | Huge jump vs Grok-4.3; full ESP/static/backend, only minor context reason-code miss |
| 3 | GLM-5.2 | Opencode/API | 95 | 95.0 | 33/34 | 6/8 | Evaluator WSL build passed | Strongest non-GPT V2 result before Grok-4.5; complete backend, ESP has static/field-risk deductions |
| 4 | GLM-5.2 | Volcengine / Opencode | 89 | 88.9 | 32/34 | 7/8 | User-confirmed Windows ESP-IDF v6.0.1 build passed | Strong channel sample; old DB migration crash keeps it below the API baseline |
| 5 | GPT-5.4 | Codex | 88 | 88.3 | 32/34 | 6/8 | Evaluator WSL build passed | Slight tie-break win over WorkBuddy GLM-5.2; old DB migration still breaks |
| 6 | GLM-5.2 | WorkBuddy | 88 | 87.8 | 32/34 | 6/8 | Evaluator WSL build passed | Strong channel cross-check; old DB migration regresses vs API run |
| 7 | doubao-seed-2.0-code | Opencode/API | 86 | 86.0 | 32/34 | 5/8 | Evaluator WSL build passed | Very strong backend; weaker ESP contract |
| 8 | GLM-5.1 | Qoder | 82 | 82.0 | 30/34 | 8/8 | User-confirmed final build after intervention | Best final-code result in the old 82 cluster; tool/process drag |
| 9 | Kimi K2.7 Code | Opencode/API | 82 | 81.8 | 29/34 | 8/8 | Evaluator WSL build passed | Strong firmware/build result; still hits sensitive-context cap |
| 10 | DeepSeek V4 Flash | Opencode/API | 82 | 81.8 | 30/34 | 8/8 | Evaluator WSL build passed | Strong Flash run; old DB path is harsher |
| 11 | Mimo v2.5 Pro | Opencode/API | 82 | 81.7 | 29/34 | 8/8 | User-confirmed WSL build | Efficient and broad; context fallback remains |
| 12 | GLM-5.1 | WorkBuddy | 82 | 81.6 | 30/34 | 7/8 | User-confirmed build before PR writing | Better tool/process than Qoder; final code loses old-DB migration |
| 13 | LongCat-2.0 | Current workspace channel | 82 | 81.5 | 30/34 | 5/8 | Windows ESP-IDF v6.0.1 build rerun passed | DB migration/build pass; sensitive context leak and weaker ESP static keep it capped |
| 14 | Composer 2.5 | grok-cli | 82 | 81.45 | 30/34 | 7/8 | User-confirmed ESP-IDF build passed | Fast and credible ESP work; context fallback and old DB migration keep it capped |
| 15 | Minimax M3 | Opencode/API | 82 | 81.4 | 30/34 | 6/8 | PR records build flow | Good process/reporting; migration and ESP static less clean |
| 16 | Minimax M3 | WorkBuddy / medium thinking | 82 | 81.2 | 27/34 | 6/8 | Candidate claims build; not independently rerun/confirmed | Better than Kimi WorkBuddy; reason-code noise, migration fidelity, and context cap remain |
| 17 | Gemini 3.1 Pro | Antigravity | 80 | 80.0 | 29/34 | 7/8 | Not uniformly rerun | Big V1 -> V2 improvement |
| 18 | Kimi K2.6 | Qoder | 80 | 80.0 | 29/34 | 7/8 | Process record weak; Qoder compression interference | Capable, but tool stability hurt process |
| 19 | Gemini 3.5 Flash | Antigravity | 79 | 79.0 | 28/34 | 8/8 | Not uniformly rerun | Already strong in V1, less V2 lift |
| 20 | Kimi K2.6 | WorkBuddy / medium thinking | 78 | 78.5 | 27/34 | 6/8 | Candidate claims build; not independently rerun/confirmed | Cheaper WorkBuddy run, but weaker final code than Qoder K2.6 |
| 21 | DeepSeek V4 Pro | Opencode/API | 78 | 78.0 | 29/34 | 5/8 | Not uniformly rerun | Backend strong, ESP/migration looser |
| 22 | Qwen3.7 Max | Qoder | 74 | 74.0 | 24/34 | 6/8 | Not uniformly rerun | High effort, but several core families incomplete |
| 23 | Mimo v2.5 Flash | Opencode/API | 72 | 72.0 | 29/34 | 7/8 | Evaluator WSL build failed | Public/debug strong, build overclaim caps score |
| 24 | Minimax M2.5 | Opencode/API | 66 | 66.0 | 30/34 | 8/8 | Evaluator WSL build failed | Hidden/static looked good, but public/build/report trust failed |

Summary:

- Average score: about **82.7**.
- Median score: **82**.
- Grok-4.5 is now recorded as a top-tier V2 sample: hidden 33/34, ESP static 8/8, and user-confirmed real ESP-IDF build success twice. It is a very large improvement over the earlier Grok-4.3 result.
- Composer 2.5 is recorded as a fast, credible 82-cluster sample: hidden 30/34, ESP static 7/8, and user-confirmed real ESP-IDF build success. It remains capped by the classic explicit-session context boundary bug and an old DB migration miss.
- Main crowding point: the old **82 cap**, caused by sensitive targeted-context fallback through ambient current session. The GLM-5.2 samples that clear this cap rise into the 88-95 band.
- LongCat-2.0 is now recorded as another capped 82-point sample: public/debug/build/DB migration are good, but sensitive targeted context and weaker ESP static contract prevent it from leaving the crowded band.
- Kimi K2.7 Code should be treated as a new Opencode/API result, not a direct apples-to-apples replacement for Kimi K2.6 in Qoder.
- GLM-5.2 now has three recorded V2 channel samples. The Opencode/API baseline remains the strongest at 95; the new Volcengine/Opencode run reaches 89; WorkBuddy reaches 88. The split suggests GLM-5.2's model ceiling is high, but channel/runtime shape still matters.
- GPT-5.4, GLM-5.2 Volcengine/Opencode, and GLM-5.2 WorkBuddy are close in final strict score. The new Volcengine sample is ranked above GPT-5.4 because it has cleaner ESP static evidence, but it still loses heavily to the 95-point API run on old-DB migration compatibility.
- GLM-5.1 now has both Qoder and WorkBuddy results. WorkBuddy behaved much better around context compression and build/report continuation, but the final code is slightly weaker than the Qoder run because old-DB migration regressed.
- Kimi K2.6 now has both Qoder and WorkBuddy results. WorkBuddy was cheaper in this sample: about 500 points at 0.7x, or roughly 714 normalized base-usage units. The final code is weaker, though: 27/34 hidden and 6/8 ESP static versus Qoder's 29/34 and 7/8.
- Minimax M3 now has both Opencode/API and WorkBuddy medium-thinking results. The WorkBuddy run has fewer hidden passes, but many failures are reason-code exactness issues; its old-DB migration improves from crash-class to timestamp-fidelity failure. Cost-wise it was not actually cheap despite the 0.25x multiplier: about 900 points, or roughly 3600 normalized base-usage units, because the run expanded much more work than Kimi K2.6 WorkBuddy.
