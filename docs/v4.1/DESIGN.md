# V4.1 Design Summary

**Status:** **V4.1b formal stable baseline**; V4.1a retained as historical transition  
**Archive gate:** `archives/v4_round_final_20260718/`  
**Benchmark string:** `project2-v4.1b`（现行）/ `project2-v4.1`（4.1a 历史）  
**Seed tag:** `project2-v4-broken-seed` (unchanged broken seed)

## Goals

1. Stop F6 double-peak (0/10 vs 10/10) from a single init crash cascading all five items.
2. Record multi-run identity so lucky single runs are not treated as stable level.
3. Keep Ability 100-point scale and Ship/`M-crash` release semantics.
4. Never rewrite V4.0 formal Ability.
5. **V4.1b:** stop ambient→F5 Ability double-count; keep authorized care wiring independent.

## Non-goals

- Capstone / freshness / session preemption / QEMU / HIL (long-term V5 memo; no V4.1c)
- Efficiency inside Ability
- Full matrix retest of all historical models
- Changing candidate ONBOARDING task surface (unless later seed bump)

## Candidate workspace policy (ops)

- **Default:** reset + edit live `workspace/project2_task`, then `run_full_eval` on that path.
- **Optional:** `prepare_candidate_handoff.py` for strict isolation / archiveable drop packages.
- Do not accumulate unused handoff trees under `modeltest_candidate_handoffs/`.

## F6 fixtures

| Item | Points | Fixture |
|------|-------:|---------|
| V4-F6-01 | 3 | Full v0 legacy schema → real upgrade path |
| V4-F6-02 | 2 | Intermediate: new columns already present |
| V4-F6-03 | 2 | Intermediate: columns present, `ts` null → backfill |
| V4-F6-04 | 1 | Intermediate: double init |
| V4-F6-05 | 2 | Intermediate: mixed old/new sort |

## Cascade field

`score_draft.cascade` / `blockers.cascade` annotate root cause for reviews.  
They **do not** change earned points.

## Multi-run main column

Same `model + channel + harness + thinking_level`, n≥2 formal runs:

- **Main Ability = worst formal run**
- Appendix: best / worst / range / family hotspots

## Source of truth order (V4.1b)

1. `evaluator/reports/v4.1b_freeze_manifest.md`
2. `evaluator/scoring/rubric.md` + `item_registry.json` (version v4.1b)
3. evaluator code and tests
4. `evaluator/reports/v4.1b_scoreboard.md`
5. V4.0 archive for historical comparison only
