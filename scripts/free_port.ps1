param(
    [int]$Port = 8100,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue

if (-not $connections) {
    Write-Host "Port $Port is already free." -ForegroundColor Green
    return
}

Write-Host "The following processes currently own port ${Port}:" -ForegroundColor Yellow
$connections |
    Select-Object LocalAddress, LocalPort, State, OwningProcess |
    Sort-Object OwningProcess |
    Format-Table -AutoSize

$uniquePids = $connections |
    Select-Object -ExpandProperty OwningProcess -Unique

if (-not $Force) {
    Write-Warning "Re-run with -Force to terminate these processes automatically."
    return
}

foreach ($procId in $uniquePids) {
    if ($procId -eq 0) {
        Write-Warning "Skipping PID 0 (System Idle), cannot terminate."
        continue
    }
    try {
        $proc = Get-Process -Id $procId -ErrorAction Stop
        Write-Host "Stopping PID ${procId} ($($proc.ProcessName))" -ForegroundColor Cyan
        Stop-Process -Id $procId -Force -ErrorAction Stop
    } catch {
        Write-Warning "Failed to stop PID ${procId}: $($_.Exception.Message)"
    }
}

Start-Sleep -Seconds 1

if (Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue) {
    Write-Warning "Port $Port is still in use. Manual intervention may be required."
} else {
    Write-Host "Port $Port is now free." -ForegroundColor Green
}
