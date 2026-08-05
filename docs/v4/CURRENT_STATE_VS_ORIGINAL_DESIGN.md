# V4.0 Current State vs Original Design

**Date:** 2026-07-11  
**Current state:** implemented, calibrated and frozen

## 1. What the Original Documents Were

The material under `archive/original_design/` is the design package assembled before V4
implementation. It combined V2/V3.1 diagnosis, scoring proposals, item authoring, seed changes,
pipeline plans, migration strategy and reviews from several models.

It is valuable as decision history, but it is not a literal description of the final repository.
Some sections deliberately present alternatives, future work or provisional acceptance gates.

## 2. What Was Implemented as Designed

| Original direction | Current implementation |
|---|---|
| Ability and Ship are separate views | Implemented; official ranking is Ability-first, Ship/Class describe release risk |
| Remove the ambient 82-point wall | Implemented; `S-ambient` deducts item points and affects Class without forcing Ability to 82 |
| Split context behavior from reason semantics | Implemented as F3 behavior and F12 semantic-only items |
| Add high-coupling migration, mixed CSV and voice bridge checks | Implemented in hidden tests and item registry |
| Separate ESP static contract from real build evidence | Implemented as F8 and F9 |
| Preserve V2 history and calibrate against real reruns | Implemented; V2 has a 24-result freeze and V4 has seven formal reruns |
| Maintain a frozen Gold implementation | Implemented; final Gold result is `20260711_222515`, 100/A |

The 12-family, 100-point structure survived substantially intact. The final Gold reaches full
credit, so the scale has a demonstrated top endpoint rather than a theoretical one.

## 3. Important Differences and Hardening Added During Implementation

### Evidence became stricter than the initial plan

- Formal runs require non-empty `model`, `channel` and `harness` via `--require-meta`.
- F9=6 requires result-local build log, firmware, size and SHA256 validation.
- A successful build exit code by itself is not enough for full credit.
- First-round F9 evidence without archived artifacts is explicitly marked
  `operator_attested_legacy` in the freeze manifest.

### Release blockers were separated more precisely

- Ship/Class use behavior blockers only.
- Reason-only mismatches remain in F12 and cannot create behavior caps.
- `blockers.json`, `summary.json`, dimensions and score draft are written consistently.

### F11 changed from a loose report heuristic to a guarded heuristic

The first implementation treated retained template wording as an unfinished report. The frozen
scorer distinguishes standalone placeholders from substantive content and has regression tests for
filled reports that retain template headings or discuss removed placeholder text.

### Candidate isolation became an explicit mechanism

The original workflow often described giving the candidate `workspace/`. The frozen workflow uses
`prepare_candidate_handoff.py`, which creates an external allowlist workspace and excludes live
terminal/MCP state, evaluator files, archives and root documentation. It also rejects Git histories
containing extra commits, refs, reflog heads or unreachable objects before copying.

### Gold verification became stronger

Early Gold checks either targeted live workspace content or skipped the real toolchain. The final
verification directly evaluates `archives/v4_gold/project2_task`, builds with Windows EIM
ESP-IDF v6.0.1, archives the firmware in the result and validates its hash.

## 4. Original Ideas Not Included in V4.0

- The capstone proposals in `CAPSTONE_ITEM_IDEAS.md` were not added to the frozen 100-point V4.0
  registry. They remain candidates for V4.1+ if the top of the leaderboard becomes crowded.
- Hardware flash/monitor, real Wi-Fi/MQTT connectivity and physical sensor behavior remain outside
  automatic scoring.
- Historical V2 relabel tables remain explanatory only; formal V4 rankings come from V4 reruns.
- Efficiency and harness friction are recorded narratively and do not affect Ability.

## 5. Current Operational State

The live `evaluator/results/` directory now contains only:

- one canonical broken-seed smoke result (`20260711_174033`);
- seven formal model results;
- the final Gold verification (`20260711_222515`).

V2 results remain in `archives/second_round_v2_final_20260711/`. Historical Gold verification
`20260711_214920` remains under `archives/v4_gold/verification_20260711_214920/`.

## 6. Source-of-Truth Order

When the original design and current behavior differ, use this order:

1. `evaluator/reports/v4_freeze_manifest.md`
2. `evaluator/scoring/rubric.md` and `item_registry.json`
3. evaluator code and tests
4. `evaluator/reports/v4_scoreboard.md` and formal reviews
5. this current-state explanation
6. archived original design and cross-review material

Changing the scorer, rubric, registry or key hidden tests after this point should be treated as a
V4.1+ change and should trigger the Gold gate again.
