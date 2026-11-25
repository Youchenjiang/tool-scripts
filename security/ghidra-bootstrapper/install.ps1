<#
.SYNOPSIS
    Ghidra Automation & Shortcut Bootstrapper
.DESCRIPTION
    Automates the installation, configuration, silent zero-console launcher generation,
    and dual shortcut registration (Desktop + Start Menu) for NSA Ghidra SRE framework (12.2+).
.PARAMETER InstallPath
    Target installation path for Ghidra (Default: C:\MyAPP\Sec\Ghidra)
.PARAMETER SkipDownload
    Skip downloading and use existing Ghidra directory
#>
param(
    [string]$InstallPath = "C:\MyAPP\Sec\Ghidra",
    [switch]$SkipDownload,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Detailed
    exit 0
}

function Write-Step {
    param([string]$Message)
    Write-Host "`n[+] $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "    $Message" -ForegroundColor Cyan
}

function Write-Warn {
    param([string]$Message)
    Write-Host "    $Message" -ForegroundColor Yellow
}

function Get-DownloadEngine {
    $aria2c = Get-Command aria2c -ErrorAction SilentlyContinue
    if (-not $aria2c -and (Test-Path "C:\MyAPP\Sec\BurpSuitePro\aria2c.exe")) {
        $aria2c = "C:\MyAPP\Sec\BurpSuitePro\aria2c.exe"
    }
    if ($aria2c) {
        return @{ Type = "aria2c"; Path = if ($aria2c -is [string]) { $aria2c } else { $aria2c.Source } }
    }
    return @{ Type = "curl"; Path = "curl.exe" }
}

function Find-JavaJdk {
    Write-Step "Checking for compatible 64-bit JDK (25+ recommended for Ghidra 12.2)..."
    
    $candidates = @(
        $env:JAVA_HOME,
        "C:\MyAPP\Dev\Env\jdk-25",
        "C:\Program Files\Java\jdk-25",
        "C:\MyAPP\Dev\Env\jdk-21",
        "C:\Program Files\Java\jdk-21"
    )

    foreach ($cand in $candidates) {
        if (-not $cand) { continue }
        $resolved = Resolve-Path $cand -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path -First 1
        if ($resolved -and (Test-Path "$resolved\bin\java.exe")) {
            Write-Info "Found compatible JDK at: $resolved"
            return $resolved
        }
    }

    $javaInPath = Get-Command java.exe -ErrorAction SilentlyContinue
    if ($javaInPath) {
        $binDir = Split-Path $javaInPath.Source
        $jdkHome = Split-Path $binDir
        if (Test-Path "$jdkHome\bin\javac.exe") {
            Write-Info "Found JDK via system PATH: $jdkHome"
            return $jdkHome
        }
    }

    Write-Warn "No compatible JDK 25+ found. Downloading portable Adoptium OpenJDK 25 LTS..."
    $devEnv = "C:\MyAPP\Dev\Env"
    if (-not (Test-Path $devEnv)) {
        New-Item -ItemType Directory -Path $devEnv -Force | Out-Null
    }

    $jdkZip = Join-Path $devEnv "openjdk25.zip"
    $jdkUrl = "https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.5.1%2B2/OpenJDK25U-jdk_x64_windows_hotspot_25.0.5.1_2.zip"
    $engine = Get-DownloadEngine

    if ($engine.Type -eq "aria2c") {
        & $engine.Path -x 16 -s 16 -k 1M -c -d $devEnv -o "openjdk25.zip" $jdkUrl
    } else {
        & curl.exe -L -o $jdkZip $jdkUrl
    }

    tar.exe -xf $jdkZip -C $devEnv
    Remove-Item $jdkZip -Force -ErrorAction SilentlyContinue
    $extractedJdk = Join-Path $devEnv "jdk-25.0.5.1+2"
    $targetJdk = Join-Path $devEnv "jdk-25"
    if (Test-Path $targetJdk) { Remove-Item $targetJdk -Recurse -Force }
    Rename-Item $extractedJdk "jdk-25"

    [Environment]::SetEnvironmentVariable('JAVA_HOME', $targetJdk, 'User')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($userPath -notlike "*$targetJdk\bin*") {
        [Environment]::SetEnvironmentVariable('Path', "$targetJdk\bin;$userPath", 'User')
    }

    Write-Info "Configured portable OpenJDK 25 LTS at: $targetJdk"
    return $targetJdk
}

function Install-GhidraDistribution {
    param([string]$TargetDir)

    if (Test-Path "$TargetDir\ghidraRun.bat") {
        Write-Info "Ghidra already exists at: $TargetDir"
        return
    }

    Write-Step "Downloading Ghidra 12.2 (Official Release for JDK 25)..."
    $parentDir = Split-Path $TargetDir
    if (-not (Test-Path $parentDir)) {
        New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
    }

    $url = "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.2_build/ghidra_12.2_PUBLIC_20261016.zip"
    $zipPath = Join-Path $parentDir "ghidra_download.zip"

    $engine = Get-DownloadEngine
    Write-Info "Using download engine: $($engine.Type)"

    if ($engine.Type -eq "aria2c") {
        & $engine.Path -x 16 -s 16 -k 1M -c -d $parentDir -o "ghidra_download.zip" $url
    } else {
        & curl.exe -L -o $zipPath $url
    }

    Write-Step "Extracting archive to target directory..."
    tar.exe -xf $zipPath -C $parentDir
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

    $extractedFolder = Join-Path $parentDir "ghidra_12.2_PUBLIC"
    if (Test-Path $extractedFolder -and $extractedFolder -ne $TargetDir) {
        if (Test-Path $TargetDir) {
            Remove-Item $TargetDir -Recurse -Force
        }
        Rename-Item $extractedFolder (Split-Path $TargetDir -Leaf)
    }

    Write-Info "Extracted and configured target directory: $TargetDir"
}

