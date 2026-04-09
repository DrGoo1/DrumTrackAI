$ErrorActionPreference = 'Stop'

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$root = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($root)) { throw "Could not determine script root" }

$outDir = Join-Path $root ("_BACKUPS\chatgpt_gap_analysis_split\" + $ts)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Host "Repo root: $root"
Write-Host "Output dir: $outDir"

$manifestPath = Join-Path $outDir 'VERSION_MANIFEST.txt'
"Backup created: $ts" | Out-File -FilePath $manifestPath -Encoding utf8
"Repo root: $root" | Out-File -FilePath $manifestPath -Encoding utf8 -Append
"Repo folder: $(Split-Path -Leaf $root)" | Out-File -FilePath $manifestPath -Encoding utf8 -Append

try {
  if (Test-Path (Join-Path $root '.git')) {
    $gitCommit = (& git -C $root rev-parse HEAD 2>$null)
    if ($LASTEXITCODE -eq 0 -and $gitCommit) {
      "Git commit: $gitCommit" | Out-File -FilePath $manifestPath -Encoding utf8 -Append
    }
    $gitBranch = (& git -C $root rev-parse --abbrev-ref HEAD 2>$null)
    if ($LASTEXITCODE -eq 0 -and $gitBranch) {
      "Git branch: $gitBranch" | Out-File -FilePath $manifestPath -Encoding utf8 -Append
    }
  }
} catch {}

try {
  $frontendPkg = Join-Path $root 'frontend\package.json'
  if (Test-Path $frontendPkg) {
    $pkgJson = Get-Content -LiteralPath $frontendPkg -Raw
    $m = [regex]::Match($pkgJson, '"version"\s*:\s*"([^"]+)"')
    if ($m.Success) {
      "Frontend package.json version: $($m.Groups[1].Value)" | Out-File -FilePath $manifestPath -Encoding utf8 -Append
    }
  }
} catch {}

try {
  $adminModelManifest = Join-Path $root 'admin\models\production\v1.1.17\drum_humanizer\model_manifest.json'
  if (Test-Path $adminModelManifest) {
    "Admin model manifest present: admin\\models\\production\\v1.1.17\\drum_humanizer\\model_manifest.json" | Out-File -FilePath $manifestPath -Encoding utf8 -Append
  }
} catch {}

"" | Out-File -FilePath $manifestPath -Encoding utf8 -Append
"This manifest helps verify the upload set corresponds to the intended app snapshot." | Out-File -FilePath $manifestPath -Encoding utf8 -Append
Write-Host "Wrote manifest: $manifestPath"

function New-ZipFromPaths {
  param(
    [Parameter(Mandatory=$true)][string]$ZipPath,
    [Parameter(Mandatory=$true)][string[]]$Paths,
    [string[]]$Excludes = @()
  )

  if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }

  $existing = @()
  foreach ($p in $Paths) {
    $abs = Join-Path $root $p
    if (Test-Path $abs) { $existing += $p }
  }

  if ($existing.Count -eq 0) {
    Write-Host "Skip (no paths exist): $ZipPath"
    return
  }

  Write-Host "Creating: $ZipPath"
  & tar -a -c -f $ZipPath -C $root @Excludes @existing
  Write-Host "Created:  $ZipPath"
}

# Common excludes to keep archives upload-friendly
$commonExcludes = @(
  '--exclude=.git',
  '--exclude=.venv',
  '--exclude=drumtrackai_env',
  '--exclude=**/node_modules',
  '--exclude=**/__pycache__',
  '--exclude=**/.pytest_cache',
  '--exclude=logs',
  '--exclude=database/processed_stems',
  '--exclude=_ARCHIVE_FRONTENDS',
  '--exclude=_ARCHIVE_PRE_CLEANUP',
  '--exclude=sessions',
  '--exclude=uploads',
  '--exclude=validation_samples'
)

# -----------------------------------------------------------------------------
# App repo set
# -----------------------------------------------------------------------------
New-ZipFromPaths -ZipPath (Join-Path $outDir 'backend.zip') -Paths @('backend','llm_service','brain_configs','config','infrastructure') -Excludes $commonExcludes

New-ZipFromPaths -ZipPath (Join-Path $outDir 'frontend.zip') -Paths @('frontend') -Excludes $commonExcludes

# Plugin code (present as DrumTracKAIConnector)
New-ZipFromPaths -ZipPath (Join-Path $outDir 'plugin.zip') -Paths @('DrumTracKAIConnector') -Excludes $commonExcludes

