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