function Configure-Launchers {
    param(
        [string]$TargetDir,
        [string]$JdkPath
    )

    Write-Step "Configuring silent launcher & launch properties..."

    # 1. Update support\launch.properties without UTF-8 BOM
    $launchProps = Join-Path $TargetDir "support\launch.properties"
    if ((Test-Path $launchProps) -and $JdkPath) {
        $content = Get-Content $launchProps -Raw
        if ($content -match "JAVA_HOME_OVERRIDE=") {
            $content = $content -replace "JAVA_HOME_OVERRIDE=.*", "JAVA_HOME_OVERRIDE=$JdkPath"
            $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
            [System.IO.File]::WriteAllText($launchProps, $content, $utf8NoBom)
            Write-Info "Set JAVA_HOME_OVERRIDE in launch.properties -> $JdkPath (UTF-8 No BOM)"
        }
    }

    # 2. Patch support\launch.bat
    $launchBat = Join-Path $TargetDir "support\launch.bat"
    if (Test-Path $launchBat) {
        $content = Get-Content $launchBat -Raw
        if ($content -match "start `"%APPNAME%`" /B `"!JAVA_CMD!`"") {
            $content = $content.Replace('start "%APPNAME%" /B "!JAVA_CMD!"', 'start "%APPNAME%" "!JAVA_CMD!"')
            $content = $content.Replace('%SystemRoot%\System32\timeout.exe /NOBREAK 1 > NUL', 'ping -n 2 127.0.0.1 >nul')
            Set-Content -Path $launchBat -Value $content -Encoding ASCII
            Write-Info "Optimized launch.bat background execution parameters"
        }
    }

    # 3. Create Ghidra.bat
    $ghidraBat = Join-Path $TargetDir "Ghidra.bat"
    $batContent = @"
@echo off
setlocal
cd /d "%~dp0"

if not defined JAVA_HOME (
    if exist "$JdkPath" (
        set "JAVA_HOME=$JdkPath"
    ) else if exist "C:\MyAPP\Dev\Env\jdk-25" (
        set "JAVA_HOME=C:\MyAPP\Dev\Env\jdk-25"
    ) else if exist "C:\Program Files\Java\jdk-25" (
        set "JAVA_HOME=C:\Program Files\Java\jdk-25"
    )
)

call "%~dp0ghidraRun.bat" %*
"@
    Set-Content -Path $ghidraBat -Value $batContent -Encoding ASCII
    Write-Info "Created Ghidra.bat launcher"

    # 4. Create Ghidra.vbs (Zero console window wrapper)
    $ghidraVbs = Join-Path $TargetDir "Ghidra.vbs"
    $vbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
strDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strDir
WshShell.Run """" & strDir & "\Ghidra.bat""", 0, False
"@
    Set-Content -Path $ghidraVbs -Value $vbsContent -Encoding ASCII
    Write-Info "Created Ghidra.vbs (silent background wrapper)"
}

function Register-DualShortcuts {
    param([string]$TargetDir)

    Write-Step "Creating dual shortcuts (Desktop + Start Menu for Win Search)..."

    $targetVbs = Join-Path $TargetDir "Ghidra.vbs"
    $iconPath = Join-Path $TargetDir "support\ghidra.ico"

    if (-not (Test-Path $iconPath)) {
        Write-Warn "Icon not found at $iconPath, using system default."
        $iconPath = ""
    }

    $wsh = New-Object -ComObject WScript.Shell
    $destinations = @(
        [System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), "Ghidra.lnk"),
        [System.IO.Path]::Combine([Environment]::GetFolderPath('Programs'), "Ghidra.lnk")
    )

    foreach ($dst in $destinations) {
        $sc = $wsh.CreateShortcut($dst)
        $sc.TargetPath = "wscript.exe"
        $sc.Arguments = "`"$targetVbs`""
        $sc.WorkingDirectory = $TargetDir
        if ($iconPath) {
            $sc.IconLocation = "$iconPath, 0"
        }
        $sc.Description = "Ghidra Software Reverse Engineering Framework"
        $sc.Save()
        Write-Info "Registered shortcut: $dst"
    }
}

# Main Execution Flow
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       Ghidra SRE 12.2 + JDK 25 Bootstrapper              " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$jdk = Find-JavaJdk

if (-not $SkipDownload) {
    Install-GhidraDistribution -TargetDir $InstallPath
}

Configure-Launchers -TargetDir $InstallPath -JdkPath $jdk
Register-DualShortcuts -TargetDir $InstallPath

Write-Host "`n[V] Ghidra 12.2 Bootstrapping & Shortcut Registration Completed Successfully!" -ForegroundColor Green
Write-Host "    - Install Directory : $InstallPath" -ForegroundColor Gray
Write-Host "    - JDK Location      : $jdk (JDK 25 LTS)" -ForegroundColor Gray
Write-Host "    - Desktop Shortcut  : Yes (Zero Terminal Popup)" -ForegroundColor Gray
Write-Host "    - Start Menu Search : Yes (Press Win, type 'ghidra')" -ForegroundColor Gray
