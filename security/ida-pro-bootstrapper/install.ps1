# ==============================================================================
# IDA Professional 9.1 - 一鍵自動化安裝、環境配置與維護工具箱
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

# 自動判斷 IDA 安裝目錄
function Resolve-IdaDir {
    if ($IdaPath) { return (Resolve-Path $IdaPath.Trim('"')).Path }
    if (Test-Path (Join-Path $ScriptDir "ida.exe")) { return $ScriptDir }
    $candidates = @(
        "C:\MyAPP\Sec\IDA Professional 9.1",
        "C:\Program Files\IDA Professional 9.1",
        "C:\Program Files\IDA Pro 9.1"
    )
    foreach ($c in $candidates) {
        if (Test-Path (Join-Path $c "ida.exe")) { return $c }
    }
    return $ScriptDir
}

$global:IdaInstallDir = Resolve-IdaDir

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

# ----------------------------------------------------
# 建立桌面與開始功能表捷徑 (綁定 ida.ico)
# ----------------------------------------------------
function Create-Shortcuts {
    $idaExe = Join-Path $global:IdaInstallDir "ida.exe"
    $icoPath = Join-Path $global:IdaInstallDir "ida.ico"

    if (-not (Test-Path $idaExe)) {
        Write-Host "  [!] 錯誤：未在目錄找到 ida.exe！" -ForegroundColor Red
        return $false
    }

    $targetShortcuts = @(
        @{ Name = "桌面"; Path = Join-Path ([Environment]::GetFolderPath('Desktop')) "IDA Professional 9.1.lnk" },
        @{ Name = "開始功能表"; Path = Join-Path ([Environment]::GetFolderPath('Programs')) "IDA Professional 9.1.lnk" }
    )

    try {
        $wsh = New-Object -ComObject WScript.Shell
        foreach ($item in $targetShortcuts) {
            $shortcut = $wsh.CreateShortcut($item.Path)
            $shortcut.TargetPath = $idaExe
            $shortcut.WorkingDirectory = $global:IdaInstallDir
            $shortcut.Description = "IDA Professional 9.1 (Disassembler & Decompiler)"

            if (Test-Path $icoPath) {
                $shortcut.IconLocation = $icoPath
            }
            $shortcut.Save()
            [System.Runtime.InteropServices.Marshal]::ReleaseComObject($shortcut) | Out-Null
            Write-Host "  [+] 已在$($item.Name)建立捷徑：$($item.Path)" -ForegroundColor Green
        }
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wsh) | Out-Null
        Write-Host "  [+] 支援按鍵盤 Win 鍵直接搜尋 'ida' 秒開！" -ForegroundColor Cyan
    } catch {
        Write-Host "  [!] 建立捷徑時發生錯誤：$_" -ForegroundColor Red
    }
}

# ----------------------------------------------------
# 一鍵全自動完整配置流程
# ----------------------------------------------------
function Run-FullSetup {
    Write-Host "`n[1/6] 建立專屬 .conda (Python 3.11) 環境..." -ForegroundColor Yellow
    $ok = Setup-CondaEnv
    if (-not $ok) { return }

    Write-Host "`n[2/6] 綁定 IDAPython 至 .conda..." -ForegroundColor Yellow
    Setup-IdaPySwitch

    Write-Host "`n[3/6] 安裝與啟用 idalib (Headless Python API)..." -ForegroundColor Yellow
    Setup-IdaLib

    Write-Host "`n[4/6] 配置 ida_feeds 外掛與 flair 路徑..." -ForegroundColor Yellow
    Setup-IdaFeeds

    Write-Host "`n[5/6] 產生授權憑證與 DLL 模組補丁..." -ForegroundColor Yellow
    Apply-KeygenAndPatch

    Write-Host "`n[6/6] 建立桌面與開始功能表雙捷徑..." -ForegroundColor Yellow
    Create-Shortcuts

    Write-Host "`n========================================================" -ForegroundColor Green
    Write-Host "   IDA Pro 9.1 一鍵自動化配置全數完成！" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
}