# DB models / schema / migrations (repo has schema files; no alembic detected)
New-ZipFromPaths -ZipPath (Join-Path $outDir 'db_models_and_migrations.zip') -Paths @(
  'backend\dcsmpiano',
  'database',
  'admin\services\central_database_service.py'
) -Excludes ($commonExcludes + @(
  '--exclude=database/processed_stems'
))

# Docs + scripts + specs + readmes + utilities
New-ZipFromPaths -ZipPath (Join-Path $outDir 'docs_and_scripts.zip') -Paths @(
  'docs',
  'scripts',
  'README.md',
  'README_SENTIENT_DRUMMER.md',
  'MAKE_CHATGPT_ZIPS.ps1',
  'MAKE_CHATGPT_ZIPS.bat',
  'MAKE_CHATGPT_ZIPS_SPLIT.ps1',
  ("_BACKUPS\\chatgpt_gap_analysis_split\\" + $ts + "\\VERSION_MANIFEST.txt")
) -Excludes $commonExcludes

# -----------------------------------------------------------------------------
# Admin repo set (admin lives inside this mono-repo)
# -----------------------------------------------------------------------------
$adminExcludes = $commonExcludes + @(
  '--exclude=admin/drumtrackai.db*',
  '--exclude=admin/**/drumtrackai.db*',
  '--exclude=admin/**/*.log',
  '--exclude=admin/**/*.wav',
  '--exclude=admin/**/*.mp3',
  '--exclude=admin/**/*.flac',
  '--exclude=admin/**/*.zip',
  '--exclude=admin/data',
  '--exclude=admin/db_backups',
  '--exclude=admin/downloads',
  '--exclude=admin/output',
  '--exclude=admin/reaper_projects',
  '--exclude=admin/sd3_extracted_samples',
  '--exclude=admin/sd3_midi_patterns',
  '--exclude=admin/models'
)

# Split admin into smaller, upload-friendly architecture bundles
New-ZipFromPaths -ZipPath (Join-Path $outDir 'admin_core.zip') -Paths @(
  'admin/main.py',
  'admin/__init__.py',
  'admin/admin',
  'admin/core',
  'admin/utils',
  'admin/widgets'
) -Excludes $adminExcludes

New-ZipFromPaths -ZipPath (Join-Path $outDir 'admin_ui.zip') -Paths @(
  'admin/ui',
  'admin/admin/ui'
) -Excludes $adminExcludes

New-ZipFromPaths -ZipPath (Join-Path $outDir 'admin_services.zip') -Paths @(
  'admin/services',
  'admin/admin/services'
) -Excludes $adminExcludes

New-ZipFromPaths -ZipPath (Join-Path $outDir 'admin_tools_and_training.zip') -Paths @(
  'admin/tools',
  'admin/training',
  'admin/admin_monitoring_overview.md'
) -Excludes $adminExcludes

New-ZipFromPaths -ZipPath (Join-Path $outDir 'admin_tests_and_scripts.zip') -Paths @(
  'admin/test_imports.py',
  'admin/test_system.py',
  'admin/test_timeline_reset.py',
  'admin/test_youtube_learning.py',
  'admin/scripts',
  'admin/docs'
) -Excludes $adminExcludes

# Analysis core (pipeline orchestration + audio-core helpers)
New-ZipFromPaths -ZipPath (Join-Path $outDir 'analysis_core.zip') -Paths @(
  'admin\services\phased_drum_analysis.py',
  'admin\services\central_database_service.py',
  'audio-core',
  'backend\drum_generation'
) -Excludes $commonExcludes

# Models + tools (WARNING: models may still be large; common excludes will remove processed stems etc)
New-ZipFromPaths -ZipPath (Join-Path $outDir 'models_and_tools.zip') -Paths @(
  'models',
  'Jamstix',
  'DrumBeats',
  'audio-core'
) -Excludes ($commonExcludes + @(
  '--exclude=models/**/*.pt',
  '--exclude=models/**/*.pth',
  '--exclude=models/**/*.onnx',
  '--exclude=models/**/*.bin',
  '--exclude=models/**/*.tflite'
))

# Docs + tests
New-ZipFromPaths -ZipPath (Join-Path $outDir 'docs_and_tests.zip') -Paths @(
  'docs',
  'admin\test_imports.py',
  'admin\test_system.py',
  'backend\tests'
) -Excludes $commonExcludes

Write-Host "Done. Output folder: $outDir"
