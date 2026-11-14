<#
.SYNOPSIS
    ThreatHunter-Triage.ps1 - Windows 本機端點快速應急鑑識工具
.DESCRIPTION
    無需安裝任何第三方套件或依賴，原生支援 Windows 10 / 11 / Server 2016+。
    專門鑑識全網卡開放通訊埠、對外公網連線、高資源佔用進程與可疑路徑。
#>

[CmdletBinding()]
param(
    [string]$OutputDir = (Get-Location).Path,
    [switch]$NoHtml
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'SilentlyContinue'

$ReportTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$FileTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$HostName = $env:COMPUTERNAME
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$IsAdmin = ([System.Security.Principal.WindowsPrincipal][System.Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " [ThreatHunter-Triage] Windows 本機端點快速應急鑑識工具 " -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "主機名稱: $HostName | 執行身分: $CurrentUser $(if($IsAdmin){'[系統管理員]'}else{'[非管理員-部分核心資訊可能受限]'})"
Write-Host "執行時間: $ReportTime`n"

# 1. 建立進程雜湊表 (快取二進位檔案資訊)
Write-Host "[1/4] 收集全系統進程與二進位檔案資訊..." -ForegroundColor Cyan
$ProcessMap = @{}
$WmiProcesses = Get-CimInstance Win32_Process
foreach ($proc in $WmiProcesses) {
    $verInfo = $null
    if ($proc.ExecutablePath -and (Test-Path $proc.ExecutablePath)) {
        try { $verInfo = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($proc.ExecutablePath) } catch {}
    }
    $ProcessMap[[int]$proc.ProcessId] = [PSCustomObject]@{
        Id             = $proc.ProcessId
        Name           = $proc.Name
        Path           = $proc.ExecutablePath
        CommandLine    = $proc.CommandLine
        ParentPID      = $proc.ParentProcessId
        Company        = if ($verInfo) { $verInfo.CompanyName } else { "" }
        Description    = if ($verInfo) { $verInfo.FileDescription } else { "" }
    }
}

# 2. 全網卡監聽鑑識 (0.0.0.0 / ::)
Write-Host "[2/4] 鑑識全網卡監聽埠 (0.0.0.0 / ::) 與危險暴露協定..." -ForegroundColor Cyan
$WellKnownRisks = @{
    21   = @{ Service = "FTP"; Risk = "高"; Note = "明文傳輸協議，易被探測嗅探" }
    22   = @{ Service = "SSH"; Risk = "中"; Note = "遠端安全通道，需留意爆破" }
    23   = @{ Service = "Telnet"; Risk = "極高"; Note = "高危明文遠端協定" }
    80   = @{ Service = "HTTP"; Risk = "中"; Note = "Web 服務" }
    445  = @{ Service = "SMB"; Risk = "高"; Note = "微軟檔案共用，內網勒索病毒主力擴散埠" }
    1433 = @{ Service = "MSSQL"; Risk = "高"; Note = "SQL Server 暴露，易遭密碼撞庫" }
    3306 = @{ Service = "MySQL"; Risk = "高"; Note = "MySQL 資料庫暴露，應改綁 127.0.0.1" }
    3389 = @{ Service = "RDP"; Risk = "極高"; Note = "微軟遠端桌面，全球勒索軟體爆破主力目標" }
    5432 = @{ Service = "PostgreSQL"; Risk = "中"; Note = "資料庫服務" }
    5900 = @{ Service = "VNC"; Risk = "高"; Note = "VNC 遠端桌面協定" }
    9444 = @{ Service = "KDService/Web"; Risk = "中"; Note = "設備通知/Web Service 監聽" }
}

$AllTcp = Get-NetTCPConnection
$ListeningExposed = @()

foreach ($conn in ($AllTcp | Where-Object { $_.State -eq 'Listen' })) {
    if ($conn.LocalAddress -in @('127.0.0.1', '::1')) {
        continue
    }

    $pInfo = $ProcessMap[[int]$conn.OwningProcess]
    $pName = if ($pInfo) { $pInfo.Name } else { "Unknown" }
    $pPath = if ($pInfo) { $pInfo.Path } else { "N/A" }
    $pComp = if ($pInfo) { $pInfo.Company } else { "" }
    $pDesc = if ($pInfo) { $pInfo.Description } else { "" }

    $riskLevel = "低"
    $riskNote = "第三方/自訂服務開放"
    $serviceTag = "自訂服務"

    if ($WellKnownRisks.ContainsKey([int]$conn.LocalPort)) {
        $riskLevel = $WellKnownRisks[[int]$conn.LocalPort].Risk
        $serviceTag = $WellKnownRisks[[int]$conn.LocalPort].Service
        $riskNote = $WellKnownRisks[[int]$conn.LocalPort].Note
    } elseif ($pName -eq "svchost.exe") {
        $riskLevel = "中"
        $riskNote = "Windows 系統服務開放埠"
    }

    $ListeningExposed += [PSCustomObject]@{
        Port         = $conn.LocalPort
        Address      = $conn.LocalAddress
        Protocol     = "TCP"
        PID          = $conn.OwningProcess
        ProcessName  = $pName
        Company      = $pComp
        Description  = $pDesc
        ServiceTag   = $serviceTag
        Risk         = $riskLevel
        Note         = $riskNote
        Path         = $pPath
    }
}

# 3. 活躍對外公網連線 (Established WAN)
Write-Host "[3/4] 鑑識對外活躍公網連線 (Established WAN)..." -ForegroundColor Cyan
$WanConnections = @()

foreach ($conn in ($AllTcp | Where-Object { $_.State -eq 'Established' })) {
    $remoteIp = $conn.RemoteAddress
    if ($remoteIp -in @('127.0.0.1', '::1', '0.0.0.0', '::') -or $remoteIp -like '127.*') {
        continue
    }

    $isPrivate = ($remoteIp -like '10.*') -or ($remoteIp -like '192.168.*') -or ($remoteIp -match '^172\.(1[6-9]|2[0-9]|3[0-1])\.') -or ($remoteIp -like 'fe80:*')
    if (-not $isPrivate) {
        $pInfo = $ProcessMap[[int]$conn.OwningProcess]
        $WanConnections += [PSCustomObject]@{
            LocalIP      = "$($conn.LocalAddress):$($conn.LocalPort)"
            RemoteIP     = "$($conn.RemoteAddress):$($conn.RemotePort)"
            PID          = $conn.OwningProcess
            ProcessName  = if ($pInfo) { $pInfo.Name } else { "Unknown" }
            Company      = if ($pInfo) { $pInfo.Company } else { "" }
            Path         = if ($pInfo) { $pInfo.Path } else { "N/A" }
        }
    }
}

# 4. 資源鑑識：高 CPU 瞬時率與累計耗時排查
Write-Host "[4/5] 採樣計算 CPU 瞬時使用率與累計資源佔用..." -ForegroundColor Cyan

# 採樣 1.5 秒計算目前活動中佔用 CPU 的進程
$sample1 = Get-Process | Select-Object Id, ProcessName, CPU, WorkingSet64
Start-Sleep -Milliseconds 1500
$sample2 = Get-Process | Select-Object Id, ProcessName, CPU, WorkingSet64

$procDiff = foreach ($p2 in $sample2) {
    $p1 = $sample1 | Where-Object { $_.Id -eq $p2.Id }
    if ($p1 -and $p2.CPU -and $p1.CPU) {
        $delta = ($p2.CPU - $p1.CPU) / 1.5 * 100 / [Environment]::ProcessorCount
        if ($delta -gt 1.0) {
            $pInfo = $ProcessMap[[int]$p2.Id]
            [PSCustomObject]@{
                PID            = $p2.Id
                ProcessName    = $p2.ProcessName
                InstantCpuPct  = [math]::Round($delta, 1)
                TotalCpuSec    = [math]::Round($p2.CPU, 1)
                MemoryMB       = [math]::Round($p2.WorkingSet64 / 1MB, 1)
                Path           = if ($pInfo) { $pInfo.Path } else { "N/A" }
            }
        }
    }
}

# 歷史累計 CPU 消耗最高 Top 10
$TopCumulativeCpu = Get-Process | Where-Object { $_.CPU } | Sort-Object CPU -Descending | Select-Object -First 10 | ForEach-Object {
    $pInfo = $ProcessMap[[int]$_.Id]
    [PSCustomObject]@{
        PID         = $_.Id
        ProcessName = $_.ProcessName
        TotalCpuSec = [math]::Round($_.CPU, 1)
        MemoryMB    = [math]::Round($_.WorkingSet64 / 1MB, 1)
        Path        = if ($pInfo) { $pInfo.Path } else { "N/A" }
    }
}

Write-Host "`n[!] 全網卡開放之監聽埠 (0.0.0.0 Listening, 共 $($ListeningExposed.Count) 個):" -ForegroundColor Yellow
if ($ListeningExposed) {
    $ListeningExposed | Sort-Object Risk -Descending | Format-Table Port, Address, ProcessName, ServiceTag, Risk, Note -AutoSize
}

# 5. 進程鑑識：可疑目錄執行、系統二進位檔偽裝與遠端軟體偵測
Write-Host "[5/5] 鑑識可疑路徑、進程偽裝與遠端控制工具 (RAT)..." -ForegroundColor Cyan

$RemoteToolKeywords = @('gameviewer', 'anydesk', 'teamviewer', 'todesk', 'rustdesk', 'sunlogin', 'tailscale', 'zerotier', 'frpc', 'ngrok', 'softether', 'vpnclient', 'cloudflare warp')
$SuspiciousPathPatterns = @('AppData\\Local\\Temp', 'Windows\\Temp', 'Users\\Public', 'ProgramData\\[^\\]+\.exe$')

$DetectedRemoteTools = @()
$DetectedPathAnomalies = @()

foreach ($kv in $ProcessMap.Values) {
    if (-not $kv.Path) { continue }
    $pPath = $kv.Path
    $pName = $kv.Name

    # 檢查是否為遠端控制 / 穿透工具
    foreach ($kw in $RemoteToolKeywords) {
        if ($pName -like "*$kw*" -or $pPath -like "*$kw*") {
            $DetectedRemoteTools += [PSCustomObject]@{
                PID         = $kv.Id
                ProcessName = $pName
                MatchedRule = $kw
                Path        = $pPath
                Company     = $kv.Company
            }
            break
        }
    }

    # 檢查是否在可疑臨時或共用目錄執行
    foreach ($pattern in $SuspiciousPathPatterns) {
        if ($pPath -match $pattern) {
            $DetectedPathAnomalies += [PSCustomObject]@{
                PID         = $kv.Id
                ProcessName = $pName
                AnomalyType = "可疑執行路徑"
                Detail      = "符合高危目錄特徵: $pattern"
                Path        = $pPath
            }
            break
        }
    }

    # 檢查微軟核心系統二進位檔偽裝（Masquerading）
    if ($pName -in @('svchost.exe', 'csrss.exe', 'smss.exe', 'lsass.exe', 'services.exe', 'winlogon.exe')) {
        if ($pPath -notmatch '(?i)^C:\\Windows\\System32\\') {
            $DetectedPathAnomalies += [PSCustomObject]@{
                PID         = $kv.Id
                ProcessName = $pName
                AnomalyType = "系統二進位檔偽裝"
                Detail      = "核心系統進程未位於 System32 目錄下"
                Path        = $pPath
            }
        }
    } elseif ($pName -eq 'explorer.exe' -and $pPath -notmatch '(?i)^C:\\Windows\\explorer\.exe$') {
        $DetectedPathAnomalies += [PSCustomObject]@{
            PID         = $kv.Id
            ProcessName = $pName
            AnomalyType = "系統二進位檔偽裝"
            Detail      = "explorer.exe 未位於 Windows 根目錄"
            Path        = $pPath
        }
    }
}

Write-Host "`n[!] 偵測到的遠端控制 / 穿透工具 (共 $($DetectedRemoteTools.Count) 個):" -ForegroundColor Yellow
if ($DetectedRemoteTools) {
    $DetectedRemoteTools | Format-Table PID, ProcessName, MatchedRule, Company, Path -AutoSize
} else {
    Write-Host "  未偵測到常見的商業遠端控制或穿透工具。" -ForegroundColor Gray
}

Write-Host "`n[!] 可疑目錄執行與進程偽裝異常 (共 $($DetectedPathAnomalies.Count) 個):" -ForegroundColor Yellow
if ($DetectedPathAnomalies) {
    $DetectedPathAnomalies | Format-Table PID, ProcessName, AnomalyType, Detail, Path -AutoSize
} else {
    Write-Host "  未發現可疑目錄執行或系統進程偽裝行為。" -ForegroundColor Gray
}

Write-Host "`n[!] 當前累計 CPU 佔用最高 Top 5 進程:" -ForegroundColor Yellow
$TopCumulativeCpu | Select-Object -First 5 | Format-Table PID, ProcessName, TotalCpuSec, MemoryMB, Path -AutoSize

# -------------------------------------------------------------
# 產生專業獨立 HTML 報告
# -------------------------------------------------------------
if (-not $NoHtml) {
    $HtmlPath = Join-Path $OutputDir "Forensic_Report_${HostName}_${FileTimestamp}.html"

    $listeningHtmlRows = ($ListeningExposed | Sort-Object Risk -Descending | ForEach-Object {
        $badgeClass = switch ($_.Risk) {
            "極高" { "badge-critical" }
            "高"   { "badge-high" }
            "中"   { "badge-medium" }
            default { "badge-low" }
        }
        "<tr><td><strong>$($_.Port)</strong></td><td>$($_.Address)</td><td>$($_.ProcessName) (PID: $($_.PID))</td><td>$($_.ServiceTag)</td><td><span class='$badgeClass'>$($_.Risk)</span></td><td>$($_.Note)</td><td class='code-path'>$($_.Path)</td></tr>"
    }) -join "`n"

    $remoteHtmlRows = ($DetectedRemoteTools | ForEach-Object {
        "<tr><td>$($_.ProcessName)</td><td>$($_.PID)</td><td><strong>$($_.MatchedRule)</strong></td><td>$($_.Company)</td><td class='code-path'>$($_.Path)</td></tr>"
    }) -join "`n"

    $anomalyHtmlRows = ($DetectedPathAnomalies | ForEach-Object {
        "<tr><td><span class='badge-critical'>$($_.AnomalyType)</span></td><td>$($_.ProcessName) (PID: $($_.PID))</td><td>$($_.Detail)</td><td class='code-path'>$($_.Path)</td></tr>"
    }) -join "`n"

    $topCpuHtmlRows = ($TopCumulativeCpu | ForEach-Object {
        "<tr><td>$($_.PID)</td><td><strong>$($_.ProcessName)</strong></td><td>$($_.TotalCpuSec) s</td><td>$($_.MemoryMB) MB</td><td class='code-path'>$($_.Path)</td></tr>"
    }) -join "`n"

    $wanConnHtmlRows = ($WanConnections | Select-Object -First 30 | ForEach-Object {
        "<tr><td>$($_.LocalIP)</td><td><strong>$($_.RemoteIP)</strong></td><td>$($_.ProcessName) (PID: $($_.PID))</td><td class='code-path'>$($_.Path)</td></tr>"
    }) -join "`n"

    $HtmlContent = @"
<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>端點應急鑑識分析報告 - $HostName</title>
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f8f9fa; color: #333; margin: 0; padding: 25px; }
    .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
    h1 { color: #1a202c; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-top: 0; }
    h2 { color: #2d3748; margin-top: 30px; border-left: 4px solid #3182ce; padding-left: 10px; font-size: 1.25rem; }
    .meta-box { background: #edf2f7; padding: 15px; border-radius: 6px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 20px; font-size: 0.95rem; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9rem; }
    th, td { border: 1px solid #e2e8f0; padding: 10px 12px; text-align: left; }
    th { background: #f7fafc; color: #4a5568; font-weight: 600; }
    tr:nth-child(even) { background-color: #fcfdfd; }
    tr:hover { background-color: #f1f5f9; }
    .code-path { font-family: Consolas, Monaco, monospace; font-size: 0.82rem; color: #4a5568; word-break: break-all; }
    .badge-critical { background: #e53e3e; color: #fff; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
    .badge-high { background: #dd6b20; color: #fff; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
    .badge-medium { background: #d69e2e; color: #fff; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
    .badge-low { background: #38a169; color: #fff; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
    .empty-note { color: #718096; font-style: italic; padding: 10px 0; }
</style>
</head>
<body>
<div class="container">
    <h1>端點應急鑑識分析報告 (Endpoint Forensic Triage)</h1>
    <div class="meta-box">
        <div><strong>主機名稱：</strong>$HostName</div>
        <div><strong>報告時間：</strong>$ReportTime</div>
        <div><strong>檢測身分：</strong>$CurrentUser $(if($IsAdmin){'<span class="badge-low">Admin</span>'}else{'<span class="badge-medium">Non-Admin</span>'})</div>
    </div>

    <h2>1. 全網卡開放之監聽埠 (0.0.0.0 Listening)</h2>
    $(if ($ListeningExposed.Count -gt 0) {
        "<table><thead><tr><th>埠號</th><th>綁定地址</th><th>進程與 PID</th><th>服務推測</th><th>風險</th><th>說明</th><th>程式路徑</th></tr></thead><tbody>$listeningHtmlRows</tbody></table>"
    } else {
        "<div class='empty-note'>✔ 未發現高危全網卡開放監聽埠。</div>"
    })

    <h2>2. 遠端桌面 / 穿透工具 / RAT 偵測</h2>
    $(if ($DetectedRemoteTools.Count -gt 0) {
        "<table><thead><tr><th>進程名稱</th><th>PID</th><th>命中特徵</th><th>開發公司</th><th>路徑</th></tr></thead><tbody>$remoteHtmlRows</tbody></table>"
    } else {
        "<div class='empty-note'>✔ 未發現常見第三方遠端控制或內網穿透軟體。</div>"
    })

    <h2>3. 異常執行路徑與進程偽裝檢查</h2>
    $(if ($DetectedPathAnomalies.Count -gt 0) {
        "<table><thead><tr><th>異常類別</th><th>進程名稱</th><th>特徵細節</th><th>實體路徑</th></tr></thead><tbody>$anomalyHtmlRows</tbody></table>"
    } else {
        "<div class='empty-note'>✔ 未檢測到可疑臨時路徑執行或微軟系統進程名稱偽裝。</div>"
    })

    <h2>4. 累計 CPU 時間消耗前 10 大進程</h2>
    <table><thead><tr><th>PID</th><th>進程名稱</th><th>累計 CPU 時間</th><th>記憶體佔用</th><th>程式路徑</th></tr></thead><tbody>$topCpuHtmlRows</tbody></table>

    <h2>5. 活躍對外公網連線 (前 30 筆)</h2>
    $(if ($WanConnections.Count -gt 0) {
        "<table><thead><tr><th>本地端點</th><th>遠端公網 IP 與埠</th><th>進程名稱</th><th>程式路徑</th></tr></thead><tbody>$wanConnHtmlRows</tbody></table>"
    } else {
        "<div class='empty-note'>當前無活躍之外部公網連線。</div>"
    })
</div>
</body>
</html>
"@

    $HtmlContent | Out-File -FilePath $HtmlPath -Encoding utf8
    Write-Host "`n[+] HTML 鑑識報告已產生：" -ForegroundColor Green
    Write-Host "    $HtmlPath" -ForegroundColor White
}

Write-Host "`n鑑識掃描完成！" -ForegroundColor Cyan


