# 設置輸出編碼
$OutputEncoding = [System.Text.Encoding]::UTF8

# 1. 下載函式：支援 aria2c 斷點續傳 / curl 續傳與檔案大小驗證
function Download-File ($url, $output, [long]$minBytes = 0) {
    if (Test-Path ".\aria2c.exe") {
        Write-Host "  [Speed] Use local aria2c (16 threads with resume)..." -ForegroundColor DarkCyan
        .\aria2c.exe -c -x 16 -s 16 -k 1M --allow-overwrite=true -o $output $url
    } elseif (Get-Command "curl.exe" -ErrorAction SilentlyContinue) {
        Write-Host "  [Standard] Use Windows curl.exe (with resume)..." -ForegroundColor DarkYellow
        curl.exe -# -L -C - -A "Mozilla/5.0" -o $output $url
    } else {
        $ProgressPreference = 'Continue'
        Invoke-WebRequest -Uri $url -OutFile $output
    }

    if (Test-Path $output) {
        $fileSize = (Get-Item $output).Length
        if ($minBytes -gt 0 -and $fileSize -lt $minBytes) {
            Write-Host "  [!] Error: Downloaded file size abnormally small ($([math]::Round($fileSize/1MB, 2)) MB < $([math]::Round($minBytes/1MB, 2)) MB)!" -ForegroundColor Red
            return $false
        }
        return $true
    }
    return $false
}

# 2. 動態搜尋系統中 JDK 21 執行檔路徑 (優先本機綠色版，次選系統路徑)
function Find-JDK21Path {
    $portableExe = Join-Path (Get-Location) "jdk-21\bin\java.exe"
    if (Test-Path $portableExe) { return $portableExe }

    $defaultPaths = @(
        "C:\Program Files\Java\jdk-21\bin\java.exe",
        "C:\Program Files (x86)\Java\jdk-21\bin\java.exe"
    )
    foreach ($path in $defaultPaths) {
        if (Test-Path $path) { return $path }
    }

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

    if ($env:JAVA_HOME) {
        $exe = Join-Path $env:JAVA_HOME "bin\java.exe"
        if (Test-Path $exe) {
            $verOutput = & $exe -version 2>&1
            if ($verOutput -match '"21\.') { return $exe }
        }
    }

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

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Burp Suite Pro Auto Installer" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

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
        if (-not $ok) { return $null }

        Write-Host "  -> 下載完成！正在解壓縮至本地目錄..." -ForegroundColor Cyan
        $tempExtract = ".\jdk-temp-extract"
        if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force }
        Expand-Archive -Path $zipName -DestinationPath $tempExtract -Force

        $innerDir = Get-ChildItem -Path $tempExtract -Directory | Where-Object { Test-Path (Join-Path $_.FullName "bin\java.exe") } | Select-Object -First 1
        $targetDir = ".\jdk-21"
        if (Test-Path $targetDir) { Remove-Item $targetDir -Recurse -Force }

        if ($innerDir) {
            Move-Item -Path $innerDir.FullName -Destination $targetDir -Force
        } else {
            Move-Item -Path $tempExtract -Destination $targetDir -Force
        }

        if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force }
        if (Test-Path $zipName) { Remove-Item $zipName -Force }

        Write-Host "  [+] 綠色免安裝版 JDK 21 配置完成！" -ForegroundColor Green
        return (Join-Path $targetDir "bin\java.exe")
    } else {
        Write-Host "`n  -> 正在下載 Oracle JDK 21 安裝檔..." -ForegroundColor Cyan
        $exeName = "jdk-21.exe"
        $downloadUrl = "https://download.oracle.com/java/21/archive/jdk-21_windows-x64_bin.exe"
        $ok = Download-File $downloadUrl $exeName (100 * 1024 * 1024)
        if (-not $ok) { return $null }

        Write-Host "  -> 正在靜默安裝 JDK-21 至系統..." -ForegroundColor Cyan
        Start-Process -FilePath $exeName -ArgumentList "/s" -Wait
        Remove-Item $exeName -Force

        $found = Find-JDK21Path
        if ($found) { return $found }
        return "C:\Program Files\Java\jdk-21\bin\java.exe"
    }
}

