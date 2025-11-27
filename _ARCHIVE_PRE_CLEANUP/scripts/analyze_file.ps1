# Copy and analyze audio file
$source = "C:\Users\dagol\OneDrive\Documents\Sound Recordings\Recording (2).m4a"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$dest = "uploads\$timestamp-Recording_2.m4a"

Write-Host "Copying audio file..." -ForegroundColor Cyan
Copy-Item $source $dest -ErrorAction Stop

Write-Host "File copied to: $dest" -ForegroundColor Green
Write-Host ""

# Extract just the filename
$filename = Split-Path $dest -Leaf

Write-Host "Analyzing with backend..." -ForegroundColor Cyan
Write-Host ""

# Call backend API
$response = Invoke-WebRequest -Uri "http://localhost:8000/waveform?key=$filename" -Method GET

Write-Host $response.Content
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host "File Key: $filename" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host ""
Write-Host "To load in React app, add this to URL:" -ForegroundColor Cyan
Write-Host "http://localhost:3000/?fileKey=$filename&filename=Recording_2.m4a" -ForegroundColor White
Write-Host ""
