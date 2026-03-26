param(
    [string]$ProjectRoot = "F:\DrumTracKAI_v1.1.17",
    [string]$FrontendPath = "frontend",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3002,
    [string]$FrontendLogPath = "",
    [switch]$SkipFrontend,
    [switch]$SkipBrowser,
    [switch]$TailBackendLog
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
    param(
        [string]$BasePath,
        [string]$MaybeRelative,
        [switch]$AllowMissing
    )

    if ([string]::IsNullOrWhiteSpace($MaybeRelative)) {
        throw "Path value cannot be empty."
    }

    if ([System.IO.Path]::IsPathRooted($MaybeRelative)) {
        if (Test-Path $MaybeRelative) {
            return (Resolve-Path $MaybeRelative).Path
        }
        if ($AllowMissing) {
            return [System.IO.Path]::GetFullPath($MaybeRelative)
        }
        throw "Path '$MaybeRelative' was not found."
    }

    $candidate = Join-Path $BasePath $MaybeRelative
    if (Test-Path $candidate) {
        return (Resolve-Path $candidate).Path
    }
    if ($AllowMissing) {
        return [System.IO.Path]::GetFullPath($candidate)
    }
    throw "Path '$candidate' was not found."
}

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$FrontendPath = Resolve-ProjectPath -BasePath $ProjectRoot -MaybeRelative $FrontendPath

$scriptDir = Join-Path $ProjectRoot "scripts"
$freePortScript = Join-Path $scriptDir "free_port.ps1"
$backendScript = Join-Path $scriptDir "start_backend_with_logging.ps1"

if (-not (Test-Path $freePortScript)) { throw "Missing $freePortScript" }
if (-not (Test-Path $backendScript)) { throw "Missing $backendScript" }

Write-Host "[1/4] Ensuring backend port $BackendPort is free" -ForegroundColor Cyan
& $freePortScript -Port $BackendPort -Force

function Start-InNewWindow {
    param([string]$Title, [string]$Command, [string]$WorkingDirectory)
    $args = @('-NoLogo','-NoExit','-ExecutionPolicy','Bypass','-Command',$Command)
    Start-Process -FilePath "powershell.exe" -ArgumentList $args -WorkingDirectory $WorkingDirectory -WindowStyle Normal -Verb Open | Out-Null
    if ($Title) { Write-Host "Started $Title" -ForegroundColor Green }
}

function Quote-Single {
    param([string]$Value)
    return $Value -replace "'", "''"
}

$escapedBackend = Quote-Single $backendScript
$escapedRoot = Quote-Single $ProjectRoot
$backendCommand = "& '$escapedBackend' -ProjectRoot '$escapedRoot' -Port $BackendPort"
Write-Host "[2/4] Launching backend with logging" -ForegroundColor Cyan
Start-InNewWindow -Title "backend" -Command $backendCommand -WorkingDirectory $ProjectRoot

if ($TailBackendLog) {
    $tailScript = @'
param(
    [string]$ProjectRoot,
    [int]$BackendPort
)
Set-Location $ProjectRoot
$logDir = Join-Path $ProjectRoot 'logs'
while (-not (Test-Path $logDir)) { Start-Sleep -Seconds 1 }
Write-Host "Waiting for backend log..." -ForegroundColor Yellow
$latest = $null
while (-not $latest) {
    $latest = Get-ChildItem $logDir -Filter 'backend-*.log' | Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $latest) { Start-Sleep -Seconds 1 }
}
Write-Host "Tailing $($latest.FullName)" -ForegroundColor Yellow
Get-Content $latest.FullName -Tail 80 -Wait
'@
    $tempTail = New-TemporaryFile
    Set-Content -Path $tempTail -Value $tailScript -Encoding ASCII
    $tailCommand = "& '$($tempTail.FullName)' -ProjectRoot '$escapedRoot' -BackendPort $BackendPort"
    Start-InNewWindow -Title "backend-log" -Command $tailCommand -WorkingDirectory $ProjectRoot
}

if (-not $SkipFrontend) {
    Write-Host "[3/4] Launching frontend dev server on port $FrontendPort" -ForegroundColor Cyan
    $escapedFrontendPath = Quote-Single $FrontendPath
    if ([string]::IsNullOrWhiteSpace($FrontendLogPath)) {
        $frontendCommand = ([string]::Format('$env:PORT={0}; Set-Location ''{1}''; npm run dev', $FrontendPort, $escapedFrontendPath))
    } else {
        $resolvedLog = Resolve-ProjectPath -BasePath $ProjectRoot -MaybeRelative $FrontendLogPath -AllowMissing
        $frontendCommand = ([string]::Format('$env:PORT={0}; Set-Location ''{1}''; npm run dev *>&1 | Tee-Object -FilePath ''{2}'' -Append', $FrontendPort, $escapedFrontendPath, (Quote-Single $resolvedLog)))
        Write-Host "Frontend output -> $resolvedLog" -ForegroundColor Yellow
        $logParent = Split-Path -Parent $resolvedLog
        if ($logParent -and -not (Test-Path $logParent)) {
            New-Item -ItemType Directory -Path $logParent -Force | Out-Null
        }
    }
    Start-InNewWindow -Title "frontend" -Command $frontendCommand -WorkingDirectory $FrontendPath
} else {
    Write-Host "[3/4] Skipping frontend launch" -ForegroundColor DarkYellow
}

if (-not $SkipBrowser) {
    Write-Host "[4/4] Opening browser" -ForegroundColor Cyan
    $url = "http://localhost:$FrontendPort"
    Start-Process $url | Out-Null
} else {
    Write-Host "[4/4] Browser launch skipped" -ForegroundColor DarkYellow
}

Write-Host "Automation complete. Backend and frontend consoles are running in separate windows." -ForegroundColor Green
