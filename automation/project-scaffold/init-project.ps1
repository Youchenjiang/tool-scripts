<#
.SYNOPSIS
  Project Scaffolding Tool for Agent Rules, Git Policies & CI Workflows
.DESCRIPTION
  Two-tier project initializer:
  1. Select project Archetype (web-spa, backend-api, desktop-app, sec-research, minimal)
  2. Select optional Features (strict-linting, chained-prs, sec-enterprise)
.PARAMETER Archetype
  Project core archetype profile (or alias -Preset)
.PARAMETER Flow
  Git workflow mode: 'pr' (Pull Request based) or 'direct-push' / 'trunk' (Direct trunk push, no PR).
.PARAMETER Release
  Release & CD lifecycle strategy: 'default', 'none', 'npm-version', 'dotnet-store', 'python-version', 'github-tag'.
.PARAMETER NoRelease
  Disable version and release management (sets release strategy to 'none').
.PARAMETER Features
  Optional array of features to enable
.PARAMETER TargetDir
  Target project directory (defaults to current directory)
.PARAMETER ProjectName
  Project name (defaults to TargetDir folder name)
.PARAMETER AllFeatures
  Enable all optional features
.PARAMETER NoFeatures
  Disable all optional features (do not even apply recommended)
.PARAMETER Force
  Overwrite existing rule/workflow files
.EXAMPLE
  .\init-project.ps1 -Archetype web-spa -ProjectName "MyWebApp"
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
$TemplatesDir = Join-Path $ScriptDir "templates"

if (-not (Test-Path $PresetsFile)) {
  Write-Error "presets.json not found in $ScriptDir"
  exit 1
}

$Config = Get-Content $PresetsFile -Raw -Encoding UTF8 | ConvertFrom-Json
$AvailableFeatures = @($Config.features.PSObject.Properties.Name)

# Handle legacy aliases
if ($Archetype -and $Config.legacyAliases.$Archetype) {
  $Archetype = $Config.legacyAliases.$Archetype
}

# 1. Interactive Selection for Archetype
if (-not $Archetype) {
  Write-Host ""
  Write-Host "=================================================" -ForegroundColor Cyan
  Write-Host "   🚀 Youchen Project Scaffolding Initializer" -ForegroundColor Yellow
  Write-Host "=================================================" -ForegroundColor Cyan
  Write-Host "Stage 1: Please select a Project Archetype:"
  Write-Host ""

  $archetypeKeys = @($Config.archetypes.PSObject.Properties.Name)
  for ($i = 0; $i -lt $archetypeKeys.Count; $i++) {
    $key = $archetypeKeys[$i]
    $arch = $Config.archetypes.$key
    Write-Host "  [$($i + 1)] $key ($($arch.name))" -ForegroundColor Green -NoNewline
    Write-Host " - $($arch.description)" -ForegroundColor Gray
  }
  Write-Host ""

  $choice = Read-Host "Enter number (1-$($archetypeKeys.Count))"
  $index = [int]$choice - 1
  if ($index -ge 0 -and $index -lt $archetypeKeys.Count) {
    $Archetype = $archetypeKeys[$index]
  } else {
    Write-Error "Invalid choice. Aborting."
    exit 1
  }
}

$SelectedArchetype = $Config.archetypes.$Archetype
if (-not $SelectedArchetype) {
  Write-Error "Archetype '$Archetype' not found in configuration."
  exit 1
}

# 2. Resolve Git Workflow Mode (PR vs Direct Trunk Push)
$defaultFlow = if ($SelectedArchetype.flow) {
  $SelectedArchetype.flow
} elseif ($SelectedArchetype.recommendedFeatures -contains "direct-push" -or $Archetype -eq "script-tool") {
  "direct-push"
} else {
  "pr"
}

if (-not $Flow) {
  # If running in interactive mode (neither Archetype nor Features supplied via CLI)
  if (-not $PSBoundParameters.ContainsKey('Archetype') -or (-not $Features -and -not $AllFeatures -and -not $NoFeatures)) {
    Write-Host ""
    Write-Host "Stage 2: Git Workflow Mode (工作流程模式):" -ForegroundColor Cyan
    Write-Host "  [1] pr          - Pull Request 流程 (標準分支開發、開 PR、PR 模板與審查門禁)" -ForegroundColor $(if ($defaultFlow -eq 'pr') { "Green" } else { "Gray" })
    Write-Host "  [2] direct-push - Direct Trunk Push (免開 PR、主幹原子提交直接推送 main)" -ForegroundColor $(if ($defaultFlow -eq 'direct-push') { "Green" } else { "Gray" })
    Write-Host ""
    $flowChoice = Read-Host "請選擇工作流程 [1/2, 預設: $(if ($defaultFlow -eq 'pr') { '1' } else { '2' }) ($defaultFlow)]"
    if ($flowChoice -eq '1' -or $flowChoice -match '^[Pp]') {
      $Flow = "pr"
    } elseif ($flowChoice -eq '2' -or $flowChoice -match '^[DdTt]') {
      $Flow = "direct-push"
    } elseif ($flowChoice -eq '') {
      $Flow = $defaultFlow
    } else {
      Write-Host "  ! 無效輸入，採用預設: $defaultFlow" -ForegroundColor DarkYellow
      $Flow = $defaultFlow
    }
  } else {
    $Flow = $defaultFlow
  }
}

if ($Flow -eq "trunk") { $Flow = "direct-push" }

# 3. Resolve Release & CD Lifecycle Strategy
$defaultReleaseStrategy = if ($SelectedArchetype.release -and $SelectedArchetype.release.strategy) {
  $SelectedArchetype.release.strategy
} else {
  "github-tag"
}

