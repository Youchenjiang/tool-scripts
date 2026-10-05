<#
.SYNOPSIS
  Project Scaffolding Tool for Agent Rules, Git Policies & CI Workflows
.DESCRIPTION
  Two-tier project initializer:
  1. Select project Archetype (web-spa, backend-api, desktop-app, sec-research, minimal)
  2. Select optional Features (strict-linting, chained-prs, sec-enterprise)
.PARAMETER Archetype
  Project core archetype profile (or alias -Preset)
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

# 2. Resolve Active Features
$ActiveFeatures = @()
if ($NoFeatures) {
  $ActiveFeatures = @()
} elseif ($AllFeatures) {
  $ActiveFeatures = @($Config.features.PSObject.Properties.Name)
} elseif ($Features -and $Features.Count -gt 0) {
  $ActiveFeatures = $Features
} else {
  # Default to recommended features for this archetype
  $recommended = @($SelectedArchetype.recommendedFeatures)
  if ($recommended.Count -gt 0) {
    Write-Host ""
    Write-Host "Stage 2: Features Configuration:" -ForegroundColor Cyan
    Write-Host "Recommended features for ${Archetype}: $($recommended -join ', ')" -ForegroundColor Yellow
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

# Add Archetype agent rules
foreach ($ruleFile in $SelectedArchetype.agentRules) {
  $rulePath = Join-Path $TemplatesDir "agent-rules\$ruleFile"
  if (Test-Path $rulePath) {
    $content = Get-Content $rulePath -Raw -Encoding UTF8
    $CombinedRules += "`n`n" + $content
  }
}

# Add Feature agent rules
foreach ($featKey in $ActiveFeatures) {
  $feat = $Config.features.$featKey
  if ($feat -and $feat.agentRules) {
    foreach ($ruleFile in $feat.agentRules) {
      $rulePath = Join-Path $TemplatesDir "agent-rules\$ruleFile"
      if (Test-Path $rulePath) {
        $content = Get-Content $rulePath -Raw -Encoding UTF8
        $CombinedRules += "`n`n" + $content
      }
    }
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
$HookSrc = Join-Path $TemplatesDir "git\hooks\commit-msg"

if (Test-Path $GitDir) {
  $HooksDir = Join-Path $GitDir "hooks"
  if (-not (Test-Path $HooksDir)) { New-Item -ItemType Directory -Path $HooksDir -Force | Out-Null }
  
  $HookDst = Join-Path $HooksDir "commit-msg"
  if (Test-Path $HookSrc) {
    Copy-Item $HookSrc $HookDst -Force
    Write-Host "  + Installed: .git/hooks/commit-msg" -ForegroundColor Green
  }

  try {
    Push-Location $TargetDir
    git config commit.template .gitmessage.txt
    Pop-Location
    Write-Host "  + Configured: git config commit.template .gitmessage.txt" -ForegroundColor Green
  } catch {
    # Non-fatal
  }
} else {
  Write-Host "  (Note: .git directory not found. Run 'git init' later to install hooks)" -ForegroundColor DarkYellow
}

# Setup version-controlled scripts/hooks/ for npm prepare lifecycle
if (Test-Path $HookSrc) {
  $TargetScriptsDir = Join-Path $TargetDir "scripts"
  $TargetScriptsHooksDir = Join-Path $TargetScriptsDir "hooks"
  if (-not (Test-Path $TargetScriptsHooksDir)) { New-Item -ItemType Directory -Path $TargetScriptsHooksDir -Force | Out-Null }
  Copy-Item $HookSrc (Join-Path $TargetScriptsHooksDir "commit-msg") -Force
  
  $installHooksSrc = Join-Path $TemplatesDir "git\scripts\install-hooks.mjs"
  if (Test-Path $installHooksSrc) {
    Copy-Item $installHooksSrc (Join-Path $TargetScriptsDir "install-hooks.mjs") -Force
    Write-Host "  + Deployed: scripts/install-hooks.mjs & scripts/hooks/commit-msg" -ForegroundColor Gray
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
if ($SelectedArchetype.toolFiles) {
  $ToolsDir = Join-Path $TargetDir "tools"
  if (-not (Test-Path $ToolsDir)) { New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null }
  foreach ($tf in $SelectedArchetype.toolFiles) {
    $tfSrc = Join-Path $TemplatesDir "tools\$tf"
    $tfDst = Join-Path $ToolsDir $tf
    if (Test-Path $tfSrc) {
      Copy-Item $tfSrc $tfDst -Force
      Write-Host "  + Deployed Tool: tools/$tf" -ForegroundColor Gray
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

    if ($customized) {
      [System.IO.File]::WriteAllText($wfDst, $wfContent, [System.Text.Encoding]::UTF8)
      Write-Host "  + Deployed Workflow: .github/workflows/$wf (Tailored / Jitter Configured)" -ForegroundColor Green
    } else {
      Copy-Item $wfSrc $wfDst -Force
      Write-Host "  + Deployed Workflow: .github/workflows/$wf" -ForegroundColor Gray
    }
  }
}

foreach ($ghFile in $SelectedArchetype.githubFiles) {
  $ghSrc = Join-Path $TemplatesDir "github\$ghFile"
  $ghDst = Join-Path $GithubDir $ghFile
  if (Test-Path $ghSrc) {
    Copy-Item $ghSrc $ghDst -Force
    Write-Host "  + Deployed GitHub Template: .github/$ghFile" -ForegroundColor Gray
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
Write-Host "   - Features : $(if ($ActiveFeatures.Count -gt 0) { $ActiveFeatures -join ', ' } else { 'None' })"
Write-Host "   - Scopes   : $($SelectedArchetype.defaultScopes -join ', ')"
Write-Host "   - Rules    : AGENTS.md, .agent/rules.md, MEMORY.md"
Write-Host "   - Tools    : $(if ($SelectedArchetype.toolFiles) { $SelectedArchetype.toolFiles -join ', ' } else { 'None' })"
Write-Host "   - Jitter   : Monthly ($ProjectMonthlyCron), Weekly ($ProjectWeeklyCron)"
Write-Host "   - Workflows: $($AllWorkflows -join ', ')"
Write-Host "=================================================" -ForegroundColor Cyan
