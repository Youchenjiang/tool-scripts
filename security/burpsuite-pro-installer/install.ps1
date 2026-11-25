# ==============================================================================
# Burp Suite Pro - 一鍵自動化安裝、配置與維護腳本
# ==============================================================================
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = (Get-Location).Path }
Set-Location -Path $ScriptDir

# ----------------------------------------------------
# 輔助函式：管理員權限檢查
# ----------------------------------------------------
function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# ----------------------------------------------------
# 輔助函式：檔案下載 (支援 aria2c 斷點續傳 / curl / PowerShell)
# ----------------------------------------------------
function Download-File {
    param (
        [string]$url,
        [string]$output,
        [long]$minBytes = 0
    )

    $outputFile = Join-Path $ScriptDir $output
    $aria2 = Join-Path $ScriptDir "aria2c.exe"

    if (Test-Path $aria2) {
        Write-Host "  [Speed] 使用 aria2c 多線程斷點續傳 (16 connections)..." -ForegroundColor DarkCyan
        & $aria2 -c -x 16 -s 16 -k 1M --allow-overwrite=true -o $output $url
    } elseif (Get-Command "curl.exe" -ErrorAction SilentlyContinue) {
        Write-Host "  [Standard] 使用 Windows 內建 curl.exe (斷點續傳)..." -ForegroundColor DarkYellow
        & curl.exe -# -L -C - -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" -o $outputFile $url
    } else {
        Write-Host "  [Fallback] 使用 PowerShell WebRequest 下載..." -ForegroundColor Gray
        $ProgressPreference = 'Continue'
        Invoke-WebRequest -Uri $url -OutFile $outputFile
    }

    if (Test-Path $outputFile) {
        $fileSize = (Get-Item $outputFile).Length
        if ($minBytes -gt 0 -and $fileSize -lt $minBytes) {
            Write-Host "  [!] 錯誤：下載檔案大小異常 ($([math]::Round($fileSize/1MB, 2)) MB < $([math]::Round($minBytes/1MB, 2)) MB)，可能遭遇防盜鏈或網路錯誤！" -ForegroundColor Red
            return $false
        }
        return $true
    }
    return $false
}

# ----------------------------------------------------
# 搜尋 JDK 21（優先本機綠色版，次選系統路徑）
# ----------------------------------------------------
function Find-JDK21Path {
    # 1. 優先檢查本目錄下的綠色版
    $portableExe = Join-Path $ScriptDir "jdk-21\bin\java.exe"
    if (Test-Path $portableExe) { return $portableExe }

    # 2. 常見系統路徑
    $defaultPaths = @(
        "C:\Program Files\Java\jdk-21\bin\java.exe",
        "C:\Program Files (x86)\Java\jdk-21\bin\java.exe"
    )
    foreach ($p in $defaultPaths) {
        if (Test-Path $p) { return $p }
    }

    # 3. 註冊表搜尋
    $regPaths = @(
        "HKLM:\SOFTWARE\JavaSoft\JDK\21*",
        "HKLM:\SOFTWARE\JavaSoft\Java Development Kit\21*"
    )
    foreach ($reg in $regPaths) {
        $foundReg = Get-ItemProperty -Path $reg -ErrorAction SilentlyContinue
        if ($foundReg -and $foundReg.JavaHome) {
            $exe = Join-Path $foundReg.JavaHome "bin\java.exe"
            if (Test-Path $exe) { return $exe }
        }
    }

    # 4. JAVA_HOME 環境變數
    if ($env:JAVA_HOME) {
        $exe = Join-Path $env:JAVA_HOME "bin\java.exe"
        if (Test-Path $exe) {
            $ver = & $exe -version 2>&1
            if ($ver -match '"21\.') { return $exe }
        }
    }

    # 5. 搜尋其他目錄
    $searchDirs = @("C:\Program Files\Java", "C:\Java", "D:\Java", "C:\Program Files (x86)\Java")
    foreach ($dir in $searchDirs) {
        if (Test-Path $dir) {
            $jdkFolders = Get-ChildItem -Path $dir -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*21*" }
            foreach ($folder in $jdkFolders) {
                $exe = Join-Path $folder.FullName "bin\java.exe"
                if (Test-Path $exe) { return $exe }
            }
        }
    }

    return $null
}

