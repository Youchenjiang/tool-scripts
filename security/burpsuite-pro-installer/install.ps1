# 設置輸出編碼
$OutputEncoding = [System.Text.Encoding]::UTF8

# 1. 下載函式：優先使用本地打包的 aria2c，無則調用內建 curl
function Download-File ($url, $output) {
    if (Test-Path ".\aria2c.exe") {
        Write-Host "  [Speed] Use local aria2c (16 threads)..." -ForegroundColor DarkCyan
        .\aria2c.exe -x 16 -s 16 -k 1M -o $output $url
    } elseif (Get-Command "curl.exe" -ErrorAction SilentlyContinue) {
        Write-Host "  [Standard] Use Windows curl.exe..." -ForegroundColor DarkYellow
        curl.exe -# -L -A "Mozilla/5.0" -o $output $url
    } else {
        $ProgressPreference = 'Continue'
        Invoke-WebRequest -Uri $url -OutFile $output
    }
}

# 2. 動態搜尋系統中 JDK 21 執行檔路徑
function Find-JDK21Path {
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

# ----------------------------------------------------
# 1. 搜尋系統現有 JDK-21 或從 Oracle 官網下載
# ----------------------------------------------------
Write-Host ""
Write-Host "[1/5] Searching for JDK-21..." -ForegroundColor Yellow
$jdk21Exe = Find-JDK21Path

if (-not $jdk21Exe) {
    Write-Host "  -> JDK-21 not found. Downloading from Oracle..." -ForegroundColor Yellow
    Download-File "https://download.oracle.com/java/21/archive/jdk-21_windows-x64_bin.exe" "jdk-21.exe"

    Write-Host ""
    Write-Host "  -> Download complete! Installing JDK-21..." -ForegroundColor Yellow
    Start-Process -FilePath "jdk-21.exe" -ArgumentList "/s" -Wait
    Remove-Item "jdk-21.exe" -Force
    
    $jdk21Exe = Find-JDK21Path
    if (-not $jdk21Exe) {
        $jdk21Exe = "C:\Program Files\Java\jdk-21\bin\java.exe"
    }
    Write-Host "  [+] JDK-21 installation completed!" -ForegroundColor Green
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
    Download-File "https://portswigger.net/burp/releases/download?product=pro&type=Jar" $burpJar
    Write-Host ""
    Write-Host "  [+] Burp Suite Pro downloaded!" -ForegroundColor Green
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
