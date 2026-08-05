# Project2 Evaluator Guide

This directory is the active **V4.0 frozen** evaluator control plane (V2-compatible workspace shell). Candidate models should only see the external allowlist workspace created by `prepare_candidate_handoff.py`.

V4 scoring: Ability + Ship + blockers. See `scoring/rubric.md`, `scoring/score_model.py`, and `reports/v4_scoreboard.md`.
Seed tag: `project2-v4-broken-seed` (also tags `project2-v2-broken-seed` for compatibility).
Gold (never hand to candidates): `archives/v4_gold/` — final verification result `evaluator/results/20260711_222515` (hidden 45/45, static 9/9, real build, Ability/Ship 100, Class A).

## Candidate Visibility Boundary

The boundary is part of the test design:

- Run `prepare_candidate_handoff.py` and give candidates only its printed `candidate_workspace`.
- Do not hand out the live staging `workspace/` directory as a whole; it may contain terminal or MCP state.
- Do not expose `model_eval/evaluator/`, hidden tests, scoring files, broken seed generation details, archived results, or good-version diffs.
- The evaluator may read the whole `model_eval/` tree, reset the workspace, run tests, collect logs, and apply the rubric.

The candidate-visible task is intentionally self-contained in:

- `workspace/ONBOARDING_TODO.md`
- `workspace/reference/`
- `workspace/tests/public/`
- `workspace/tools/`
- `workspace/project2_task/`

## Layout

- `workspace/project2_task/`: candidate edits this broken project. This directory is a git repo whose HEAD represents the v2 broken seed state.
- `workspace/project2_task/PULL_REQUEST_TEMPLATE.md`: candidate fills this required implementation report.
- `workspace/ONBOARDING_TODO.md`: public task prompt.
- `workspace/reference/`: public contracts and examples.
- `workspace/tests/public/`: public tests for candidate self-debug.
- `workspace/tools/run_debug_probe.py`: required visible diagnostic probe for candidate self-debug.
- `evaluator/broken_backup/project2_broken_seed/`: reset seed, also a git repo.
- `evaluator/tests/run_public_tests.py` and `evaluator/tests/public/`: evaluator-owned public test copy used by `run_full_eval.py`.
- `evaluator/tools/run_debug_probe.py`: evaluator-owned debug probe copy used by `run_full_eval.py`.
- `evaluator/tests/hidden/`: hidden tests.
- `evaluator/tests/espidf_static/`: ESP-IDF static contract tests.
- `evaluator/scoring/`: rubric and reviewer prompt.
- `evaluator/results/`: logs and git artifacts for new evaluation runs.

The evaluator-owned public/debug copies are intentional. Candidates can modify visible helper tests while working, but scoring should not depend on candidate-edited test files.

## Git Workflow

`workspace/project2_task/` is initialized as a git repository whose HEAD captures the v2 broken seed state. This serves several purposes:

- Candidate exploration: models can use `git status`, `git diff`, and `git log` to understand the project state.
- Fast reset: `git checkout . && git clean -fdx` restores the workspace without a full copy from seed.
- Diff collection: `git diff project2-v2-broken-seed` captures the complete set of candidate changes even if the candidate made commits.
- Commit tracking: if the candidate model commits its work, `git log` shows its development process.

The git repo is created automatically by `make_broken_project.py`. The `.gitignore` covers Python caches, project databases, build artifacts, logs, and OS/IDE metadata.

## Generate Or Reset

From project root:

```powershell
python evaluator\make_broken_project.py
```

By default this resets `workspace/project2_task`. If the workspace already has a git repo matching the seed, it uses git checkout/clean for a fast reset. Otherwise it copies from `evaluator/broken_backup/project2_broken_seed/`.

To refresh the broken seed from a completed source tree:

```powershell
python evaluator\make_broken_project.py --source E:\path\to\completed_project2
```

## Candidate-Visible Public Checks

These are the commands candidates are asked to run before and after changes:

```powershell
python workspace\tests\run_public_tests.py workspace\project2_task
python workspace\tools\run_debug_probe.py workspace\project2_task
python workspace\tools\run_espidf_build.py workspace\project2_task
```

## Hidden And Full Evaluation

Run hidden tests only:

```powershell
python evaluator\run_hidden_tests.py workspace\project2_task
```

For structured scoring evidence:

```powershell
python evaluator\run_hidden_tests.py workspace\project2_task --summary-json evaluator\results\manual_hidden_summary.json
```

Run the normal full eval:

```powershell
python evaluator\run_full_eval.py workspace\project2_task
```

With reset:

```powershell
python evaluator\run_full_eval.py --reset
```

