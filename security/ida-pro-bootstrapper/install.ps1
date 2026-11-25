# ==============================================================================
# IDA Professional 9.1 - 自動化安裝、環境配置與維護精靈
# ==============================================================================
[CmdletBinding()]
param (
    [Parameter(Position = 0)]
    [string]$IdaPath
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = (Get-Location).Path }

$global:IdaInstallDir = if ($IdaPath) { $IdaPath.Trim('"') } else { $ScriptDir }

# ----------------------------------------------------
# 尋找系統 Conda / Mamba 執行路徑
# ----------------------------------------------------
function Find-CondaExe {
    $commonPaths = @(
        "C:\MyAPP\Dev\Env\Miniforge3\condabin\conda.bat",
        "C:\MyAPP\Dev\Env\Miniforge3\Scripts\conda.exe",
        "$env:USERPROFILE\miniforge3\condabin\conda.bat",
        "$env:USERPROFILE\miniconda3\condabin\conda.bat",
        "$env:LOCALAPPDATA\miniforge3\condabin\conda.bat",
        "$env:ProgramData\miniforge3\condabin\conda.bat"
    )
    foreach ($p in $commonPaths) {
        if (Test-Path $p) { return $p }
    }
    if (Get-Command "conda.bat" -ErrorAction SilentlyContinue) {
        return (Get-Command "conda.bat").Source
    }
    return $null
}

# ----------------------------------------------------
# 建立專屬 .conda (Python 3.11) 本地隔離環境
# ----------------------------------------------------
function Setup-CondaEnv {
    $condaPython = Join-Path $global:IdaInstallDir ".conda\python.exe"
    if (Test-Path $condaPython) {
        Write-Host "  [+] 專屬 .conda (Python 3.11) 已就緒。" -ForegroundColor Green
        return $true
    }

    $condaBat = Find-CondaExe
    if (-not $condaBat) {
        Write-Host "  [!] 錯誤：未在系統中找到 Conda/Miniforge，無法自動建立 Python 3.11 環境。" -ForegroundColor Red
        return $false
    }

    Write-Host "  -> 正在建立專案本地前綴環境: $global:IdaInstallDir\.conda (Python 3.11)..." -ForegroundColor Cyan
    & $condaBat create -p (Join-Path $global:IdaInstallDir ".conda") python=3.11 -y

    if (Test-Path $condaPython) {
        Write-Host "  [+] 成功建立 .conda (Python 3.11)！" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  [!] 建立 .conda 環境失敗。" -ForegroundColor Red
        return $false
    }
}

# ----------------------------------------------------
# 綁定 IDAPython 至本地 .conda (idapyswitch)
# ----------------------------------------------------
function Setup-IdaPySwitch {
    $switcher = Join-Path $global:IdaInstallDir "idapyswitch.exe"
    $dllPath = Join-Path $global:IdaInstallDir ".conda\python3.dll"

    if (-not (Test-Path $switcher)) {
        Write-Host "  [!] 錯誤：未在 IDA 目錄找到 idapyswitch.exe！" -ForegroundColor Red
        return $false
    }
    if (-not (Test-Path $dllPath)) {
        Write-Host "  [!] 錯誤：.conda 未就緒，缺少 python3.dll！" -ForegroundColor Red
        return $false
    }

    Write-Host "  -> 正在透過 idapyswitch 將 IDAPython 綁定至本地 .conda..." -ForegroundColor Cyan
    & $switcher --force-path $dllPath
    Write-Host "  [+] 成功完成 IDAPython 綁定至: $dllPath" -ForegroundColor Green
    return $true
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      IDA Pro 9.1 一鍵自動化配置與維護工具箱" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  - 目標目錄 : $global:IdaInstallDir" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Cyan