if ($NoRelease) {
  $Release = "none"
}

if (-not $Release -or $Release -eq "default") {
  # If running in interactive mode (neither Archetype nor Features supplied via CLI)
  if (-not $PSBoundParameters.ContainsKey('Archetype') -or (-not $Features -and -not $AllFeatures -and -not $NoFeatures)) {
    Write-Host ""
    Write-Host "Stage 3: Release & CD Lifecycle (版本管理與發佈門禁):" -ForegroundColor Cyan
    Write-Host "  [1] 遵循範本預設 ($defaultReleaseStrategy) - 具備完整版本檔校驗、tag 門禁與自動 CD 發佈" -ForegroundColor Green
    Write-Host "  [2] none         - 不需要管理版本 (免除 tag 與版本號綁定、無 release 門禁、自由發布)" -ForegroundColor $(if ($defaultReleaseStrategy -eq 'none') { "Green" } else { "Gray" })
    Write-Host "  [3] github-tag   - 輕量 GitHub Release Tag (以 VERSION 檔為準)" -ForegroundColor Gray
    Write-Host "  [4] 自選套件策略 (npm-version / dotnet-store / python-version)" -ForegroundColor Gray
    Write-Host ""
    $relChoice = Read-Host "請選擇版本管理策略 [1/2/3/4, 預設: 1 ($defaultReleaseStrategy)]"
    if ($relChoice -eq '1' -or $relChoice -eq '') {
      $Release = $defaultReleaseStrategy
    } elseif ($relChoice -eq '2' -or $relChoice -match '^[Nn]') {
      $Release = "none"
    } elseif ($relChoice -eq '3' -or $relChoice -match '^[GgTt]') {
      $Release = "github-tag"
    } elseif ($relChoice -eq '4') {
      Write-Host "  可用策略: npm-version, dotnet-store, python-version" -ForegroundColor Cyan
      $customRel = Read-Host "請輸入策略名稱"
      if ($customRel -in @('npm-version', 'dotnet-store', 'python-version', 'github-tag', 'none')) {
        $Release = $customRel
      } else {
        Write-Host "  ! 未知策略，採用預設: $defaultReleaseStrategy" -ForegroundColor DarkYellow
        $Release = $defaultReleaseStrategy
      }
    } else {
      Write-Host "  ! 無效輸入，採用預設: $defaultReleaseStrategy" -ForegroundColor DarkYellow
      $Release = $defaultReleaseStrategy
    }
  } else {
    $Release = $defaultReleaseStrategy
  }
}

# Construct $releaseConfig object
$releaseConfig = if ($Release -eq "none") {
  [ordered]@{
    strategy    = "none"
    versionFile = ""
    syncFiles   = @()
  }
} elseif ($Release -eq $SelectedArchetype.release.strategy) {
  $SelectedArchetype.release
} else {
  switch ($Release) {
    "npm-version" {
      [ordered]@{ strategy = "npm-version"; versionFile = "package.json"; syncFiles = @("package-lock.json") }
    }
    "dotnet-store" {
      [ordered]@{ strategy = "dotnet-store"; versionFile = "Directory.Build.props"; syncFiles = @("Package.appxmanifest") }
    }
    "python-version" {
      [ordered]@{ strategy = "python-version"; versionFile = "pyproject.toml"; syncFiles = @() }
    }
    "github-tag" {
      [ordered]@{ strategy = "github-tag"; versionFile = "VERSION"; syncFiles = @() }
    }
    default {
      [ordered]@{ strategy = $Release; versionFile = ""; syncFiles = @() }
    }
  }
}

# 4. Resolve Active Features
$ActiveFeatures = @()
if ($NoFeatures) {
  $ActiveFeatures = @()
} elseif ($AllFeatures) {
  $ActiveFeatures = @($Config.features.PSObject.Properties.Name)
} elseif ($Features -and $Features.Count -gt 0) {
  # From a shell, -Features a,b arrives as one string, so split it here.
  $ActiveFeatures = $Features -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
} else {
  # Default to recommended features for this archetype
  $recommended = @($SelectedArchetype.recommendedFeatures)
  if ($Flow -eq "direct-push" -and -not ($recommended -contains "direct-push")) {
    $recommended += "direct-push"
  }
  if ($Flow -eq "pr" -and ($recommended -contains "direct-push")) {
    $recommended = @($recommended | Where-Object { $_ -ne "direct-push" })
  }
  if ($recommended.Count -gt 0) {
    Write-Host ""
    Write-Host "Stage 4: Features Configuration:" -ForegroundColor Cyan
    Write-Host "Recommended features for ${Archetype}: $($recommended -join ', ')" -ForegroundColor Yellow
    Write-Host "Available features: $($Config.features.PSObject.Properties.Name -join ', ')" -ForegroundColor DarkGray
    $prompt = Read-Host "Enable recommended features? [Y/n] (or enter custom comma-separated list)"
    if ($prompt -eq '' -or $prompt -match '^[Yy]') {
      $ActiveFeatures = $recommended
    } elseif ($prompt -match '^[Nn]') {
      $ActiveFeatures = @()
    } else {
      $ActiveFeatures = $prompt -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    }
  }
}

# Align features with selected flow
if ($Flow -eq "direct-push") {
  if (-not ($ActiveFeatures -contains "direct-push")) {
    $ActiveFeatures += "direct-push"
  }
  if ($ActiveFeatures -contains "chained-prs") {
    $ActiveFeatures = @($ActiveFeatures | Where-Object { $_ -ne "chained-prs" })
  }
} elseif ($Flow -eq "pr") {
  if ($ActiveFeatures -contains "direct-push") {
    $ActiveFeatures = @($ActiveFeatures | Where-Object { $_ -ne "direct-push" })
  }
}

