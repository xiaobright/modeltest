param(
    [string]$ProjectDir = (Join-Path $PSScriptRoot "..\project2_task"),
    [string]$Target = "esp32s3",
    [string]$ActivationScript = $env:ESP_IDF_ACTIVATION_SCRIPT,
    [string]$BuildRoot = "",
    [int]$Jobs = 0,
    [switch]$CleanCopy,
    [switch]$SetTarget
)

$ErrorActionPreference = "Stop"

$pythonRunner = Join-Path $PSScriptRoot "run_espidf_build.py"
$argsList = @(
    $ProjectDir,
    "--target", $Target,
    "--activation-script", $ActivationScript
)
if ($BuildRoot) {
    $argsList += @("--build-root", $BuildRoot)
}
if ($Jobs -gt 0) {
    $argsList += @("--jobs", $Jobs)
}
if ($CleanCopy) {
    $argsList += "--clean-copy"
}
if ($SetTarget) {
    $argsList += "--set-target"
}

python $pythonRunner @argsList
exit $LASTEXITCODE
