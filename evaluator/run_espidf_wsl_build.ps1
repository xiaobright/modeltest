param(
    [string]$ProjectDir = (Join-Path $PSScriptRoot "..\workspace\project2_task"),
    [string]$Distro = "",
    [string]$WslWorkDir = "",
    [string]$Target = "esp32s3",
    [string]$ActivateScript = "",
    [string]$IdfPython = "",
    [string]$IdfPy = "",
    [string]$ActivationScript = $env:ESP_IDF_ACTIVATION_SCRIPT,
    [string]$BuildRoot = ""
)

$ErrorActionPreference = "Stop"

Write-Warning "[espidf] run_espidf_wsl_build.ps1 is deprecated. Using the Windows EIM ESP-IDF runner instead."
if ($Distro -or $WslWorkDir -or $ActivateScript -or $IdfPython -or $IdfPy) {
    Write-Host "[espidf] note=WSL-specific parameters were ignored."
}

$windowsRunner = Join-Path $PSScriptRoot "run_espidf_windows_build.ps1"
$params = @{
    ProjectDir = $ProjectDir
    Target = $Target
    ActivationScript = $ActivationScript
}
if ($BuildRoot) {
    $params.BuildRoot = $BuildRoot
}

& $windowsRunner @params
exit $LASTEXITCODE