# Drop unknown feature names instead of letting them look enabled
$UnknownFeatures = @($ActiveFeatures | Where-Object { $AvailableFeatures -notcontains $_ })
if ($UnknownFeatures.Count -gt 0) {
  Write-Host "  ! Unknown feature(s) ignored: $($UnknownFeatures -join ', ')" -ForegroundColor Yellow
  Write-Host "    Available: $($AvailableFeatures -join ', ')" -ForegroundColor DarkGray
  $ActiveFeatures = @($ActiveFeatures | Where-Object { $AvailableFeatures -contains $_ })
}

# Resolve Target Directory & Project Name
if (-not (Test-Path $TargetDir)) {
  New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}
$TargetDir = (Resolve-Path $TargetDir).Path

if (-not $ProjectName) {
  $ProjectName = Split-Path -Leaf $TargetDir
}

# Calculate stable project-specific hash-based jitter cron schedule
# Prevents concurrent spike / Self-DDoS across multiple scaffolded repositories
$projectHash = [Math]::Abs($ProjectName.GetHashCode())
$jitterMonthDay = ($projectHash % 28) + 1
$jitterHour = ($projectHash % 4) + 1
$jitterMinute = $projectHash % 59
$ProjectMonthlyCron = "$jitterMinute $jitterHour $jitterMonthDay * *"
$jitterWeekDay = $projectHash % 7
$ProjectWeeklyCron = "$jitterMinute $jitterHour * * $jitterWeekDay"

Write-Host ""
Write-Host "Target Directory : $TargetDir" -ForegroundColor Cyan
Write-Host "Project Name     : $ProjectName" -ForegroundColor Cyan
Write-Host "Archetype        : $Archetype ($($SelectedArchetype.name))" -ForegroundColor Green
Write-Host "Workflow Mode    : $Flow $(if ($Flow -eq 'direct-push') { '(免 PR 主幹直接推送)' } else { '(Pull Request 分支審查流程)' })" -ForegroundColor Cyan
Write-Host "Release Strategy : $(if ($releaseConfig.strategy -and $releaseConfig.strategy -ne 'none') { "$($releaseConfig.strategy) (Version file: $($releaseConfig.versionFile))" } else { 'none (免版本管理)' })" -ForegroundColor Cyan
Write-Host "Active Features  : $(if ($ActiveFeatures.Count -gt 0) { $ActiveFeatures -join ', ' } else { '(None)' })" -ForegroundColor Yellow
Write-Host "Jitter Schedules : Monthly ($ProjectMonthlyCron), Weekly ($ProjectWeeklyCron)" -ForegroundColor DarkCyan
Write-Host "-------------------------------------------------"

# Step 1: Assemble Agent Rules
Write-Host "[1/5] Assembling Agent Rules..." -ForegroundColor Yellow

$RulesHeader = @"
# $ProjectName Agent Rules & Developer Guidelines

You are a senior pair-programming AI assistant operating in the **$ProjectName** codebase.
Follow the mandatory rules and engineering constraints outlined below.

"@

$CombinedRules = $RulesHeader

# Assemble and deduplicate rule files
$AllRuleFiles = [System.Collections.Generic.List[string]]::new()
foreach ($r in $SelectedArchetype.agentRules) { $AllRuleFiles.Add($r) }
foreach ($featKey in $ActiveFeatures) {
  $feat = $Config.features.$featKey
  if ($feat -and $feat.agentRules) {
    foreach ($r in $feat.agentRules) {
      if (-not $AllRuleFiles.Contains($r)) { $AllRuleFiles.Add($r) }
    }
  }
}

# If direct-push is active, replace PR-centric git-discipline.md with direct-trunk.md
if ($Flow -eq "direct-push" -or $ActiveFeatures -contains "direct-push") {
  if ($AllRuleFiles.Contains("git-discipline.md")) {
    $AllRuleFiles.Remove("git-discipline.md") | Out-Null
  }
  if (-not $AllRuleFiles.Contains("direct-trunk.md")) {
    $AllRuleFiles.Add("direct-trunk.md")
  }
} else {
  if ($AllRuleFiles.Contains("direct-trunk.md")) {
    $AllRuleFiles.Remove("direct-trunk.md") | Out-Null
  }
  if (-not $AllRuleFiles.Contains("git-discipline.md")) {
    $AllRuleFiles.Add("git-discipline.md")
  }
}

foreach ($ruleFile in $AllRuleFiles) {
  $rulePath = Join-Path $TemplatesDir "agent-rules\$ruleFile"
  if (Test-Path $rulePath) {
    $content = Get-Content $rulePath -Raw -Encoding UTF8
    $CombinedRules += "`n`n" + $content
  }
}

# Write AGENTS.md
$AgentsMdPath = Join-Path $TargetDir "AGENTS.md"
[System.IO.File]::WriteAllText($AgentsMdPath, $CombinedRules, [System.Text.Encoding]::UTF8)
Write-Host "  + Created: AGENTS.md" -ForegroundColor Gray

# Write .agent/rules.md
$AgentDir = Join-Path $TargetDir ".agent"
if (-not (Test-Path $AgentDir)) { New-Item -ItemType Directory -Path $AgentDir -Force | Out-Null }
$AgentRulesPath = Join-Path $AgentDir "rules.md"
[System.IO.File]::WriteAllText($AgentRulesPath, $CombinedRules, [System.Text.Encoding]::UTF8)
Write-Host "  + Created: .agent/rules.md" -ForegroundColor Gray

