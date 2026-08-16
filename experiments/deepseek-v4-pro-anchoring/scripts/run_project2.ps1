param(
    [Parameter(Mandatory = $true)][ValidateSet('standard','minimal-full','anchored-standard')][string]$Preset,
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
)

$ErrorActionPreference = 'Stop'
$experimentRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$privateRun = Join-Path $experimentRoot "private\project2\$RunId"
$publicRun = Join-Path $experimentRoot "artifacts\runs\$RunId.json"
$baseline = Join-Path $experimentRoot 'artifacts\environment-baseline.json'
$price = Join-Path $experimentRoot 'artifacts\price-snapshot.json'
$prompt = Join-Path $privateRun 'candidate-prompt.txt'
$workspace = Join-Path $RepositoryRoot 'workspace'
$session = Join-Path $privateRun 'session.jsonl'
$sessionMeta = Join-Path $privateRun 'session-meta.json'
$driver = Join-Path $PSScriptRoot 'dsh_session_driver.mjs'
$analyzer = Join-Path $PSScriptRoot 'analyze_session.py'

if (-not (Test-Path $baseline)) { throw "缺少 baseline：$baseline" }
if (-not (Test-Path $price)) { throw "缺少价格快照：$price" }
if (Test-Path $privateRun) { throw "run ID 已存在：$RunId" }
if ($env:DEEPSEEK_BASE_URL) { throw "正式 DSH run 检测到 DEEPSEEK_BASE_URL override" }
$dshHomeForSettings = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $HOME '.dsh' }
$settingsPath = Join-Path $dshHomeForSettings 'settings.yaml'
if ((Test-Path $settingsPath) -and (Select-String -Path $settingsPath -Pattern 'baseURL|baseUrl' -Quiet)) {
    throw "正式 DSH run 检测到 settings endpoint override"
}
New-Item -ItemType Directory -Force -Path $privateRun,(Split-Path $publicRun) | Out-Null

& python (Join-Path $PSScriptRoot 'extract_candidate_prompt.py') --source (Join-Path $RepositoryRoot 'CANDIDATE_PROMPT.md') --output $prompt
if ($LASTEXITCODE -ne 0) { throw "候选提示提取失败，exit=$LASTEXITCODE" }

& python (Join-Path $RepositoryRoot 'evaluator\make_broken_project.py')
if ($LASTEXITCODE -ne 0) { throw "Project2 reset 失败，exit=$LASTEXITCODE" }

$baselineData = Get-Content $baseline -Raw | ConvertFrom-Json
$presetHash = $baselineData.preset_hashes.$Preset
if (-not $presetHash) { throw "baseline 缺少 preset hash：$Preset" }

& node $driver --cwd $workspace --preset $Preset --prompt-file $prompt --private-output $privateRun --timeout-seconds 4500 --provider deepseek-official --model deepseek-v4-pro --reasoning-effort max
if ($LASTEXITCODE -ne 0) { throw "DSH run $RunId 失败，exit=$LASTEXITCODE" }

$metaExtra = Join-Path $privateRun 'meta-extra.json'
& python $analyzer --session $session --session-meta $sessionMeta --benchmark project2-v4.1b --task-id project2-v4-broken-seed --run-id $RunId --dsh-version 0.1.0-rc.6 --dsh-commit 47f943859bef60e4160492346772ded9b24f765a --preset-hash $presetHash --benchmark-commit 04255b55f16c4439e538239fb9783070c4165081 --price $price --output $metaExtra
if ($LASTEXITCODE -ne 0) { throw "session 初次分析失败，exit=$LASTEXITCODE" }

$before = @(Get-ChildItem (Join-Path $RepositoryRoot 'evaluator\results') -Directory | ForEach-Object FullName)
& python (Join-Path $RepositoryRoot 'evaluator\run_full_eval.py') (Join-Path $workspace 'project2_task') --model DeepSeek-V4-Pro --channel deepseek-official --harness "dsh-$Preset" --require-meta --run-group-id "dsv4p-anchor-20260815-$Preset" --run-index 1 --thinking-level max --provider DeepSeek --endpoint-product DeepSeek-API --billing-tier paygo --meta-extra $metaExtra
$evalExit = $LASTEXITCODE
$after = @(Get-ChildItem (Join-Path $RepositoryRoot 'evaluator\results') -Directory | Where-Object { $_.FullName -notin $before })
if ($after.Count -ne 1) { throw "evaluator 新结果目录数量应为 1，实际为 $($after.Count)" }
$summary = Join-Path $after[0].FullName 'summary.json'
if (-not (Test-Path $summary)) { throw "evaluator 缺少 summary.json：$($after[0].Name)" }

& python $analyzer --session $session --session-meta $sessionMeta --benchmark project2-v4.1b --task-id project2-v4-broken-seed --run-id $RunId --dsh-version 0.1.0-rc.6 --dsh-commit 47f943859bef60e4160492346772ded9b24f765a --preset-hash $presetHash --benchmark-commit 04255b55f16c4439e538239fb9783070c4165081 --price $price --result $summary --output $publicRun
if ($LASTEXITCODE -ne 0) { throw "session 最终分析失败，exit=$LASTEXITCODE" }

$result = Get-Content $publicRun -Raw | ConvertFrom-Json
Write-Output ([pscustomobject]@{
    run_id = $RunId
    preset = $Preset
    evaluator_exit = $evalExit
    evaluator_result_id = $after[0].Name
    ability = $result.benchmark_result.ability_draft
    ship = $result.benchmark_result.ship_draft
    class = $result.benchmark_result.release_class_hint
    cost_cny = $result.api_cost_cny
} | ConvertTo-Json -Compress)
