<#
.SYNOPSIS
  Project Scaffolding CLI Wrapper (PowerShell Edition)
.DESCRIPTION
  Delegates core scaffolding to cross-platform scaffold_engine.py.
  Provides interactive CLI menus if parameters are omitted.
#>

[CmdletBinding()]
param(
  [Alias('Preset')]
  [string]$Archetype,

  [ValidateSet('pr', 'direct-push', 'trunk')]
  [string]$Flow,

  [Alias('ReleaseStrategy')]
  [ValidateSet('default', 'none', 'npm-version', 'dotnet-store', 'python-version', 'github-tag')]
  [string]$Release,

  [switch]$NoRelease,

  [string[]]$Features,

  [string]$TargetDir = (Get-Location).Path,

  [string]$ProjectName,

  [switch]$AllFeatures,

  [switch]$NoFeatures,

  [switch]$Force
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PresetsFile = Join-Path $ScriptDir "presets.json"
$EngineScript = Join-Path $ScriptDir "scaffold_engine.py"

if (-not (Test-Path $PresetsFile)) {
  Write-Error "presets.json not found in $ScriptDir"
  exit 1
}

$Config = Get-Content $PresetsFile -Raw -Encoding UTF8 | ConvertFrom-Json

# Handle legacy aliases
if ($Archetype -and $Config.legacyAliases.$Archetype) {
  $Archetype = $Config.legacyAliases.$Archetype
}

# 1. Interactive Archetype Selection if not passed
if (-not $Archetype) {
  Write-Host ""
  Write-Host "=================================================" -ForegroundColor Cyan
  Write-Host "   🚀 Youchen Project Scaffolding Initializer" -ForegroundColor Yellow
  Write-Host "=================================================" -ForegroundColor Cyan
  Write-Host "Stage 1: Please select a Project Archetype:"
  Write-Host ""

  $keys = @($Config.archetypes.PSObject.Properties.Name)
  for ($i = 0; $i -lt $keys.Count; $i++) {
    $k = $keys[$i]
    $arch = $Config.archetypes.$k
    Write-Host "  [$($i + 1)] $k ($($arch.name))" -ForegroundColor Green -NoNewline
    Write-Host " - $($arch.description)" -ForegroundColor Gray
  }
  Write-Host ""

  $choice = Read-Host "Enter number (1-$($keys.Count))"
  $index = [int]$choice - 1
  if ($index -ge 0 -and $index -lt $keys.Count) {
    $Archetype = $keys[$index]
  } else {
    Write-Error "Invalid choice. Aborting."
    exit 1
  }
}

# 2. Build Python Argument List
$pyArgs = @($EngineScript, "--archetype", $Archetype, "--target-dir", $TargetDir)

if ($Flow) { $pyArgs += @("--flow", $Flow) }
if ($Release) { $pyArgs += @("--release", $Release) }
if ($NoRelease) { $pyArgs += "--no-release" }
if ($ProjectName) { $pyArgs += @("--project-name", $ProjectName) }
if ($Force) { $pyArgs += "--force" }
if ($AllFeatures) { $pyArgs += "--all-features" }
if ($NoFeatures) { $pyArgs += "--no-features" }

if ($Features -and $Features.Count -gt 0) {
  $featJoined = ($Features -join ',')
  $pyArgs += @("--features", $featJoined)
}

# 3. Delegate to scaffold_engine.py
& python @pyArgs
if ($LASTEXITCODE -ne 0) {
  Write-Error "Scaffolding engine failed with exit code $LASTEXITCODE"
  exit $LASTEXITCODE
}