# Initialize MEMORY.md if not present
$MemoryPath = Join-Path $TargetDir "MEMORY.md"
if (-not (Test-Path $MemoryPath) -or $Force) {
  $StarterMemory = @"
# Agent Persistent Memory

> **Every agent session MUST read this file first** (defined in `.agent/rules.md`).
> **Every agent session MUST update this file before ending.**

---

## 🔑 User Preferences
- **Language**: 繁體中文 preferred for casual conversation; code/commits in English.
- **Style**: Direct, no fluff. Get things done with high engineering rigor.

---

## 📋 Current Active Tasks
- Initial project setup completed with archetype '$Archetype'.

---

## 🏗️ Architectural Context
- **Project**: $ProjectName
- **Archetype**: $Archetype ($($SelectedArchetype.name))
- **Features**: $(if ($ActiveFeatures.Count -gt 0) { $ActiveFeatures -join ', ' } else { 'Standard baseline' })

---

## ✅ Completed Decisions & Lessons Learned
- Initialized with Youchen two-tier scaffolding system.
"@
  [System.IO.File]::WriteAllText($MemoryPath, $StarterMemory, [System.Text.Encoding]::UTF8)
  Write-Host "  + Created: MEMORY.md (Starter Context)" -ForegroundColor Gray
}

# Step 2: Setup Git Policies & Templates
Write-Host "[2/5] Configuring Git Templates & Hooks..." -ForegroundColor Yellow

foreach ($gf in $SelectedArchetype.gitFiles) {
  if ($gf -like "hooks/*") { continue }
  $gfSrc = Join-Path $TemplatesDir "git\$gf"
  $gfDst = Join-Path $TargetDir $gf
  if (Test-Path $gfSrc) {
    if ($gf -eq ".gitignore" -and (Test-Path $gfDst) -and -not $Force) {
      Write-Host "  = Retained: $gf (already exists)" -ForegroundColor DarkGray
    } else {
      Copy-Item $gfSrc $gfDst -Force
      Write-Host "  + Created: $gf" -ForegroundColor Gray
    }
  }
}

# Setup Git Hook if .git repository exists
$GitDir = Join-Path $TargetDir ".git"
$HookDirSrc = Join-Path $TemplatesDir "git\hooks"

if (Test-Path $GitDir) {
  $HooksDir = Join-Path $GitDir "hooks"
  if (-not (Test-Path $HooksDir)) { New-Item -ItemType Directory -Path $HooksDir -Force | Out-Null }
  
  if (Test-Path $HookDirSrc) {
    Get-ChildItem $HookDirSrc -File | ForEach-Object {
      Copy-Item $_.FullName (Join-Path $HooksDir $_.Name) -Force
      Write-Host "  + Installed: .git/hooks/$($_.Name)" -ForegroundColor Green
    }
  }

  try {
    Push-Location $TargetDir
    git config commit.template .gitmessage.txt
    if ($Flow -eq "direct-push" -or $ActiveFeatures -contains "direct-push") {
      git config repo.directPush true
      Write-Host "  + Configured: git config repo.directPush true (Direct Trunk Push Mode)" -ForegroundColor Green
    } else {
      git config --unset repo.directPush 2>$null
    }
    Pop-Location
    Write-Host "  + Configured: git config commit.template .gitmessage.txt" -ForegroundColor Green
  } catch {
    # Non-fatal
  }
} else {
  Write-Host "  (Note: .git directory not found. Run 'git init' later to install hooks)" -ForegroundColor DarkYellow
}

# Setup version-controlled scripts/hooks/ for npm prepare lifecycle
if (Test-Path $HookDirSrc) {
  $TargetScriptsDir = Join-Path $TargetDir "scripts"
  $TargetScriptsHooksDir = Join-Path $TargetScriptsDir "hooks"
  if (-not (Test-Path $TargetScriptsHooksDir)) { New-Item -ItemType Directory -Path $TargetScriptsHooksDir -Force | Out-Null }
  Get-ChildItem $HookDirSrc -File | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $TargetScriptsHooksDir $_.Name) -Force
  }
  
  $installHooksSrc = Join-Path $TemplatesDir "git\scripts\install-hooks.mjs"
  if (Test-Path $installHooksSrc) {
    Copy-Item $installHooksSrc (Join-Path $TargetScriptsDir "install-hooks.mjs") -Force
    Write-Host "  + Deployed: scripts/install-hooks.mjs & scripts/hooks/*" -ForegroundColor Gray
  }

  # If package.json exists, inject "prepare": "node scripts/install-hooks.mjs"
  $pkgJsonPath = Join-Path $TargetDir "package.json"
  if (Test-Path $pkgJsonPath) {
    try {
      $pkg = Get-Content $pkgJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
      if (-not $pkg.scripts) {
        $pkg | Add-Member -MemberType NoteProperty -Name "scripts" -Value ([PSCustomObject]@{})
      }
      if (-not $pkg.scripts.prepare) {
        $pkg.scripts | Add-Member -MemberType NoteProperty -Name "prepare" -Value "node scripts/install-hooks.mjs"
        $newJson = $pkg | ConvertTo-Json -Depth 10
        [System.IO.File]::WriteAllText($pkgJsonPath, $newJson, [System.Text.Encoding]::UTF8)
        Write-Host "  + Configured: npm 'prepare' hook in package.json" -ForegroundColor Green
      }
    } catch {
      # Non-fatal if JSON parsing fails
    }
  }
}

