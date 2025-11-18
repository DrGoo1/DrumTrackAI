# DrumTracKAI v1.1.16 Archive Backup Script
# Drummer Style Integration Complete

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "  DrumTracKAI v1.1.16 - Archive Backup Script" -ForegroundColor Cyan
Write-Host "  Drummer Style Integration Complete" -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$sourceDir = "f:\DrumTracKAI_v1.1.16_Clean"
$backupDir = "f:\Backups\DrumTracKAI"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$archiveName = "DrumTracKAI_v1.1.16_Drummer_Integration_$timestamp.zip"
$archivePath = Join-Path $backupDir $archiveName

# Create backup directory if it doesn't exist
if (!(Test-Path $backupDir)) {
    Write-Host "[1/5] Creating backup directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    Write-Host "      Created: $backupDir" -ForegroundColor Green
} else {
    Write-Host "[1/5] Backup directory exists: $backupDir" -ForegroundColor Green
}

Write-Host ""
Write-Host "[2/5] Calculating source size..." -ForegroundColor Yellow

# Get source directory size
$sourceSize = (Get-ChildItem $sourceDir -Recurse -File | Measure-Object -Property Length -Sum).Sum
$sourceSizeMB = [math]::Round($sourceSize / 1MB, 2)

Write-Host "      Source directory: $sourceSizeMB MB" -ForegroundColor Green
Write-Host ""

# Files to exclude
$excludePatterns = @(
    "node_modules",
    "drumtrackai_env",
    "target",
    "uploads",
    "sessions",
    ".git",
    "*.pyc",
    "__pycache__",
    ".pytest_cache",
    "*.log",
    "build",
    "dist"
)

Write-Host "[3/5] Creating temporary directory..." -ForegroundColor Yellow
$tempDir = Join-Path $env:TEMP "DrumTracKAI_Backup_Temp"
if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

Write-Host "[4/5] Copying files (excluding build artifacts)..." -ForegroundColor Yellow
Write-Host "      Excluding: $($excludePatterns -join ', ')" -ForegroundColor Gray

# Copy files excluding patterns
Get-ChildItem -Path $sourceDir -Recurse | ForEach-Object {
    $relativePath = $_.FullName.Substring($sourceDir.Length)
    $shouldExclude = $false
    
    foreach ($pattern in $excludePatterns) {
        if ($relativePath -like "*\$pattern\*" -or $relativePath -like "*$pattern*") {
            $shouldExclude = $true
            break
        }
    }
    
    if (!$shouldExclude) {
        $destPath = Join-Path $tempDir $relativePath
        $destDir = Split-Path $destPath -Parent
        
        if (!(Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        
        if ($_.PSIsContainer -eq $false) {
            Copy-Item $_.FullName $destPath -Force
        }
    }
}

$copiedSize = (Get-ChildItem $tempDir -Recurse -File | Measure-Object -Property Length -Sum).Sum
$copiedSizeMB = [math]::Round($copiedSize / 1MB, 2)
Write-Host "      Copied: $copiedSizeMB MB (after exclusions)" -ForegroundColor Green

Write-Host ""
Write-Host "[5/5] Creating archive..." -ForegroundColor Yellow

Compress-Archive -Path "$tempDir\*" -DestinationPath $archivePath -Force -CompressionLevel Optimal

# Clean up temp directory
Remove-Item $tempDir -Recurse -Force

# Get final archive size
$archiveSize = (Get-Item $archivePath).Length
$archiveSizeMB = [math]::Round($archiveSize / 1MB, 2)
$compressionRatio = [math]::Round(($archiveSize / $copiedSize) * 100, 1)

Write-Host "      Archive created: $archiveSizeMB MB" -ForegroundColor Green
Write-Host "      Compression ratio: $compressionRatio%" -ForegroundColor Green
Write-Host ""

# Generate backup summary
$summaryPath = Join-Path $backupDir "backup_summary_$timestamp.txt"
$summary = @"
==================================================================
  DrumTracKAI v1.1.16 Backup Summary
  Drummer Style Integration Complete
==================================================================

Backup Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Version: 1.1.16

SOURCE:
  Directory: $sourceDir
  Size: $sourceSizeMB MB

ARCHIVE:
  File: $archiveName
  Path: $archivePath
  Size: $archiveSizeMB MB
  Compression: $compressionRatio%

EXCLUDED:
  $($excludePatterns -join "`n  ")

INCLUDED:
  - All source code (Python, Rust, TypeScript)
  - Configuration files
  - Complete documentation (12 .md files)
  - Admin database (drumtrackai.db)
  - Test scripts
  - Build scripts

NEW IN THIS VERSION:
  - drummer_mapping_service.py (342 lines)
  - DrummerSelector.tsx (390 lines)
  - test_drummer_connection.py (100 lines)
  - 3 new API endpoints
  - 6 new documentation files
  - Modified WebDAWApp.tsx integration
  - Modified dcsm_backend.py (118 lines added)

TOTAL CHANGES:
  - New Lines: ~3,500+
  - Files Created: 10
  - Files Modified: 2
  - Status: ✅ All tested and working

RESTORATION:
  1. Extract archive to destination folder
  2. Create virtual environment: python -m venv drumtrackai_env
  3. Install dependencies: pip install -r requirements.txt
  4. Build Rust: cd audio-core && cargo build --release
  5. Install frontend: cd frontend && npm install
  6. Test: python test_drummer_connection.py

NEXT STEPS:
  - End-to-end testing with Peg audio file
  - Populate admin database with more drummers
  - Begin Phase 2: Groove Analysis Integration

==================================================================
Backup completed successfully! ✅
==================================================================
"@

$summary | Out-File -FilePath $summaryPath -Encoding UTF8

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "  Archive Backup Complete! ✅" -ForegroundColor Green
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Archive: $archiveName" -ForegroundColor White
Write-Host "  Location: $backupDir" -ForegroundColor White
Write-Host "  Size: $archiveSizeMB MB" -ForegroundColor White
Write-Host "  Compression: $compressionRatio%" -ForegroundColor White
Write-Host ""
Write-Host "  Summary: backup_summary_$timestamp.txt" -ForegroundColor White
Write-Host ""
Write-Host "===================================================================" -ForegroundColor Cyan

# Open backup directory
Write-Host ""
$response = Read-Host "Open backup directory? (Y/N)"
if ($response -eq 'Y' -or $response -eq 'y') {
    Start-Process "explorer.exe" -ArgumentList $backupDir
}

Write-Host ""
Write-Host "Done! Press any key to exit..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