# ----------------------------------------------------
# JDK 21 安裝流程 (方案 B: 詢問使用綠色版或系統版)
# ----------------------------------------------------
function Install-JDK21Dialog {
    Write-Host "`n系統中未偵測到 JDK 21，請選擇安裝模式：" -ForegroundColor Yellow
    Write-Host "  [1] 下載綠色免安裝版 OpenJDK 21 (解壓至當前目錄 jdk-21\，免管理員權限，推薦)" -ForegroundColor Cyan
    Write-Host "  [2] 下載 Oracle JDK 21 安裝檔 (安裝至系統 Program Files，需系統管理員權限)" -ForegroundColor DarkYellow
    $choice = Read-Host "請輸入選項 (預設 1)"
    if ([string]::IsNullOrWhiteSpace($choice)) { $choice = "1" }

    if ($choice -eq "1") {
        Write-Host "`n  -> 正在從 Adoptium 官方下載 Eclipse Temurin JDK 21 綠色版 (約 200MB)..." -ForegroundColor Cyan
        $zipName = "jdk-21.zip"
        $downloadUrl = "https://api.adoptium.net/v3/binary/latest/21/ga/windows/x64/jdk/hotspot/normal/eclipse"
        $ok = Download-File $downloadUrl $zipName (150 * 1024 * 1024)

        if (-not $ok) {
            Write-Host "  [!] JDK 下載失敗，請檢查網路連線。" -ForegroundColor Red
            return $null
        }

        Write-Host "  -> 下載完成！正在解壓縮至本地目錄..." -ForegroundColor Cyan
        $tempExtract = Join-Path $ScriptDir "jdk-temp-extract"
        if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force }
        Expand-Archive -Path (Join-Path $ScriptDir $zipName) -DestinationPath $tempExtract -Force

        # 找到包含 bin\java.exe 的主資料夾
        $innerDir = Get-ChildItem -Path $tempExtract -Directory | Where-Object { Test-Path (Join-Path $_.FullName "bin\java.exe") } | Select-Object -First 1
        $targetDir = Join-Path $ScriptDir "jdk-21"
        if (Test-Path $targetDir) { Remove-Item $targetDir -Recurse -Force }

        if ($innerDir) {
            Move-Item -Path $innerDir.FullName -Destination $targetDir -Force
        } else {
            Move-Item -Path $tempExtract -Destination $targetDir -Force
        }

        # 清理暫存
        if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force }
        if (Test-Path (Join-Path $ScriptDir $zipName)) { Remove-Item (Join-Path $ScriptDir $zipName) -Force }

        Write-Host "  [+] 綠色免安裝版 JDK 21 配置完成！" -ForegroundColor Green
        return (Join-Path $targetDir "bin\java.exe")
    } else {
        if (-not (Test-IsAdmin)) {
            Write-Host "`n  [!] 注意：安裝到系統需要系統管理員權限，請確認目前 PowerShell 是否有管理員權限。" -ForegroundColor Yellow
        }
        Write-Host "`n  -> 正在下載 Oracle JDK 21 安裝檔..." -ForegroundColor Cyan
        $exeName = "jdk-21.exe"
        $downloadUrl = "https://download.oracle.com/java/21/archive/jdk-21_windows-x64_bin.exe"
        $ok = Download-File $downloadUrl $exeName (100 * 1024 * 1024)

        if (-not $ok) {
            Write-Host "  [!] Oracle JDK 下載失敗！" -ForegroundColor Red
            return $null
        }

        Write-Host "  -> 正在靜默安裝 JDK-21 至系統..." -ForegroundColor Cyan
        Start-Process -FilePath (Join-Path $ScriptDir $exeName) -ArgumentList "/s" -Wait
        Remove-Item (Join-Path $ScriptDir $exeName) -Force

        $found = Find-JDK21Path
        if ($found) {
            Write-Host "  [+] 系統 JDK 21 安裝完成！" -ForegroundColor Green
            return $found
        } else {
            Write-Host "  [!] 安裝完成後仍未偵測到 JDK，預設指定路徑。" -ForegroundColor Yellow
            return "C:\Program Files\Java\jdk-21\bin\java.exe"
        }
    }
}