# Step 3: Setup Engineering Tools & Code Quality
Write-Host "[3/5] Configuring Engineering Tools & Linter..." -ForegroundColor Yellow
$SkippedTestsNotShipped = [System.Collections.Generic.List[string]]::new()
$SkippedTestsNoConda = [System.Collections.Generic.List[string]]::new()
if ($SelectedArchetype.toolFiles) {
  $ToolsDir = Join-Path $TargetDir "tools"
  if (-not (Test-Path $ToolsDir)) { New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null }

  $prTools = @(
    "pr_helper.py", "branch_policy.py", "process_guard.py", "gh_guard.py",
    "sonar_audit.py", "pr_audit.py", "pr_reports.py", "pr_verification.py",
    "pr_body_contract.py", "pr_preflight.py", "pr_publication.py", "pr_creation.py", "pr_tool.py"
  )
  $toolsToDeploy = [System.Collections.Generic.List[string]]::new()
  foreach ($tf in $SelectedArchetype.toolFiles) {
    if ($Flow -eq "direct-push" -and $prTools -contains $tf) {
      continue
    }
    $toolsToDeploy.Add($tf)
  }
  if ($Flow -eq "pr") {
    foreach ($pt in $prTools) {
      if (-not $toolsToDeploy.Contains($pt)) {
        $toolsToDeploy.Add($pt)
      }
    }
  }

  foreach ($featKey in $ActiveFeatures) {
    $feat = $Config.features.$featKey
    if ($feat -and $feat.toolFiles) {
      foreach ($ftf in $feat.toolFiles) {
        if (-not $toolsToDeploy.Contains($ftf)) {
          $toolsToDeploy.Add($ftf)
        }
      }
    }
  }

  foreach ($tf in $toolsToDeploy) {
    $tfSrc = Join-Path $TemplatesDir "tools\$tf"
    $tfDst = Join-Path $ToolsDir $tf
    if (Test-Path $tfSrc) {
      if ($tf -eq "lint_commits.py" -and $SelectedArchetype.defaultScopes) {
        $pyScopes = "# /* SCOPES_PLACEHOLDER_START */`nALLOWED_SCOPES = [`n"
        foreach ($s in $SelectedArchetype.defaultScopes) {
          $pyScopes += "    `"$s`",`n"
        }
        $pyScopes += "]`n# /* SCOPES_PLACEHOLDER_END */"
        $toolContent = Get-Content $tfSrc -Raw -Encoding UTF8
        $regex = "(?s)#\s*/\*\s*SCOPES_PLACEHOLDER_START\s*\*/.*?#\s*/\*\s*SCOPES_PLACEHOLDER_END\s*\*/"
        if ($toolContent -match $regex) {
          $toolContent = $toolContent -replace $regex, $pyScopes
        } else {
          $toolContent = $toolContent -replace "(?s)ALLOWED_SCOPES\s*=\s*\[.*?\]", $pyScopes
        }
        [System.IO.File]::WriteAllText($tfDst, $toolContent, [System.Text.Encoding]::UTF8)
        Write-Host "  + Deployed Tool: tools/$tf (Configured with $($SelectedArchetype.defaultScopes.Count) archetype scopes)" -ForegroundColor Green
        continue
      }
      Copy-Item $tfSrc $tfDst -Force
      Write-Host "  + Deployed Tool: tools/$tf" -ForegroundColor Gray
    }
  }

  $TestTemplateDir = Join-Path $TemplatesDir "tests"
  if (Test-Path $TestTemplateDir) {
    $TestsDir = Join-Path $TargetDir "tests"
    if (-not (Test-Path $TestsDir)) { New-Item -ItemType Directory -Path $TestsDir -Force | Out-Null }
    Get-ChildItem $TestTemplateDir -File | ForEach-Object {
      # A test only belongs here if the tool it exercises was deployed.
      $testModule = ($_.Name -replace '^test_', '') -replace '\.py$', ''
      # env_tool.py is deployed after this loop, so consult the feature, not the file.
      $toolDeployed = (Test-Path (Join-Path $ToolsDir "$testModule.py")) -or
                      ($testModule -eq "env_tool" -and $ActiveFeatures -contains "conda-env")
      if (-not $toolDeployed) {
        if ($testModule -eq "env_tool") { $SkippedTestsNoConda.Add($_.Name) }
        else { $SkippedTestsNotShipped.Add($_.Name) }
        return
      }
      Copy-Item $_.FullName (Join-Path $TestsDir $_.Name) -Force
      Write-Host "  + Deployed Test: tests/$($_.Name)" -ForegroundColor Gray
    }
  }

  # Deploy tools/project.json contract (Stage 1 schema)
  $projectJsonPath = Join-Path $ToolsDir "project.json"
  $projectObj = [ordered]@{
    name      = $ProjectName
    archetype = $Archetype
    flow      = $Flow
    features  = @($ActiveFeatures)
    scopes    = @($SelectedArchetype.defaultScopes)
    build     = if ($SelectedArchetype.build) { $SelectedArchetype.build } else { [ordered]@{ lint = ""; test = ""; build = "" } }
    release   = $releaseConfig
  }
  $projectJsonContent = $projectObj | ConvertTo-Json -Depth 5
  $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
  [System.IO.File]::WriteAllText($projectJsonPath, $projectJsonContent, $utf8NoBom)
  Write-Host "  + Created: tools/project.json (Project Metadata & Architecture Contract)" -ForegroundColor Green

  if ($releaseConfig.strategy -eq "github-tag" -and $releaseConfig.versionFile -eq "VERSION") {
    $versionFilePath = Join-Path $TargetDir "VERSION"
    if (-not (Test-Path $versionFilePath)) {
      [System.IO.File]::WriteAllText($versionFilePath, "0.1.0`n", $utf8NoBom)
      Write-Host "  + Created: VERSION (Initial version 0.1.0)" -ForegroundColor Gray
    }
  }
}

