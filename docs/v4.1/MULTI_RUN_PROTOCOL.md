# V4.1 Multi-Run Protocol

## Purpose

A single formal run is `model + provider + harness + trajectory`, not a stable
model level. V4.0 already showed Composer / HY-3 **92 → 82** on rerun (F6 only).

## Required meta (formal)

Always: `model`, `channel`, `harness` (`--require-meta`).

Recommended for multi-run:

| Field | CLI / env |
|-------|-----------|
| `run_group_id` | `--run-group-id` / `EVAL_RUN_GROUP_ID` |
| `run_index` | `--run-index` / `EVAL_RUN_INDEX` (1-based) |
| `thinking_level` | `--thinking-level` / `EVAL_THINKING_LEVEL` |
| `provider` | `--provider` |
| `endpoint_product` | `--endpoint-product` |
| `billing_tier` | `--billing-tier` |

Optional bag: `--meta-extra path.json` (tokens, cost, timing).

Missing multi-run fields → `meta.meta_partial=true`; review should mark `single-obs`
if n=1.

## Scoreboard rules

1. Group key: `model + channel + harness + thinking_level` (and provider when known).
2. **n ≥ 2:** main Ability = **worst** formal Ability; appendix best/worst/range.
3. **n = 1:** main Ability with label `single-obs`; do not claim stability.
4. Never write range as “方差 ±10”.
5. V4.0 lucky 92 runs stay in V4.0 archive / appendix only — not V4.1 main column.

## Interpretation limit

The V4.1b scoreboard keeps `worst` as its conservative operational main column,
but `worst-of-2` and a single observation are not statistically equivalent.
Testing a model more often creates more opportunities to observe a lower run.

- Treat n=1 rows as provisional.
- Treat worst as the lowest observed delivery, not an estimated population floor.
- Do not infer that an n=1 score above an n=2 worst is the more reliable model.
- A future benchmark should use a fixed formal run count and separate first-run
  Ability from reliability/failure-rate reporting.

## Family hotspots to report

At least: F6, F3 ambient, F4 voice, F8/F9 ESP.
