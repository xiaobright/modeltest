# Project2 V4 — implemented notes

V4 is active on the evaluator side (2026-07-11).

## What changed vs V2

- Dual scores: Ability + Ship + blockers + confidence artifacts  
- F3/F12 split tests; ambient is not an 82 hard wall  
- F4 voice bridge, F6 multi-step migration, F7 mixed CSV, F8 buffer check  
- Seed tag `project2-v4-broken-seed` (+ legacy v2 tag for compatibility)  
- `data/legacy_sample.db` sample; public tests still use TEMP DB  
- Scoreboard: `reports/v4_scoreboard.md` Ability-first  

## Commands

```powershell
python evaluator\make_broken_project.py
python evaluator\run_full_eval.py workspace\project2_task
python evaluator\scoring\score_model.py evaluator\results\<id> --write
```

## Docs

Current state: `docs/v4/CURRENT_STATE_VS_ORIGINAL_DESIGN.md`. Historical design and handoff:
`docs/v4/archive/original_design/`.  
V2 freeze: `archives/second_round_v2_final_20260711/`.