if ($ActiveFeatures -contains "strict-linting") {
  $eslintSrc = Join-Path $TemplatesDir "lint\eslint.config.mjs"
  $eslintDst = Join-Path $TargetDir "eslint.config.mjs"
  if ((Test-Path $eslintSrc) -and (-not (Test-Path $eslintDst) -or $Force)) {
    Copy-Item $eslintSrc $eslintDst -Force
    Write-Host "  + Deployed: eslint.config.mjs (Strict Code Quality Gate)" -ForegroundColor Green
  }
} else {
  Write-Host "  - Skipped: strict-linting feature not enabled" -ForegroundColor DarkGray
}

if ($ActiveFeatures -contains "conda-env") {
  # 1. Deploy env_tool.py
  $ToolsDir = Join-Path $TargetDir "tools"
  if (-not (Test-Path $ToolsDir)) { New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null }
  $envToolSrc = Join-Path $TemplatesDir "tools\env_tool.py"
  $envToolDst = Join-Path $ToolsDir "env_tool.py"
  if (Test-Path $envToolSrc) {
    Copy-Item $envToolSrc $envToolDst -Force
    Write-Host "  + Deployed Tool: tools/env_tool.py (Conda/Mamba & Hardware Doctor)" -ForegroundColor Green
  }

  # 2. Deploy test_env_tool.py
  $TestsDir = Join-Path $TargetDir "tests"
  if (-not (Test-Path $TestsDir)) { New-Item -ItemType Directory -Path $TestsDir -Force | Out-Null }
  $testEnvSrc = Join-Path $TemplatesDir "tests\test_env_tool.py"
  $testEnvDst = Join-Path $TestsDir "test_env_tool.py"
  if (Test-Path $testEnvSrc) {
    Copy-Item $testEnvSrc $testEnvDst -Force
    Write-Host "  + Deployed Test: tests/test_env_tool.py" -ForegroundColor Gray
  }

  # 3. Deploy environment.yml tailored to Archetype
  $targetEnvYaml = Join-Path $TargetDir "environment.yml"
  if ((-not (Test-Path $targetEnvYaml)) -or $Force) {
    $templateName = switch ($Archetype) {
      "sec-research" { "environment.ai.yml" }
      "backend-api"  { "environment.api.yml" }
      default        { "environment.tool.yml" }
    }
    $templateSrc = Join-Path $TemplatesDir "conda\$templateName"
    if (Test-Path $templateSrc) {
      $envContent = Get-Content $templateSrc -Raw -Encoding UTF8
      # Format environment name with domain prefix and project name
      $envName = "$Archetype-$ProjectName".ToLower() -replace "[^a-z0-9_-]", "-"
      $envContent = $envContent -replace "^name:\s*[^\r\n]+", "name: $envName"
      [System.IO.File]::WriteAllText($targetEnvYaml, $envContent, [System.Text.Encoding]::UTF8)
      Write-Host "  + Deployed: environment.yml (Profile: $templateName, name: $envName)" -ForegroundColor Green
    }
  } else {
    Write-Host "  - Skipped: environment.yml already exists" -ForegroundColor Gray
  }
} else {
  Write-Host "  - Skipped: conda-env feature not enabled" -ForegroundColor DarkGray
}

# Step 4: Setup GitHub Actions Workflows & Templates
Write-Host "[4/5] Deploying GitHub Workflows & Policy CI..." -ForegroundColor Yellow

$GithubDir = Join-Path $TargetDir ".github"
$WorkflowsDir = Join-Path $GithubDir "workflows"
if (-not (Test-Path $WorkflowsDir)) { New-Item -ItemType Directory -Path $WorkflowsDir -Force | Out-Null }

# Collect all workflows (Archetype + Active Features)
$AllWorkflows = [System.Collections.Generic.HashSet[string]]::new()
foreach ($wf in $SelectedArchetype.githubWorkflows) {
  [void]$AllWorkflows.Add($wf)
}
foreach ($featKey in $ActiveFeatures) {
  $feat = $Config.features.$featKey
  if ($feat -and $feat.githubWorkflows) {
    foreach ($wf in $feat.githubWorkflows) {
      [void]$AllWorkflows.Add($wf)
    }
  }
}