# ----------------------------------------------------
# 尋找與檢查現有 Burp Suite Pro JAR 檔
# ----------------------------------------------------
function Get-BurpJarFile {
    $jars = Get-ChildItem -Path $ScriptDir -Filter "burpsuite_pro*.jar" -File
    if ($jars -and $jars.Count -gt 0) {
        return $jars[0].Name
    }
    return $null
}

# ----------------------------------------------------
# 下載 Burp Suite Professional JAR
# ----------------------------------------------------
function Download-BurpJar {
    param ([string]$targetName = "burpsuite_pro_v2025.jar")
    Write-Host "`n  -> 正在從 PortSwigger 官網下載最新 Burp Suite Pro (約 650MB)..." -ForegroundColor Cyan
    $url = "https://portswigger.net/burp/releases/download?product=pro&type=Jar"
    $ok = Download-File $url $targetName (300 * 1024 * 1024)
    if ($ok) {
        Write-Host "  [+] Burp Suite Pro 主程式下載完成！" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  [!] 下載失敗，請檢查網路狀態。" -ForegroundColor Red
        return $false
    }
}

# ----------------------------------------------------
# 生成可攜式啟動腳本 (Burp.bat & Burp-Suite-Pro.vbs)
# ----------------------------------------------------
function Create-StartupScripts {
    param (
        [string]$javaExePath,
        [string]$burpJarName,
        [string]$maxMem = "4096m"
    )

    Write-Host "`n  -> 正在生成可攜式啟動腳本..." -ForegroundColor Cyan

    $vmOptions = "--enable-native-access=ALL-UNNAMED --add-opens=java.desktop/javax.swing=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm.Opcodes=ALL-UNNAMED"

    # 1. 生成 Burp.bat（使用 %~dp0 相對路徑，完全便攜）
    $batPath = Join-Path $ScriptDir "Burp.bat"
    $batContent = @"
@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: 優先檢測本地綠色版 JDK，否則使用系統安裝的 JDK 21
if exist "%~dp0jdk-21\bin\java.exe" (
    set "JAVA_EXE=%~dp0jdk-21\bin\java.exe"
) else (
    set "JAVA_EXE=$javaExePath"
)

:: 動態搜尋目錄下的 Burp 主程式 JAR
set "BURP_JAR="
for %%f in ("%~dp0burpsuite_pro*.jar") do (
    set "BURP_JAR=%%f"
)
if not defined BURP_JAR set "BURP_JAR=%~dp0$burpJarName"

:: JVM 記憶體與模組參數
set "JAVA_MEM=-Xms1024m -Xmx$maxMem -XX:+UseG1GC"
set "VM_OPTIONS=$vmOptions"

:: 啟動 Burp Suite Pro
start "" "!JAVA_EXE!" !JAVA_MEM! !VM_OPTIONS! -javaagent:"%~dp0loader.jar" -noverify -jar "!BURP_JAR!"
"@
    [System.IO.File]::WriteAllText($batPath, $batContent, [System.Text.Encoding]::UTF8)

    # 2. 生成 Burp-Suite-Pro.vbs（自動獲取當前腳本所在目錄，無黑框背景執行）
    $vbsPath = Join-Path $ScriptDir "Burp-Suite-Pro.vbs"
    $vbsContent = @"
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = currentDir
WshShell.Run Chr(34) & currentDir & "\Burp.bat" & Chr(34), 0, False
Set WshShell = Nothing
Set fso = Nothing
"@
    [System.IO.File]::WriteAllText($vbsPath, $vbsContent, [System.Text.Encoding]::UTF8)

    Write-Host "  [+] 成功生成 Burp.bat 與 Burp-Suite-Pro.vbs (支援任意路徑搬移)" -ForegroundColor Green
}

