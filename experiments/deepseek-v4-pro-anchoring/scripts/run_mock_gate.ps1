param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
)

$ErrorActionPreference = 'Stop'
$experimentRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$dshHome = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $HOME '.dsh' }
$presetHome = Join-Path $dshHome '.agent-presets'
$privateRoot = Join-Path $experimentRoot 'private\mock'
$publicOutput = Join-Path $experimentRoot 'artifacts\schema-gate.json'
$promptFile = Join-Path $experimentRoot 'mock-prompt.txt'
$driver = Join-Path $PSScriptRoot 'dsh_session_driver.mjs'
$server = Join-Path $PSScriptRoot 'mock_deepseek_server.mjs'
$validator = Join-Path $PSScriptRoot 'validate_presets.py'

function Install-Preset([string]$Name) {
    $source = Join-Path $RepositoryRoot "tools\deepseek-harness-presets\$Name"
    $target = Join-Path $presetHome $Name
    if (Test-Path $target) {
        $sourceHashes = Get-ChildItem -Recurse -File $source | ForEach-Object {
            [pscustomobject]@{ Relative = [IO.Path]::GetRelativePath($source, $_.FullName); Hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash }
        }
        $targetHashes = Get-ChildItem -Recurse -File $target | ForEach-Object {
            [pscustomobject]@{ Relative = [IO.Path]::GetRelativePath($target, $_.FullName); Hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash }
        }
        if (($sourceHashes | ConvertTo-Json -Compress) -ne ($targetHashes | ConvertTo-Json -Compress)) {
            throw "DSH preset 目标已存在且内容不同：$target"
        }
        return
    }
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    Copy-Item -Path (Join-Path $source '*') -Destination $target -Recurse
}

function Wait-Tcp([int]$Port, [Diagnostics.Process]$Process) {
    $deadline = [DateTimeOffset]::UtcNow.AddSeconds(15)
    while ([DateTimeOffset]::UtcNow -lt $deadline) {
        if ($Process.HasExited) { throw "mock server 提前退出：$($Process.ExitCode)" }
        $client = [Net.Sockets.TcpClient]::new()
        try {
            $client.Connect('127.0.0.1', $Port)
            return
        } catch {
            Start-Sleep -Milliseconds 200
        } finally {
            $client.Dispose()
        }
    }
    throw "mock server 端口 $Port 启动超时"
}

Install-Preset 'anchored-standard'
Install-Preset 'minimal-full'
New-Item -ItemType Directory -Force -Path $privateRoot,(Split-Path $publicOutput) | Out-Null

$oldBaseUrl = $env:DEEPSEEK_BASE_URL
$oldApiKey = $env:DEEPSEEK_API_KEY
$oldMockPort = $env:MOCK_PORT
$oldMockOutput = $env:MOCK_OUTPUT
try {
    $requestFiles = @{}
    $runs = @(
        @{ Name = 'standard'; Port = 32190 },
        @{ Name = 'minimal-full'; Port = 32191 },
        @{ Name = 'anchored-standard'; Port = 32192 }
    )
    foreach ($run in $runs) {
        $name = $run.Name
        $port = $run.Port
        $runDir = Join-Path $privateRoot $name
        New-Item -ItemType Directory -Force -Path $runDir | Out-Null
        $requestFile = Join-Path $runDir 'requests.json'
        $env:MOCK_PORT = [string]$port
        $env:MOCK_OUTPUT = $requestFile
        $env:DEEPSEEK_BASE_URL = "http://127.0.0.1:$port"
        $env:DEEPSEEK_API_KEY = 'mock-key'
        $stdout = Join-Path $runDir 'mock.stdout.log'
        $stderr = Join-Path $runDir 'mock.stderr.log'
        $process = Start-Process -FilePath (Get-Command node).Source -ArgumentList @($server) -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
        try {
            Wait-Tcp -Port $port -Process $process
            & node $driver --cwd $RepositoryRoot --preset $name --prompt-file $promptFile --private-output $runDir --timeout-seconds 120
            if ($LASTEXITCODE -ne 0) { throw "DSH mock run $name 失败，exit=$LASTEXITCODE" }
            $requestFiles[$name] = $requestFile
        } finally {
            if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
            $process.WaitForExit()
        }
    }
    & python $validator --standard $requestFiles['standard'] --minimal-full $requestFiles['minimal-full'] --anchored $requestFiles['anchored-standard'] --output $publicOutput
    if ($LASTEXITCODE -ne 0) { throw "preset semantic gate 失败，exit=$LASTEXITCODE" }
} finally {
    $env:DEEPSEEK_BASE_URL = $oldBaseUrl
    $env:DEEPSEEK_API_KEY = $oldApiKey
    $env:MOCK_PORT = $oldMockPort
    $env:MOCK_OUTPUT = $oldMockOutput
}

Write-Output "schema gate: $publicOutput"
