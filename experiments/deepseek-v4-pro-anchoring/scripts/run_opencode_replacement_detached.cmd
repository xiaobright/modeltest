@echo off
setlocal
set "EXP=%~dp0.."
set "REPO=%~dp0..\..\.."
set "RUN=P2-20260815-04b-opencode-replacement"
set "LOGDIR=%EXP%\private\opencode-run"
python "%EXP%\scripts\run_opencode_agent.py" --workspace "%REPO%\workspace" --prompt "%LOGDIR%\candidate-prompt-%RUN%.txt" --private-run "%EXP%\private\project2\%RUN%" --models-catalog "%LOGDIR%\models-20260815.json" --t0-balance "%EXP%\private\pricing\balance-%RUN%-t0-b.json" --run-id "%RUN%" --timeout-seconds 4500 --cost-stop-cny 3.75 --balance-poll-seconds 60 1> "%LOGDIR%\%RUN%.runner.stdout.log" 2> "%LOGDIR%\%RUN%.runner.stderr.log"
exit /b %ERRORLEVEL%