# ----------------------------------------------------
# 建立桌面捷徑 (綁定 installer.ico)
# ----------------------------------------------------
function Create-DesktopShortcut {
    $desktopPath = [Environment]::GetFolderPath('Desktop')
    $shortcutPath = Join-Path $desktopPath "Burp Suite Pro.lnk"
    $vbsPath = Join-Path $ScriptDir "Burp-Suite-Pro.vbs"
    $icoPath = Join-Path $ScriptDir "installer.ico"

    try {
        $wsh = New-Object -ComObject WScript.Shell
        $shortcut = $wsh.CreateShortcut($shortcutPath)
        # 使用 wscript.exe 執行 vbs，避免副檔名關聯被破壞
        $shortcut.TargetPath = "wscript.exe"
        $shortcut.Arguments = "`"$vbsPath`""
        $shortcut.WorkingDirectory = $ScriptDir
        $shortcut.Description = "Burp Suite Professional (Portable Launcher)"

        if (Test-Path $icoPath) {
            $shortcut.IconLocation = $icoPath
        }
        $shortcut.Save()
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($shortcut) | Out-Null
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wsh) | Out-Null

        Write-Host "  [+] 已在桌面建立捷徑：$shortcutPath" -ForegroundColor Green
    } catch {
        Write-Host "  [!] 建立桌面捷徑時發生錯誤：$_" -ForegroundColor Red
    }
}

# ----------------------------------------------------
# 清理暫存檔案
# ----------------------------------------------------
function Clean-TempFiles {
    Write-Host "`n  -> 正在搜尋並清理暫存檔..." -ForegroundColor Cyan
    $patterns = @("*.aria2", "jdk-*.exe", "jdk-*.zip", "*.tmp")
    $count = 0
    foreach ($pat in $patterns) {
        $files = Get-ChildItem -Path $ScriptDir -Filter $pat -File -ErrorAction SilentlyContinue
        foreach ($f in $files) {
            Remove-Item $f.FullName -Force -ErrorAction SilentlyContinue
            Write-Host "     已刪除: $($f.Name)" -ForegroundColor DarkGray
            $count++
        }
    }
    if ($count -eq 0) {
        Write-Host "  [+] 無任何暫存檔案需清理。" -ForegroundColor Green
    } else {
        Write-Host "  [+] 清理完成，共刪除 $count 個檔案！" -ForegroundColor Green
    }
}

# ----------------------------------------------------
# 一鍵完整安裝 / 環境修復主流程
# ----------------------------------------------------
function Run-FullSetup {
    Write-Host "`n[1/5] 檢查 JDK 21 環境..." -ForegroundColor Yellow
    $jdkExe = Find-JDK21Path
    if (-not $jdkExe) {
        $jdkExe = Install-JDK21Dialog
        if (-not $jdkExe) {
            Write-Host "  [!] 缺少 JDK 21，無法繼續後續配置。" -ForegroundColor Red
            return
        }
    } else {
        Write-Host "  [+] 偵測到現有 JDK-21: $jdkExe" -ForegroundColor Green
    }

    Write-Host "`n[2/5] 檢查 Burp Suite Pro 主程式..." -ForegroundColor Yellow
    $burpJar = Get-BurpJarFile
    if (-not $burpJar) {
        $burpJar = "burpsuite_pro_v2025.jar"
        $ok = Download-BurpJar $burpJar
        if (-not $ok) { return }
    } else {
        $sizeMB = [math]::Round(((Get-Item (Join-Path $ScriptDir $burpJar)).Length / 1MB), 2)
        Write-Host "  [+] 找到現有 Burp 主程式: $burpJar ($sizeMB MB)" -ForegroundColor Green
    }

    Write-Host "`n[3/5] 檢查 loader.jar 授權載入器..." -ForegroundColor Yellow
    if (-not (Test-Path (Join-Path $ScriptDir "loader.jar"))) {
        Write-Host "  [!] 錯誤：未在目錄中找到 loader.jar！" -ForegroundColor Red
        Write-Host "      請確保 loader.jar 位於此腳本同目錄下。" -ForegroundColor Red
        return
    } else {
        Write-Host "  [+] 找到 loader.jar。" -ForegroundColor Green
    }

    Write-Host "`n[4/5] 產生啟動腳本與桌面捷徑..." -ForegroundColor Yellow
    Create-StartupScripts -javaExePath $jdkExe -burpJarName $burpJar -maxMem "4096m"
    Create-DesktopShortcut

    Write-Host "`n[5/5] 啟動程序..." -ForegroundColor Yellow
    Write-Host "  -> 啟動 Keygenerator (註冊機)..." -ForegroundColor Cyan
    Start-Process -FilePath $jdkExe -WorkingDirectory $ScriptDir -ArgumentList "-jar `"$ScriptDir\loader.jar`""

    Write-Host "  -> 啟動 Burp Suite Professional..." -ForegroundColor Cyan
    $vmOptions = "--enable-native-access=ALL-UNNAMED --add-opens=java.desktop/javax.swing=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm.Opcodes=ALL-UNNAMED"
    Start-Process -FilePath $jdkExe -WorkingDirectory $ScriptDir -ArgumentList "-Xms1024m -Xmx4096m -XX:+UseG1GC $vmOptions -javaagent:`"$ScriptDir\loader.jar`" -noverify -jar `"$ScriptDir\$burpJar`""

    Write-Host "`n========================================================" -ForegroundColor Green
    Write-Host "   安裝與配置完成！註冊步驟說明：" -ForegroundColor Green
    Write-Host "   1. 複製 Loader 視窗中的 'License' 字串貼到 Burp 視窗" -ForegroundColor White
    Write-Host "   2. 點擊 Next，選擇 'Manual activation'" -ForegroundColor White
    Write-Host "   3. 複製 Burp 的 'Activation Request' 貼回 Loader" -ForegroundColor White
    Write-Host "   4. 將 Loader 產生的 'Activation Response' 貼回 Burp 完成授權" -ForegroundColor White
    Write-Host "========================================================" -ForegroundColor Green
}

# ----------------------------------------------------
# 主選單介面
# ----------------------------------------------------
function Show-Menu {
    Clear-Host
    Write-Host "========================================================" -ForegroundColor Cyan
    Write-Host "      Burp Suite Pro 工具箱與維護精靈" -ForegroundColor Cyan
    Write-Host "========================================================" -ForegroundColor Cyan

    # 狀態面板
    $jdkStatus = Find-JDK21Path
    $burpStatus = Get-BurpJarFile
    $loaderStatus = Test-Path (Join-Path $ScriptDir "loader.jar")
    $shortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) "Burp Suite Pro.lnk"
    $shortcutStatus = Test-Path $shortcutPath

    Write-Host "【當前環境狀態】" -ForegroundColor White
    if ($jdkStatus) {
        Write-Host "  - JDK 21   : [已就緒] $jdkStatus" -ForegroundColor Green
    } else {
        Write-Host "  - JDK 21   : [未安裝] 系統或目錄無 JDK 21" -ForegroundColor Red
    }

    if ($burpStatus) {
        $mb = [math]::Round(((Get-Item (Join-Path $ScriptDir $burpStatus)).Length / 1MB), 1)
        Write-Host "  - Burp JAR : [已就緒] $burpStatus ($mb MB)" -ForegroundColor Green
    } else {
        Write-Host "  - Burp JAR : [未找到] 需要下載" -ForegroundColor Red
    }

    if ($loaderStatus) {
        Write-Host "  - Loader   : [已就緒] loader.jar" -ForegroundColor Green
    } else {
        Write-Host "  - Loader   : [缺失] loader.jar" -ForegroundColor Red
    }

    if ($shortcutStatus) {
        Write-Host "  - 桌面捷徑 : [已建立] 桌面已有捷徑" -ForegroundColor Green
    } else {
        Write-Host "  - 桌面捷徑 : [未建立]" -ForegroundColor Yellow
    }

    Write-Host "--------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "  [1] 一鍵完整安裝 / 環境修復 (推薦初次使用)" -ForegroundColor Cyan
    Write-Host "  [2] 僅更新 Burp Suite 主程式 (下載最新 PortSwigger JAR)" -ForegroundColor Yellow
    Write-Host "  [3] 自訂記憶體上限配置 (當前預設: 4GB)" -ForegroundColor White
    Write-Host "  [4] 重新建立桌面捷徑 (綁定圖示)" -ForegroundColor White
    Write-Host "  [5] 清理下載暫存檔 (.aria2 / 安裝包)" -ForegroundColor White
    Write-Host "  [6] 直接啟動 Burp Suite Pro (免黑框)" -ForegroundColor Green
    Write-Host "  [0] 離開" -ForegroundColor Gray
    Write-Host "========================================================" -ForegroundColor Cyan

    $opt = Read-Host "請輸入選項號碼 [1-6, 0]"
    switch ($opt) {
        "1" { Run-FullSetup }
        "2" {
            $newName = Read-Host "請輸入儲存檔名 (直接按 Enter 預設覆蓋更新現有)"
            if ([string]::IsNullOrWhiteSpace($newName)) {
                $cur = Get-BurpJarFile
                $newName = if ($cur) { $cur } else { "burpsuite_pro_latest.jar" }
            }
            Download-BurpJar $newName
            $jdkExe = Find-JDK21Path
            if ($jdkExe) { Create-StartupScripts -javaExePath $jdkExe -burpJarName $newName }
        }
        "3" {
            $mem = Read-Host "請輸入最大記憶體 (例如 4096m, 8192m, 8g, 16g)"
            if (-not [string]::IsNullOrWhiteSpace($mem)) {
                if ($mem -notmatch "(?i)[mg]$") { $mem = "${mem}m" }
                $jdkExe = Find-JDK21Path
                $jar = Get-BurpJarFile
                if (-not $jdkExe) { $jdkExe = "C:\Program Files\Java\jdk-21\bin\java.exe" }
                if (-not $jar) { $jar = "burpsuite_pro_v2025.jar" }
                Create-StartupScripts -javaExePath $jdkExe -burpJarName $jar -maxMem $mem
                Write-Host "  [+] 記憶體上限已更新為 $mem！" -ForegroundColor Green
            }
        }
        "4" { Create-DesktopShortcut }
        "5" { Clean-TempFiles }
        "6" {
            $vbs = Join-Path $ScriptDir "Burp-Suite-Pro.vbs"
            if (Test-Path $vbs) {
                Start-Process "wscript.exe" -ArgumentList "`"$vbs`""
                Write-Host "  [+] 已在背景啟動 Burp Suite Pro！" -ForegroundColor Green
            } else {
                Write-Host "  [!] 未找到 Burp-Suite-Pro.vbs，請先執行 [1] 進行配置。" -ForegroundColor Red
            }
        }
        "0" { return }
        default {
            Write-Host "無效選項，請重新輸入。" -ForegroundColor Red
        }
    }
}

# 進入選單
Show-Menu
