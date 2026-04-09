$ErrorActionPreference = 'Stop'

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$root = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($root)) { throw "Could not determine script root" }

$destDir = Join-Path $root '_BACKUPS\chatgpt_gap_analysis'
New-Item -ItemType Directory -Force -Path $destDir | Out-Null

Write-Host "Repo root: $root"
Write-Host "Backup dir: $destDir"

# --- ZIP 1: code-only repo snapshot (exclude heavy folders) ---
$codeZip = Join-Path $destDir ("repo_code_only_$ts.zip")
if (Test-Path $codeZip) { Remove-Item -Force $codeZip }

$excludes = @(
  '--exclude=.git',
  '--exclude=.venv',
  '--exclude=**/node_modules',
  '--exclude=database/processed_stems',
  '--exclude=models',
  '--exclude=logs',
  '--exclude=Drum_Education',
  '--exclude=Jamstix',
  '--exclude=Mixosaurus',
  '--exclude=MIDI Drum Beats',
  '--exclude=DrumBeats',
  '--exclude=Images',
  '--exclude=validation_samples',
  '--exclude=_ARCHIVE_FRONTENDS',
  '--exclude=_ARCHIVE_PRE_CLEANUP'
)

Write-Host "Creating code-only zip..."
& tar -a -c -f $codeZip -C $root @excludes .
Write-Host "Created: $codeZip"

# --- ZIP 2: admin app + DB snapshot ---
$adminZip = Join-Path $destDir ("admin_app_plus_db_$ts.zip")
if (Test-Path $adminZip) { Remove-Item -Force $adminZip }

$adminItems = @(
  (Join-Path $root 'admin'),
  (Join-Path $root 'docs\ADMIN_APP_CURRENT_STATE_PHASES_1_6.md'),
  (Join-Path $root 'docs\ASSIMILATION_SCORING_RUBRIC.md'),
  (Join-Path $root 'admin\drumtrackai.db'),
  (Join-Path $root 'admin\drumtrackai.db-wal'),
  (Join-Path $root 'admin\drumtrackai.db-shm')
) | Where-Object { Test-Path $_ }

Write-Host "Creating admin+db zip..."
Compress-Archive -Path $adminItems -DestinationPath $adminZip -Force
Write-Host "Created: $adminZip"

Write-Host "Done."
Write-Host "Code-only zip: $codeZip"
Write-Host "Admin+DB zip: $adminZip"