# ----------------------------------------------------
# 狀態看板與主選單
# ----------------------------------------------------
function Show-Menu {
    Clear-Host
    Write-Host "========================================================" -ForegroundColor Cyan
    Write-Host "      IDA Professional 9.1 一鍵自動化維護工具箱" -ForegroundColor Cyan
    Write-Host "========================================================" -ForegroundColor Cyan

    $condaReady = Test-Path (Join-Path $global:IdaInstallDir ".conda\python.exe")
    $idapyTarget = (Get-ItemProperty "HKCU:\Software\Hex-Rays\IDA" -ErrorAction SilentlyContinue).Python3TargetDLL
    $idalibReady = Test-Path (Join-Path $global:IdaInstallDir ".conda\Lib\site-packages\idapro")
    $licReady = Test-Path (Join-Path $global:IdaInstallDir "idapro.hexlic")
    $desktopLnk = Test-Path (Join-Path ([Environment]::GetFolderPath('Desktop')) "IDA Professional 9.1.lnk")
    $startLnk = Test-Path (Join-Path ([Environment]::GetFolderPath('Programs')) "IDA Professional 9.1.lnk")

    Write-Host "【當前設定與環境狀態】" -ForegroundColor White
    Write-Host "  - IDA 目錄  : $global:IdaInstallDir" -ForegroundColor Cyan
    if ($condaReady) {
        Write-Host "  - .conda    : [已就緒] 本地 Python 3.11 環境" -ForegroundColor Green
    } else {
        Write-Host "  - .conda    : [未建立] 尚未建立本地 .conda 環境" -ForegroundColor Red
    }

    if ($idapyTarget) {
        Write-Host "  - IDAPython : [已綁定] $idapyTarget" -ForegroundColor Green
    } else {
        Write-Host "  - IDAPython : [未配置] 需要執行 idapyswitch" -ForegroundColor Red
    }

    if ($idalibReady) {
        Write-Host "  - idalib    : [已啟用] idapro Python 套件就緒" -ForegroundColor Green
    } else {
        Write-Host "  - idalib    : [未安裝] 尚未啟用 idalib" -ForegroundColor Yellow
    }

    if ($licReady) {
        Write-Host "  - 授權狀態  : [已激活] idapro.hexlic (全架構反編譯器解鎖)" -ForegroundColor Green
    } else {
        Write-Host "  - 授權狀態  : [未激活] 需要執行 keygen3.py 補丁" -ForegroundColor Red
    }

    if ($desktopLnk -or $startLnk) {
        $locs = @()
        if ($startLnk) { $locs += "開始功能表 (按 Win 搜 ida 可開)" }
        if ($desktopLnk) { $locs += "桌面" }
        Write-Host "  - 系統捷徑  : [已就緒] $($locs -join ' / ')" -ForegroundColor Green
    } else {
        Write-Host "  - 系統捷徑  : [未建立]" -ForegroundColor Yellow
    }

    Write-Host "--------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "  [1] 一鍵全自動完整配置 (推薦全新環境或修復)" -ForegroundColor Cyan
    Write-Host "  [2] 重新啟用授權與 DLL 補丁 (重跑 keygen3.py 與 patch)" -ForegroundColor Yellow
    Write-Host "  [3] 修復 / 重新綁定 IDAPython (idapyswitch)" -ForegroundColor White
    Write-Host "  [4] 重新建立捷徑 (桌面與開始功能表)" -ForegroundColor White
    Write-Host "  [5] 直接啟動 IDA Pro 9.1 (ida.exe)" -ForegroundColor Green
    Write-Host "  [0] 離開" -ForegroundColor Gray
    Write-Host "========================================================" -ForegroundColor Cyan

    $opt = Read-Host "請輸入選項號碼 [1-5, 0]"
    $opt = if ($opt) { $opt.Trim() } else { "" }
    switch ($opt) {
        "1" { Run-FullSetup }
        "2" { Apply-KeygenAndPatch }
        "3" { Setup-IdaPySwitch }
        "4" { Create-Shortcuts }
        "5" {
            $idaExe = Join-Path $global:IdaInstallDir "ida.exe"
            if (Test-Path $idaExe) {
                Start-Process $idaExe -WorkingDirectory $global:IdaInstallDir
                Write-Host "  [+] 已啟動 IDA Pro 9.1！" -ForegroundColor Green
            } else {
                Write-Host "  [!] 未找到 ida.exe！" -ForegroundColor Red
            }
        }
        "0" { return }
        default {
            Write-Host "無效選項，請重新輸入。" -ForegroundColor Red
        }
    }
}

Show-Menu
