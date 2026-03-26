param(
    [string]$ProjectRoot = "F:\DrumTracKAI_v1.1.17",
    [int]$Port = 8000,
    [string]$LogDirectory = "logs",
    [string]$LogPrefix = "backend"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ProjectRoot)) {
    throw "Project root '$ProjectRoot' was not found."
}

$pythonPath = Join-Path $ProjectRoot ".venv\\Scripts\\python.exe"
$backendEntry = Join-Path $ProjectRoot "dcsm_backend.py"

if (-not (Test-Path $pythonPath)) {
    throw "Python executable not found at '$pythonPath'. Activate the virtual environment first."
}

if (-not (Test-Path $backendEntry)) {
    throw "Backend entry script not found at '$backendEntry'."
}

if ([System.IO.Path]::IsPathRooted($LogDirectory)) {
    $resolvedLogDirectory = $LogDirectory
} else {
    $resolvedLogDirectory = Join-Path $ProjectRoot $LogDirectory
}

if (-not (Test-Path $resolvedLogDirectory)) {
    New-Item -ItemType Directory -Path $resolvedLogDirectory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $resolvedLogDirectory ("{0}-{1}.log" -f $LogPrefix, $timestamp)

Write-Host "Starting backend from $backendEntry" -ForegroundColor Cyan
Write-Host "API_PORT set to $Port" -ForegroundColor Cyan
Write-Host "Streaming output to $logFile" -ForegroundColor Cyan

$env:API_PORT = $Port

Push-Location $ProjectRoot
$previousErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    & $pythonPath $backendEntry *>&1 | Tee-Object -FilePath $logFile -Append
    $exitCode = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $previousErrorAction
    Pop-Location
}

if ($exitCode -and $exitCode -ne 0) {
    Write-Warning "Backend process exited with code $exitCode"
}
