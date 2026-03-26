param(
    [string]$ProjectRoot = "F:\DrumTracKAI_v1.1.17",
    [int]$FrontendPort = 3002,
    [int]$BackendPort = 8000,
    [string]$FrontendLogPath = ".\logs\frontend-dev.log",
    [switch]$SkipFrontend,
    [switch]$SkipBrowser,
    [switch]$TailBackendLog
)

$ErrorActionPreference = "Stop"

function Resolve-PathAllowMissing {
    param(
        [string]$BasePath,
        [string]$Target
    )

    if ([string]::IsNullOrWhiteSpace($Target)) {
        return $null
    }

    if ([System.IO.Path]::IsPathRooted($Target)) {
        if (Test-Path $Target) {
            return (Resolve-Path $Target).Path
        }
        return [System.IO.Path]::GetFullPath($Target)
    }

    $joined = Join-Path $BasePath $Target
    if (Test-Path $joined) {
        return (Resolve-Path $joined).Path
    }
    return [System.IO.Path]::GetFullPath($joined)
}

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$freePortScript = Join-Path $scriptDir "free_port.ps1"
$orchestrator = Join-Path $scriptDir "orchestrate_dev.ps1"

if (-not (Test-Path $freePortScript)) {
    throw "free_port.ps1 not found at $freePortScript"
}
if (-not (Test-Path $orchestrator)) {
    throw "orchestrate_dev.ps1 not found at $orchestrator"
}

Write-Host "Clearing frontend port $FrontendPort" -ForegroundColor Cyan
& $freePortScript -Port $FrontendPort -Force | Out-Null

Write-Host "Clearing backend port $BackendPort" -ForegroundColor Cyan
& $freePortScript -Port $BackendPort -Force | Out-Null

$resolvedFrontendLog = Resolve-PathAllowMissing -BasePath $ProjectRoot -Target $FrontendLogPath
if ($resolvedFrontendLog) {
    $logParent = Split-Path -Parent $resolvedFrontendLog
    if ($logParent -and -not (Test-Path $logParent)) {
        New-Item -ItemType Directory -Path $logParent -Force | Out-Null
    }
}

$orchestratorParams = @{
    ProjectRoot = $ProjectRoot
    BackendPort = $BackendPort
    FrontendPort = $FrontendPort
}
if ($resolvedFrontendLog) {
    $orchestratorParams["FrontendLogPath"] = $resolvedFrontendLog
}
if ($SkipFrontend) { $orchestratorParams["SkipFrontend"] = $true }
if ($SkipBrowser) { $orchestratorParams["SkipBrowser"] = $true }
if ($TailBackendLog) { $orchestratorParams["TailBackendLog"] = $true }

Write-Host "Starting orchestrator" -ForegroundColor Cyan
& $orchestrator @orchestratorParams