# ----------------------------------------------------
# 1. 搜尋系統現有 JDK-21 或從 Oracle/Adoptium 下載
# ----------------------------------------------------
Write-Host ""
Write-Host "[1/5] Searching for JDK-21..." -ForegroundColor Yellow
$jdk21Exe = Find-JDK21Path

if (-not $jdk21Exe) {
    $jdk21Exe = Install-JDK21Dialog
    if (-not $jdk21Exe) {
        Write-Host "  [!] JDK 安裝失敗，退出。" -ForegroundColor Red
        exit 1
    }
    Write-Host "  [+] JDK-21 配置完成！" -ForegroundColor Green
} else {
    Write-Host "  [+] Found existing JDK-21:" -ForegroundColor Green
    Write-Host "      $jdk21Exe" -ForegroundColor Cyan
}

# ----------------------------------------------------
# 2. 下載 Burp Suite Professional
# ----------------------------------------------------
$version = "2025"
$burpJar = "burpsuite_pro_v$version.jar"

Write-Host ""
Write-Host "[2/5] Checking Burp Suite Jar..." -ForegroundColor Yellow
if (!(Test-Path $burpJar)) {
    Write-Host "  -> Downloading Burp Suite Pro from PortSwigger..." -ForegroundColor Yellow
    $ok = Download-File "https://portswigger.net/burp/releases/download?product=pro&type=Jar" $burpJar (300 * 1024 * 1024)
    if ($ok) {
        Write-Host ""
        Write-Host "  [+] Burp Suite Pro downloaded!" -ForegroundColor Green
    } else {
        Write-Host "  [!] Download failed or invalid file size." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [+] Burp Suite Pro already exists." -ForegroundColor Green
}

# ----------------------------------------------------
# 3. 檢查本地 Loader
# ----------------------------------------------------
Write-Host ""
Write-Host "[3/5] Checking loader.jar..." -ForegroundColor Yellow

if (!(Test-Path "loader.jar")) {
    Write-Host "  [!] Error: loader.jar not found in current folder!" -ForegroundColor Red
    Write-Host "      Please place loader.jar in the same directory." -ForegroundColor Red
    exit
} else {
    Write-Host "  [+] Found loader.jar." -ForegroundColor Green
}

# ----------------------------------------------------
# 4. 清除舊配置與生成啟動檔 (Burp.bat / Burp-Suite-Pro.vbs)
# ----------------------------------------------------
Write-Host ""
Write-Host "[4/5] Creating startup scripts..." -ForegroundColor Yellow

if (Test-Path ".config.ini") { Remove-Item ".config.ini" -Force }

$vmOptions = "--enable-native-access=ALL-UNNAMED --add-opens=java.desktop/javax.swing=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm.Opcodes=ALL-UNNAMED"

if (Test-Path "Burp.bat") { Remove-Item "Burp.bat" -Force }
$batContent = "@echo off`r`n`"$jdk21Exe`" $vmOptions -javaagent:`"$pwd\loader.jar`" -noverify -jar `"$pwd\$burpJar`""
Set-Content -Path "Burp.bat" -Value $batContent -Encoding UTF8

if (Test-Path "Burp-Suite-Pro.vbs") { Remove-Item "Burp-Suite-Pro.vbs" -Force }
$vbsContent = "Set WshShell = CreateObject(`"WScript.Shell`")`r`nWshShell.Run chr(34) & `"$pwd\Burp.bat`" & Chr(34), 0`r`nSet WshShell = Nothing"
Set-Content -Path "Burp-Suite-Pro.vbs" -Value $vbsContent -Encoding UTF8
Write-Host "  [+] Created Burp.bat and Burp-Suite-Pro.vbs." -ForegroundColor Green

# ----------------------------------------------------
# 5. 啟動程序
# ----------------------------------------------------
Write-Host ""
Write-Host "[5/5] Launching applications..." -ForegroundColor Yellow
Write-Host "  -> Launching Keygenerator..." -ForegroundColor Cyan
Start-Process -FilePath $jdk21Exe -ArgumentList "-jar loader.jar"

Write-Host "  -> Launching Burp Suite Professional..." -ForegroundColor Cyan
Start-Process -FilePath $jdk21Exe -ArgumentList "$vmOptions -javaagent:`"$pwd\loader.jar`" -noverify -jar `"$pwd\$burpJar`""

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "   Installation & Launch Finished!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
