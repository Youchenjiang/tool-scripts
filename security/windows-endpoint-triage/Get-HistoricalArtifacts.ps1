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

