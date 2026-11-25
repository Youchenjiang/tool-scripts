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

# ----------------------------------------------------
# 安裝並啟用 idalib (Headless 無介面 Python 庫)
# ----------------------------------------------------
function Setup-IdaLib {
    $pythonExe = Join-Path $global:IdaInstallDir ".conda\python.exe"
    $idalibDir = Join-Path $global:IdaInstallDir "idalib\python"

    if (-not (Test-Path $idalibDir)) {
        Write-Host "  [!] 提示：未在目錄找到 idalib\python，略過 idalib 安裝。" -ForegroundColor DarkGray
        return $true
    }

    Write-Host "  -> 正在安裝 idalib (idapro Python 套件)..." -ForegroundColor Cyan
    & $pythonExe -m pip install (Join-Path $idalibDir ".") --no-warn-script-location
    
    Write-Host "  -> 正在啟用 idalib 動態庫配置..." -ForegroundColor Cyan
    $activateScript = Join-Path $idalibDir "py-activate-idalib.py"
    if (Test-Path $activateScript) {
        & $pythonExe $activateScript
    }

    Write-Host "  [+] idalib 安裝與啟用完成！" -ForegroundColor Green
    return $true
}

# ----------------------------------------------------
# 安裝 ida_feeds 相依套件與配置 flair 工具路徑
# ----------------------------------------------------
function Setup-IdaFeeds {
    $pythonExe = Join-Path $global:IdaInstallDir ".conda\python.exe"
    $feedsDir = Join-Path $global:IdaInstallDir "plugins\ida_feeds"

    if (-not (Test-Path $feedsDir)) {
        Write-Host "  [!] 提示：未找到 plugins\ida_feeds 目錄，略過 feeds 配置。" -ForegroundColor DarkGray
        return $true
    }

    $reqFile = Join-Path $feedsDir "requirements.txt"
    if (Test-Path $reqFile) {
        Write-Host "  -> 正在安裝 ida_feeds 相依套件 (rpyc, PyQt5, 等)..." -ForegroundColor Cyan
        & $pythonExe -m pip install -r $reqFile --no-warn-script-location
        Write-Host "  [+] ida_feeds 相依套件安裝完成！" -ForegroundColor Green
    }

    # 自動設定 config.json
    $flairDir = Join-Path $global:IdaInstallDir "tools\flair"
    $configFile = Join-Path $feedsDir "config.json"
    $flairJsonPath = ($flairDir -replace "\\", "/")
    $configContent = @"
{
    "flair": "$flairJsonPath"
}
"@
    [System.IO.File]::WriteAllText($configFile, $configContent, [System.Text.Encoding]::UTF8)
    Write-Host "  [+] 自動配置 ida_feeds\config.json (flair: $flairJsonPath) 完成！" -ForegroundColor Green
    return $true
}

# ----------------------------------------------------
# 執行 Keygen 授權產生與 DLL 二進位補丁替換
# ----------------------------------------------------
function Apply-KeygenAndPatch {
    $pythonExe = Join-Path $global:IdaInstallDir ".conda\python.exe"
    $keygenScript = Join-Path $global:IdaInstallDir "keygen3.py"

    if (-not (Test-Path $keygenScript)) {
        Write-Host "  [!] 提示：目錄未找到 keygen3.py，略過授權補丁步驟。" -ForegroundColor DarkGray
        return $true
    }

    Write-Host "  -> 正在執行 keygen3.py 產生授權憑證與 DLL 模組補丁..." -ForegroundColor Cyan
    Push-Location $global:IdaInstallDir
    try {
        & $pythonExe "keygen3.py"
    } finally {
        Pop-Location
    }

    # 備份與替換 ida.dll
    $idaDll = Join-Path $global:IdaInstallDir "ida.dll"
    $idaDllPatched = Join-Path $global:IdaInstallDir "ida.dll.patched"
    if (Test-Path $idaDllPatched) {
        $bak = Join-Path $global:IdaInstallDir "ida.dll.bak"
        if (-not (Test-Path $bak)) {
            Copy-Item $idaDll $bak -Force
            Write-Host "  [+] 已備份原版 ida.dll -> ida.dll.bak" -ForegroundColor DarkGray
        }
        Move-Item $idaDllPatched $idaDll -Force
        Write-Host "  [+] 成功套用 ida.dll 補丁！" -ForegroundColor Green
    }

    # 備份與替換 ida32.dll
    $ida32Dll = Join-Path $global:IdaInstallDir "ida32.dll"
    $ida32DllPatched = Join-Path $global:IdaInstallDir "ida32.dll.patched"
    if (Test-Path $ida32DllPatched) {
        $bak32 = Join-Path $global:IdaInstallDir "ida32.dll.bak"
        if (-not (Test-Path $bak32)) {
            Copy-Item $ida32Dll $bak32 -Force
            Write-Host "  [+] 已備份原版 ida32.dll -> ida32.dll.bak" -ForegroundColor DarkGray
        }
        Move-Item $ida32DllPatched $ida32Dll -Force
        Write-Host "  [+] 成功套用 ida32.dll 補丁！" -ForegroundColor Green
    }

    # 同步授權檔案至 APPDATA
    $hexlic = Join-Path $global:IdaInstallDir "idapro.hexlic"
    if (Test-Path $hexlic) {
        $appdataHexRays = Join-Path $env:APPDATA "Hex-Rays\IDA Pro"
        if (-not (Test-Path $appdataHexRays)) {
            New-Item -ItemType Directory -Path $appdataHexRays -Force | Out-Null
        }
        Copy-Item $hexlic (Join-Path $appdataHexRays "idapro.hexlic") -Force
        Copy-Item $hexlic (Join-Path $env:APPDATA "Hex-Rays\idapro.hexlic") -Force
        Write-Host "  [+] idapro.hexlic 授權檔已部署至目錄與 %APPDATA%！" -ForegroundColor Green
    }

    return $true
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      IDA Pro 9.1 一鍵自動化配置與維護工具箱" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  - 目標目錄 : $global:IdaInstallDir" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Cyan
