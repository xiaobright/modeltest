# V4 Original Design Archive

**Archived:** 2026-07-11  
**Status:** historical design and cross-review material; not the active evaluator contract

This directory preserves the planning set used to design and implement Project2 V4.0.
Files are retained together so their relative links and review references remain readable.

## Contents

| Group | Files |
|---|---|
| Design sequence | `00_DESIGN_BRIEF.md` through `08_CROSS_REVIEW_CHECKLIST.md` |
| Historical scoring examples | `APPENDIX_SCORE_EXAMPLES.md` |
| Deferred upper-bound ideas | `CAPSTONE_ITEM_IDEAS.md` |
| Implementation plan | `IMPLEMENTATION_HANDOFF.md` |
| Cross-review corpus | `reviews/` |

## Reading Rule

- These documents explain intent, alternatives and decisions at design time.
- They contain future tense, unchecked boxes, provisional thresholds and relabel examples.
- They must not override the frozen implementation, formal scoreboard or result evidence.

Current sources of truth:

1. `evaluator/scoring/rubric.md`
2. `evaluator/scoring/item_registry.json`
3. `evaluator/scoring/score_model.py`
4. `evaluator/run_full_eval.py` and evaluator-owned tests
5. `evaluator/reports/v4_freeze_manifest.md`

For a concise comparison between this design and the implemented system, see
[`../../CURRENT_STATE_VS_ORIGINAL_DESIGN.md`](../../CURRENT_STATE_VS_ORIGINAL_DESIGN.md).