foreach ($wf in $AllWorkflows) {
  $wfSrc = Join-Path $TemplatesDir "github\workflows\$wf"
  $wfDst = Join-Path $WorkflowsDir $wf
  if (Test-Path $wfSrc) {
    $wfContent = Get-Content $wfSrc -Raw -Encoding UTF8
    $customized = $false

    # 1. Dynamic scopes injection for policy.yml
    if ($wf -eq "policy.yml" -and $SelectedArchetype.defaultScopes) {
      $formattedScopes = "/* SCOPES_PLACEHOLDER_START */`n"
      foreach ($s in $SelectedArchetype.defaultScopes) {
        $formattedScopes += "              `"$s`",`n"
      }
      $formattedScopes += "              /* SCOPES_PLACEHOLDER_END */"

      $wfContent = [System.Text.RegularExpressions.Regex]::Replace(
        $wfContent,
        '/\*\s*SCOPES_PLACEHOLDER_START\s*\*/[\s\S]*?/\*\s*SCOPES_PLACEHOLDER_END\s*\*/',
        $formattedScopes
      )
      $customized = $true
    }

    # 2. Hash-based Jitter Cron injection for scheduled workflows
    if ($wfContent -match 'CRON_PLACEHOLDER_START') {
      $assignedCron = if ($wf -eq "codeql.yml") { $ProjectWeeklyCron } else { $ProjectMonthlyCron }
      $formattedCron = "# /* CRON_PLACEHOLDER_START */`n    - cron: '$assignedCron'`n    # /* CRON_PLACEHOLDER_END */"
      $wfContent = [System.Text.RegularExpressions.Regex]::Replace(
        $wfContent,
        '#\s*/\*\s*CRON_PLACEHOLDER_START\s*\*/[\s\S]*?#\s*/\*\s*CRON_PLACEHOLDER_END\s*\*/',
        $formattedCron
      )
      $customized = $true
    }

    # 3. Optional bot-author exemption for the PR body contract steps
    $botMarker = "github.event_name == 'pull_request' # /* BOT_PR_EXEMPT_PLACEHOLDER */"
    if ($wfContent.Contains($botMarker)) {
      $bodyGuard = if ($ActiveFeatures -contains "bot-pr-exempt") {
        "github.event_name == 'pull_request' && github.event.pull_request.user.type != 'Bot'"
      } else {
        "github.event_name == 'pull_request'"
      }
      $wfContent = $wfContent.Replace($botMarker, $bodyGuard)
      $customized = $true
    }

    # 4. Tailoring for ci.yml (Product CI)
    if ($wf -eq "ci.yml") {
      $runsOn = if ($Archetype -eq "desktop-app") { "windows-latest" } else { "ubuntu-latest" }
      $wfContent = [System.Text.RegularExpressions.Regex]::Replace(
        $wfContent,
        '/\*\s*RUNS_ON_PLACEHOLDER\s*\*/[\s\S]*?/\*\s*RUNS_ON_PLACEHOLDER_END\s*\*/',
        $runsOn
      )

      $ciSteps = switch ($Archetype) {
        { $_ -in "web-spa", "backend-api" } {
@"
      # /* CI_STEPS_PLACEHOLDER_START */
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: `${{ hashFiles('package-lock.json') != '' && 'npm' || '' }}
      - name: Install dependencies
        run: |
          if [ -f package-lock.json ]; then
            npm ci
          elif [ -f package.json ]; then
            npm install
          else
            echo "No package.json found; skipping dependency installation."
          fi
      - name: Code Quality (Lint)
        run: |
          if [ -f package.json ]; then
            npm run lint --if-present
          else
            echo "No package.json found; skipping lint."
          fi
      - name: Run Tests
        run: |
          if [ -f package.json ]; then
            npm test --if-present
          else
            echo "No package.json found; skipping tests."
          fi
      - name: Build Project
        run: |
          if [ -f package.json ]; then
            npm run build --if-present
          else
            echo "No package.json found; skipping build."
          fi
      # /* CI_STEPS_PLACEHOLDER_END */
"@
        }
        "desktop-app" {
@"
      # /* CI_STEPS_PLACEHOLDER_START */
      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'
      - name: Code Quality (Lint)
        shell: pwsh
        run: |
          `$projects = Get-ChildItem -Path . -Recurse -Filter *.sln, *.*proj
          if (`$projects.Count -gt 0) {
            dotnet format --verify-no-changes
          } else {
            Write-Host "No .NET solution or project found; skipping lint."
          }
      - name: Run Tests
        shell: pwsh
        run: |
          `$projects = Get-ChildItem -Path . -Recurse -Filter *.sln, *.*proj
          if (`$projects.Count -gt 0) {
            dotnet test
          } else {
            Write-Host "No .NET solution or project found; skipping tests."
          }
      - name: Build Project
        shell: pwsh
        run: |
          `$projects = Get-ChildItem -Path . -Recurse -Filter *.sln, *.*proj
          if (`$projects.Count -gt 0) {
            dotnet build -c Release
          } else {
            Write-Host "No .NET solution or project found; skipping build."
          }
      # /* CI_STEPS_PLACEHOLDER_END */
"@
        }
        "sec-research" {
@"
      # /* CI_STEPS_PLACEHOLDER_START */
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          if [ -f requirements.txt ]; then
            pip install -r requirements.txt
          fi
          pip install flake8
      - name: Code Quality (Lint)
        run: |
          python_files=`$(find . -name "*.py" -not -path "*/.*" -not -path "./tools/*" | head -n 1)
          if [ -n "`$python_files" ]; then
            python -m flake8 --exclude=.git,__pycache__,tools,tests
          else
            echo "No project python files found; skipping lint."
          fi
      - name: Run Tests
        run: |
          if [ -d "tests" ]; then
            python -m unittest discover -s tests
          else
            echo "No tests directory found; skipping tests."
          fi
      # /* CI_STEPS_PLACEHOLDER_END */
"@
        }
        default {
@"
      # /* CI_STEPS_PLACEHOLDER_START */
      - name: Baseline Verification
        run: |
          echo "No build or test commands configured for this archetype. Baseline check passed."
      # /* CI_STEPS_PLACEHOLDER_END */
"@
        }
      }

      $wfContent = [System.Text.RegularExpressions.Regex]::Replace(
        $wfContent,
        '#\s*/\*\s*CI_STEPS_PLACEHOLDER_START\s*\*/[\s\S]*?#\s*/\*\s*CI_STEPS_PLACEHOLDER_END\s*\*/',
        $ciSteps.Trim()
      )
      $customized = $true
    }

    if ($customized) {
      [System.IO.File]::WriteAllText($wfDst, $wfContent, [System.Text.Encoding]::UTF8)
      Write-Host "  + Deployed Workflow: .github/workflows/$wf (Tailored / Jitter Configured)" -ForegroundColor Green
    } else {
      Copy-Item $wfSrc $wfDst -Force
      Write-Host "  + Deployed Workflow: .github/workflows/$wf" -ForegroundColor Gray
    }
  }
}

$githubFilesToDeploy = [System.Collections.Generic.List[string]]::new()
foreach ($ghFile in $SelectedArchetype.githubFiles) {
  if ($Flow -eq "direct-push" -and $ghFile -eq "pull_request_template.md") {
    Write-Host "  - Skipped: pull_request_template.md (direct-push mode)" -ForegroundColor DarkGray
    continue
  }
  $githubFilesToDeploy.Add($ghFile)
}
if ($Flow -eq "pr" -and -not $githubFilesToDeploy.Contains("pull_request_template.md")) {
  $githubFilesToDeploy.Add("pull_request_template.md")
}

foreach ($ghFile in $githubFilesToDeploy) {
  $ghSrc = Join-Path $TemplatesDir "github\$ghFile"
  $ghDst = Join-Path $GithubDir $ghFile
  if (Test-Path $ghSrc) {
    Copy-Item $ghSrc $ghDst -Force
    Write-Host "  + Deployed GitHub Template: .github/$ghFile" -ForegroundColor Gray
  }
}

# Deploy Architecture Decision Records (ADR) framework
$adrSrcDir = Join-Path $TemplatesDir "docs\adr"
if (Test-Path $adrSrcDir) {
  $docsDir = Join-Path $TargetDir "docs"
  $adrDstDir = Join-Path $docsDir "adr"
  if (-not (Test-Path $adrDstDir)) { New-Item -ItemType Directory -Path $adrDstDir -Force | Out-Null }

  Get-ChildItem $adrSrcDir -File | ForEach-Object {
    $dstFile = Join-Path $adrDstDir $_.Name
    if ((-not (Test-Path $dstFile)) -or $Force) {
      Copy-Item $_.FullName $dstFile -Force
      Write-Host "  + Deployed ADR: docs/adr/$($_.Name)" -ForegroundColor Green
    } else {
      Write-Host "  = Retained ADR: docs/adr/$($_.Name)" -ForegroundColor DarkGray
    }
  }
}

# Auto-inject Secrets via gh CLI if present
$ApiKey = $env:SILICONFLOW_API_KEY
$SecretName = "SILICONFLOW_API_KEY"
if (-not $ApiKey) { $ApiKey = $env:DEFAULT_API_KEY }
if (-not $ApiKey) { $ApiKey = $env:OPENAI_KEY; $SecretName = "OPENAI_KEY" }

if ($ApiKey -and (Test-Path $GitDir)) {
  try {
    Push-Location $TargetDir
    $remoteUrl = git remote get-url origin 2>$null
    Pop-Location
    if ($remoteUrl -match 'github\.com[:/](?<owner>[^/]+)/(?<repo>[^/.]+)') {
      $repoSlug = "$($Matches['owner'])/$($Matches['repo'])"
      Write-Host "  + Auto-injecting $SecretName into GitHub repo $repoSlug via gh CLI..." -ForegroundColor Cyan
      gh secret set $SecretName --body "$ApiKey" -R $repoSlug 2>$null
      if ($LASTEXITCODE -eq 0) {
        Write-Host "  + Successfully configured GitHub Secret: $SecretName on $repoSlug" -ForegroundColor Green
      }
    }
  } catch {
    # Non-fatal
  }
}

# Step 5: Final Summary
Write-Host "[5/5] Scaffolding Complete!" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "✨ Project '$ProjectName' is fully scaffolded!" -ForegroundColor Green
Write-Host "   - Archetype: $Archetype ($($SelectedArchetype.name))"
Write-Host "   - Workflow : $Flow $(if ($Flow -eq 'direct-push') { '(免 PR 主幹直接推送)' } else { '(Pull Request 分支審查流程)' })"
Write-Host "   - Release  : $(if ($releaseConfig.strategy -and $releaseConfig.strategy -ne 'none') { "$($releaseConfig.strategy) (Version file: $($releaseConfig.versionFile))" } else { 'none (免版本管理)' })"
Write-Host "   - Features : $(if ($ActiveFeatures.Count -gt 0) { $ActiveFeatures -join ', ' } else { 'None' })"
Write-Host "   - Scopes   : $($SelectedArchetype.defaultScopes -join ', ')"
Write-Host "   - Rules    : AGENTS.md, .agent/rules.md, MEMORY.md"
Write-Host "   - Tools    : $(if ($SelectedArchetype.toolFiles) { $SelectedArchetype.toolFiles -join ', ' } else { 'None' })$(if ($ActiveFeatures -contains 'conda-env') { ', env_tool.py' })"
Write-Host "   - Conda    : $(if ($ActiveFeatures -contains 'conda-env') { 'environment.yml deployed (Run: python tools/env_tool.py setup)' } else { 'Disabled' })"
$skippedTotal = $SkippedTestsNotShipped.Count + $SkippedTestsNoConda.Count
$skippedText = "all deployed"
if ($skippedTotal -gt 0) {
  $skippedReasons = @()
  if ($SkippedTestsNotShipped.Count -gt 0) {
    $skippedReasons += "$($SkippedTestsNotShipped.Count) for tools this archetype does not ship"
  }
  if ($SkippedTestsNoConda.Count -gt 0) {
    $skippedReasons += "$($SkippedTestsNoConda.Count) for conda-env (feature disabled)"
  }
  $skippedText = "$skippedTotal intentionally skipped: " + ($skippedReasons -join ", ")
}
Write-Host "   - Tests    : $skippedText" -ForegroundColor $(if ($skippedTotal -gt 0) { 'Yellow' } else { 'Gray' })
Write-Host "   - Jitter   : Monthly ($ProjectMonthlyCron), Weekly ($ProjectWeeklyCron)"
Write-Host "   - Workflows: $($AllWorkflows -join ', ')"
Write-Host "=================================================" -ForegroundColor Cyan