ESP-IDF build verification:

```powershell
python evaluator\run_full_eval.py --include-espidf-build
```

`run_full_eval.py` runs evaluator-owned public tests, evaluator-owned debug probe, hidden tests, and ESP-IDF static contract checks. Use `--skip-espidf-static` only for evaluator debugging, not for normal scoring.

## Collect Candidate Diff

The workspace is a git repo, so collecting changes is straightforward:

```powershell
cd workspace\project2_task
git diff project2-v2-broken-seed
git status --short
git log --oneline
```

When `run_full_eval.py` is used, git artifacts are collected automatically into the newest timestamped directory under `evaluator/results/`:

- `candidate_diff.patch`: full diff against `project2-v2-broken-seed`.
- `candidate_status.txt`: `git status --short` summary.
- `candidate_log.txt`: `git log --oneline` output.
- `pull_request_template.md`: developer's required PR description copied from `project2_task/PULL_REQUEST_TEMPLATE.md`.

To skip git diff collection:

```powershell
python evaluator\run_full_eval.py --no-diff workspace\project2_task
```

Fallback if the workspace is somehow not a git repo:

```powershell
git diff --no-index evaluator\broken_backup\project2_broken_seed workspace\project2_task
```

If `git diff --no-index` exits with code `1`, that only means differences were found. Treat the output as review input rather than a command failure.

## ESP-IDF Windows Build

ESP32-S3 firmware repair is part of the required task. `run_full_eval.py` always runs static ESP-IDF contract checks. When the candidate modifies `esp32/testpro4`, CMake, TinyUSB, NVS, MQTT/USB packet code, protocol constants, or `sdkconfig`, also run the ESP-IDF build verification when the Windows EIM environment is available.

From the evaluator:

```powershell
python evaluator\run_espidf_build.py workspace\project2_task
```

Candidate-visible companion scripts:

```powershell
python workspace\tools\run_espidf_build.py workspace\project2_task
powershell -ExecutionPolicy Bypass -File workspace\tools\run_espidf_windows_build.ps1 -ProjectDir workspace\project2_task
```

The Python script incrementally mirrors `esp32/testpro4` to a guarded Windows build directory, activates ESP-IDF through EIM, enables ccache, and builds through CMake/Ninja with explicit parallel jobs. By default it keeps the guarded copy and `build` directory so repeated candidate fixes can reuse ESP-IDF, Ninja, and ccache state.

Important details:

- The Windows activation script path is `$env:ESP_IDF_ACTIVATION_SCRIPT`.
- The build copies `esp32/testpro4` into `$env:ESP_IDF_BUILD_ROOT\project2_task`.
- Default build mode is incremental. Use the plain command while a model is iterating on firmware fixes.
- After resetting the benchmark project, or when a completely fresh firmware build is specifically needed, use `--clean-copy --set-target` once:

```powershell
python workspace\tools\run_espidf_build.py workspace\project2_task --clean-copy --set-target
```

- Parallelism defaults to the logical CPU count. Override with `--jobs N` only if the machine is overloaded or needs a different throttle.
- This is build-only. Do not require `idf.py flash`, `idf.py monitor`, real USB enumeration, Wi-Fi/MQTT connectivity, ToF cold-start timing, or real MLX90640 readings.

Interpretation:

- If ESP-IDF static checks fail, treat that as a required-task failure, not an optional-task miss.
- If ESP-IDF was touched and the build test is available, a failed build is evidence for regression compatibility deductions.
- If the environment itself is missing or unavailable, record that separately from candidate code quality.

## Scoring

Use `scoring/rubric.md`. Hidden tests are important, but architecture, privacy, and factual reporting still require code review. When `run_full_eval.py` is used, read `hidden_summary.json` and `espidf_static_summary.json` in the newest results directory for testcase-level evidence.

Automatic failure or severe cap examples:

- Core Python cannot compile.
- Gateway cannot import/start.
- Real `data/project2.db` is used for tests.
- Admin password is stored plaintext.
- Unauthenticated context leaks patient data, memories, vitals, or care events.
- Remote unauthenticated users can export face/credential templates.
- `project2_task/PULL_REQUEST_TEMPLATE.md` is missing, empty, or materially inconsistent with the diff/test logs.
- ESP32-S3 Wi-Fi + MQTT static contract is not restored.
- Candidate modifies tests/tools to fake a pass instead of fixing project code.
- Candidate hardcodes test IDs or fixed responses.

The generated v2 broken seed is expected to pass compile/smoke checks, fail the visible refactored/debug checks, and fail hidden/static checks across multiple families. That is intentional: candidates must debug from visible symptoms and then close the hidden edge cases.
