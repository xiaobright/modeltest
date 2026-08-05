# Project2 v2 Benchmark Notes

## Goal

The v2 benchmark is designed to separate mid-tier models that clustered around 50 points in v1, while still keeping admin/auth and context privacy as the first-tier divider.

Compared with v1, v2 shifts from "find everything from a weak prompt" toward a stronger debug workflow:

1. Run visible public tests.
2. Run `workspace/tools/run_debug_probe.py`.
3. Diagnose symptoms.
4. Implement fixes.
5. Re-run public/debug/ESP checks.
6. Write a factual `project2_task/PULL_REQUEST_TEMPLATE.md`.

## Main Changes

- `workspace/` is the active candidate-visible v2 benchmark.
- `evaluator/` is the active hidden evaluator state.
- First-round v1 project/results are archived under `archives/first_round_v1_20260612/`.
- `run_full_eval.py` now runs:
  - evaluator-owned public tests
  - evaluator-owned debug probe
  - hidden tests
  - ESP-IDF static contract checks
- Hidden summary includes bug-family aggregation.
- Scoring is family-based with caps, not raw hidden pass count.
- The project git repo is tagged with `project2-v2-broken-seed`; evaluator diffs use this tag so candidate commits do not hide changes.
- Evaluator-owned public/debug copies prevent candidate-edited visible tests from changing scoring.

## New Differentiators

- Process/reporting: requires initial and final debug evidence in `PULL_REQUEST_TEMPLATE.md`.
- DB migration: old `care_events` schema must upgrade without data loss.
- Context policy: sensitive target context requires explicit valid session.
- care_event contract: `limit`, descending order, normalized room/bed, and stable `ts`.
- ESP static contract: NVS keys, four topic suffixes, lowercase topic normalization, Wi-Fi/MQTT runtime, and `payload_b64`.
- Factual consistency: if `PULL_REQUEST_TEMPLATE.md` claims helper files such as `protocol_packet` or `mqtt_payload`, matching changed files must exist.

## Intended Difficulty Shape

- No admin/local auth boundary: capped near 65, but still differentiated by ESP, care_event, sleep, migration, and reporting.
- Admin fixed but context policy incomplete: likely 70-82.
- Good gateway but weak ESP/build evidence: likely 65-78.
- Full engineering closure with accurate reporting and ESP evidence: 85+.

The aim is to avoid the v1 failure mode where many mid-tier models missed the same root cause and all landed around the same score.
