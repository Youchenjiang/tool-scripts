<#
.SYNOPSIS
    Get-HistoricalArtifacts.ps1 - Windows 事後歷史飛行紀錄鑑識工具
.DESCRIPTION
    無需即時抓取現場，事後倒查系統殘留之歷史數位跡證：
      1. DNS 快取與解析歷史 (已關閉連線之外聯網域名稱)
      2. Windows 事件日誌 (4624 遠端登入 IP、4625 暴力破解、7045 新服務安裝)
      3. Prefetch 預讀取執行歷史 (已自我刪除程式之執行軌跡)
      4. 排程任務持久化後門檢查 (Scheduled Tasks Persistence)
#>

[CmdletBinding()]
param(
    [int]$EventLookbackDays = 7,
    [int]$TopPrefetchCount = 30,
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
Write-Host " [Historical-Artifacts] Windows 事後歷史跡證鑑識工具 " -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "鑑識主機: $HostName | 鑑識身分: $CurrentUser $(if($IsAdmin){'[系統管理員]'}else{'[非管理員-建議提升權限]'})"
Write-Host "分析時間範圍: 過去 $EventLookbackDays 天的事件紀錄`n"

# -------------------------------------------------------------
# 1. DNS 客戶端快取解析 (已中斷之外聯網域名稱追蹤)
# -------------------------------------------------------------
Write-Host "[1/4] 提取 DNS Client 快取紀錄 (歷史解析網域)..." -ForegroundColor Cyan

$DnsRecords = @()
try {
    $rawDns = Get-DnsClientCache -ErrorAction Stop
    foreach ($entry in $rawDns) {
        if (-not $entry.Entry -or $entry.Entry -match '^(localhost|.*\.local|.*\.internal|.*\.arpa)$') {
            continue
        }
        $DnsRecords += [PSCustomObject]@{
            RecordName = $entry.Entry
            RecordType = switch ($entry.Type) {
                1 { "A" }
                5 { "CNAME" }
                28 { "AAAA" }
                default { "$($entry.Type)" }
            }
            Data       = if ($entry.Data) { ($entry.Data -join ", ") } else { "N/A" }
            TimeToLive = "$($entry.TimeToLive) s"
            Status     = switch ($entry.Status) {
                0 { "Success" }
                default { "$($entry.Status)" }
            }
        }
    }
} catch {
    Write-Host "[-] 無法讀取 DNS 快取: $($_.Exception.Message)" -ForegroundColor DarkGray
}

Write-Host "[+] 成功提取 $($DnsRecords.Count) 筆非本地 DNS 解析紀錄。" -ForegroundColor Green

# -------------------------------------------------------------
# 2. Windows 事件日誌鑑識 (登入來源 IP、暴力破解與新服務)
# -------------------------------------------------------------
Write-Host "`n[2/4] 檢索 Windows 事件日誌 (登入來源 IP 與新服務安裝)..." -ForegroundColor Cyan
$StartTime = (Get-Date).AddDays(-$EventLookbackDays)

$RdpLogons = @()
$FailedLogons = @()
$NewServices = @()

# 檢索 Security Log (需要 Administrator 權限)
if ($IsAdmin) {
    try {
        # Event 4624: 成功登入 (重點過濾 LogonType 10 遠端桌面與外部 IP)
        $logonEvents = Get-WinEvent -FilterHashtable @{
            LogName   = 'Security'
            Id        = 4624
            StartTime = $StartTime
        } -MaxEvents 300 -ErrorAction SilentlyContinue

        foreach ($evt in $logonEvents) {
            $xml = [xml]$evt.ToXml()
            $eventData = @{}
            foreach ($data in $xml.Event.EventData.Data) {
                $eventData[$data.Name] = $data.'#text'
            }

            $logonType = $eventData['LogonType']
            $srcIp = $eventData['IpAddress']
            $targetUser = $eventData['TargetUserName']

            # LogonType 10: RemoteInteractive (RDP), 3: Network
            if ($logonType -in @('10', '3') -and $srcIp -and $srcIp -ne '-' -and $srcIp -ne '127.0.0.1') {
                $RdpLogons += [PSCustomObject]@{
                    TimeGenerated = $evt.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
                    TargetUser    = $targetUser
                    LogonType     = if ($logonType -eq '10') { "RDP 遠端桌面 (10)" } else { "網路登入 (3)" }
                    SourceIP      = $srcIp
                    SourcePort    = $eventData['IpPort']
                    AuthPackage   = $eventData['AuthenticationPackageName']
                }
            }
        }

        # Event 4625: 登入失敗 (暴力破解紀錄)
        $failedEvents = Get-WinEvent -FilterHashtable @{
            LogName   = 'Security'
            Id        = 4625
            StartTime = $StartTime
        } -MaxEvents 200 -ErrorAction SilentlyContinue

        foreach ($evt in $failedEvents) {
            $xml = [xml]$evt.ToXml()
            $eventData = @{}
            foreach ($data in $xml.Event.EventData.Data) {
                $eventData[$data.Name] = $data.'#text'
            }
            $FailedLogons += [PSCustomObject]@{
                TimeGenerated = $evt.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
                TargetUser    = $eventData['TargetUserName']
                LogonType     = $eventData['LogonType']
                SourceIP      = $eventData['IpAddress']
                FailureReason = $eventData['Status']
            }
        }
    } catch {
        Write-Host "[-] 查詢安全性事件日誌時發生錯誤: $($_.Exception.Message)" -ForegroundColor DarkGray
    }
} else {
    Write-Host "[-] 目前為非管理員權限，無法讀取 Security 事件日誌（4624/4625）。" -ForegroundColor Yellow
}

# 檢索 System Log: Event 7045 (新安裝之服務)
try {
    $serviceEvents = Get-WinEvent -FilterHashtable @{
        LogName   = 'System'
        Id        = 7045
        StartTime = $StartTime
    } -MaxEvents 100 -ErrorAction SilentlyContinue

    foreach ($evt in $serviceEvents) {
        $xml = [xml]$evt.ToXml()
        $eventData = @{}
        foreach ($data in $xml.Event.EventData.Data) {
            $eventData[$data.Name] = $data.'#text'
        }
        $NewServices += [PSCustomObject]@{
            TimeGenerated = $evt.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
            ServiceName   = $eventData['ServiceName']
            ImagePath     = $eventData['ImagePath']
            ServiceType   = $eventData['ServiceType']
            AccountName   = $eventData['AccountName']
        }
    }
} catch {
    Write-Host "[-] 查詢系統服務安裝日誌時發生錯誤: $($_.Exception.Message)" -ForegroundColor DarkGray
}

Write-Host "[+] 發現 $($RdpLogons.Count) 筆外部登入、$(@($FailedLogons).Count) 筆失敗嘗試、$(@($NewServices).Count) 筆新服務註冊紀錄。" -ForegroundColor Green

# -------------------------------------------------------------
# 3. Prefetch 預讀取歷史 (已自我刪除程式之執行軌跡)
# -------------------------------------------------------------
Write-Host "`n[3/4] 提取 Prefetch 預讀取執行歷史 (追溯近期已結束或刪除之程式)..." -ForegroundColor Cyan
$PrefetchPath = "C:\Windows\Prefetch"
$RecentPrefetch = @()

if (Test-Path $PrefetchPath) {
    try {
        $pfFiles = Get-ChildItem -Path $PrefetchPath -Filter "*.pf" | Sort-Object LastWriteTime -Descending | Select-Object -First $TopPrefetchCount
        foreach ($pf in $pfFiles) {
            # 解析 Prefetch 檔名，格式通常為 EXE-HASH.pf
            $rawName = $pf.BaseName
            $exeName = ($rawName -split '-')[0] + ".exe"
            $hash = ($rawName -split '-')[1]

            $RecentPrefetch += [PSCustomObject]@{
                ExecutionTime = $pf.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
                EstimatedExe  = $exeName
                PrefetchFile  = $pf.Name
                SizeKB        = [math]::Round($pf.Length / 1KB, 1)
            }
        }
        Write-Host "[+] 成功提取最近 $($RecentPrefetch.Count) 筆 Prefetch 程式執行軌跡。" -ForegroundColor Green
    } catch {
        Write-Host "[-] 讀取 Prefetch 資料夾失敗 (可能需要 Administrator 權限): $($_.Exception.Message)" -ForegroundColor DarkGray
    }
} else {
    Write-Host "[-] 本機未啟用 Prefetch 或路徑不可存取。" -ForegroundColor DarkGray
}

# -------------------------------------------------------------
# 4. 排程任務持久化後門檢查 (Scheduled Tasks Persistence)
# -------------------------------------------------------------
Write-Host "`n[4/4] 檢查排程任務持久化機制 (Persistence Tasks)..." -ForegroundColor Cyan
$SuspiciousTasks = @()

try {
    $allTasks = Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' }
    foreach ($t in $allTasks) {
        $actionStr = ($t.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)" }) -join " ; "
        # 標註位於使用者目錄、Temp、或執行 powershell/cmd 混淆指令的排程
        if ($actionStr -match '(?i)(AppData|Temp|Users\\Public|powershell.*-enc|wscript|cscript)') {
            $SuspiciousTasks += [PSCustomObject]@{
                TaskName    = $t.TaskName
                TaskPath    = $t.TaskPath
                State       = "$($t.State)"
                Action      = $actionStr
            }
        }
    }
    Write-Host "[+] 排程任務分析完成，偵測到 $(@($SuspiciousTasks).Count) 個具備高風險路徑/行為的排程。" -ForegroundColor Green
} catch {
    Write-Host "[-] 查詢排程任務失敗: $($_.Exception.Message)" -ForegroundColor DarkGray
}

# -------------------------------------------------------------
# 5. 終端精要輸出與 HTML 歷史鑑識報告生成
# -------------------------------------------------------------
Write-Host "`n========================= [歷史鑑識摘要] =========================" -ForegroundColor Green

if ($RdpLogons.Count -gt 0) {
    Write-Host "`n[!] 歷史外部登入成功紀錄 (RDP / Network Logons):" -ForegroundColor Yellow
    $RdpLogons | Format-Table TimeGenerated, TargetUser, LogonType, SourceIP, SourcePort -AutoSize
} else {
    Write-Host "`n[✔] 未發現可疑的外部 RDP/網路成功登入紀錄。" -ForegroundColor Gray
}

if ($NewServices.Count -gt 0) {
    Write-Host "`n[!] 歷史新註冊之系統服務 (Event 7045):" -ForegroundColor Yellow
    $NewServices | Format-Table TimeGenerated, ServiceName, ImagePath -AutoSize
} else {
    Write-Host "`n[✔] 過去 $EventLookbackDays 天未發現新註冊系統服務。" -ForegroundColor Gray
}

if ($SuspiciousTasks.Count -gt 0) {
    Write-Host "`n[!] 可疑排程任務 (Persistence Tasks):" -ForegroundColor Yellow
    $SuspiciousTasks | Format-Table TaskName, State, Action -AutoSize
}

if (-not $NoHtml) {
    $HtmlPath = Join-Path $OutputDir "Historical_Report_${HostName}_${FileTimestamp}.html"

    $rdpHtmlRows = ($RdpLogons | ForEach-Object {
        "<tr><td>$($_.TimeGenerated)</td><td><strong>$($_.TargetUser)</strong></td><td>$($_.LogonType)</td><td class='code-path'>$($_.SourceIP):$($_.SourcePort)</td><td>$($_.AuthPackage)</td></tr>"
    }) -join "`n"

    $failedHtmlRows = ($FailedLogons | Select-Object -First 20 | ForEach-Object {
        "<tr><td>$($_.TimeGenerated)</td><td><strong>$($_.TargetUser)</strong></td><td>$($_.SourceIP)</td><td>$($_.LogonType)</td><td>$($_.FailureReason)</td></tr>"
    }) -join "`n"

    $serviceHtmlRows = ($NewServices | ForEach-Object {
        "<tr><td>$($_.TimeGenerated)</td><td><strong>$($_.ServiceName)</strong></td><td class='code-path'>$($_.ImagePath)</td><td>$($_.AccountName)</td></tr>"
    }) -join "`n"

    $prefetchHtmlRows = ($RecentPrefetch | ForEach-Object {
        "<tr><td>$($_.ExecutionTime)</td><td><strong>$($_.EstimatedExe)</strong></td><td>$($_.PrefetchFile)</td><td>$($_.SizeKB) KB</td></tr>"
    }) -join "`n"

    $dnsHtmlRows = ($DnsRecords | Select-Object -First 30 | ForEach-Object {
        "<tr><td><strong>$($_.RecordName)</strong></td><td>$($_.RecordType)</td><td class='code-path'>$($_.Data)</td><td>$($_.TimeToLive)</td></tr>"
    }) -join "`n"

    $taskHtmlRows = ($SuspiciousTasks | ForEach-Object {
        "<tr><td><strong>$($_.TaskName)</strong></td><td>$($_.State)</td><td class='code-path'>$($_.Action)</td></tr>"
    }) -join "`n"

    $HtmlContent = @"
<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>端點事後歷史鑑識報告 - $HostName</title>
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f8f9fa; color: #333; margin: 0; padding: 25px; }
    .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
    h1 { color: #1a202c; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-top: 0; }
    h2 { color: #2d3748; margin-top: 30px; border-left: 4px solid #805ad5; padding-left: 10px; font-size: 1.25rem; }
    .meta-box { background: #edf2f7; padding: 15px; border-radius: 6px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 20px; font-size: 0.95rem; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9rem; }
    th, td { border: 1px solid #e2e8f0; padding: 10px 12px; text-align: left; }
    th { background: #f7fafc; color: #4a5568; font-weight: 600; }
    tr:nth-child(even) { background-color: #fcfdfd; }
    tr:hover { background-color: #f1f5f9; }
    .code-path { font-family: Consolas, Monaco, monospace; font-size: 0.82rem; color: #4a5568; word-break: break-all; }
    .empty-note { color: #718096; font-style: italic; padding: 10px 0; }
</style>
</head>
<body>
<div class="container">
    <h1>端點事後歷史跡證鑑識報告 (Historical Retrospective Triage)</h1>
    <div class="meta-box">
        <div><strong>主機名稱：</strong>$HostName</div>
        <div><strong>報告時間：</strong>$ReportTime</div>
        <div><strong>分析範圍：</strong>過去 $EventLookbackDays 天</div>
        <div><strong>鑑識身分：</strong>$CurrentUser</div>
    </div>

    <h2>1. 歷史外部登入成功紀錄 (RDP / Network Logons)</h2>
    $(if ($RdpLogons.Count -gt 0) {
        "<table><thead><tr><th>登入時間</th><th>登入使用者</th><th>登入類型</th><th>來源 IP 與通訊埠</th><th>認證封裝</th></tr></thead><tbody>$rdpHtmlRows</tbody></table>"
    } else {
        "<div class='empty-note'>✔ 過去 $EventLookbackDays 天內未發現外部 RDP 遠端登入成功紀錄。</div>"
    })

    <h2>2. 歷史新註冊之系統服務 (Event 7045)</h2>
    $(if ($NewServices.Count -gt 0) {
        "<table><thead><tr><th>安裝時間</th><th>服務名稱</th><th>執行程式路徑 (ImagePath)</th><th>啟動身分</th></tr></thead><tbody>$serviceHtmlRows</tbody></table>"
    } else {
        "<div class='empty-note'>✔ 過去 $EventLookbackDays 天未發現新註冊系統服務。</div>"
    })

    <h2>3. 可疑排程任務持久化 (Persistence Tasks)</h2>
    $(if ($SuspiciousTasks.Count -gt 0) {
        "<table><thead><tr><th>排程名稱</th><th>狀態</th><th>執行指令與參數</th></tr></thead><tbody>$taskHtmlRows</tbody></table>"
    } else {
        "<div class='empty-note'>✔ 未偵測到具備高風險臨時路徑或混淆指令的排程任務。</div>"
    })

    <h2>4. Prefetch 預讀取近期程式執行軌跡 (前 $TopPrefetchCount 筆)</h2>
    $(if ($RecentPrefetch.Count -gt 0) {
        "<table><thead><tr><th>推斷最後執行時間</th><th>推估主程式</th><th>Prefetch 檔名</th><th>大小</th></tr></thead><tbody>$prefetchHtmlRows</tbody></table>"
    } else {
        "<div class='empty-note'>無法讀取 Prefetch 資料庫。</div>"
    })

    <h2>5. DNS Client 快取解析紀錄 (前 30 筆非本地網域)</h2>
    $(if ($DnsRecords.Count -gt 0) {
        "<table><thead><tr><th>請求網域名稱</th><th>記錄類型</th><th>解析結果 (IP/CNAME)</th><th>TTL</th></tr></thead><tbody>$dnsHtmlRows</tbody></table>"
    } else {
        "<div class='empty-note'>當前 DNS 快取無外部紀錄。</div>"
    })
</div>
</body>
</html>
"@

    $HtmlContent | Out-File -FilePath $HtmlPath -Encoding utf8
    Write-Host "`n[+] HTML 歷史鑑識報告已產生：" -ForegroundColor Green
    Write-Host "    $HtmlPath" -ForegroundColor White
}

Write-Host "`n事後歷史鑑識完成！" -ForegroundColor Cyan



