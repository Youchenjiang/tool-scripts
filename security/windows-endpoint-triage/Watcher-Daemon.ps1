<#
.SYNOPSIS
    Watcher-Daemon.ps1 - Windows 端點異常守護器（背景監控與自動觸發鑑識）
.DESCRIPTION
    輕量化背景常駐守護程序，持續監控系統異常狀態（CPU 飆高、未知外聯、高危監聽），
    一旦符合觸發規則，即刻自動觸發快照記錄現場。
#>

[CmdletBinding()]
param(
    [int]$CpuThreshold = 85,
    [int]$CheckIntervalSec = 10,
    [int]$ConsecutiveHits = 2,
    [int]$AlertCooldownSec = 120,
    [string]$OutputDir = (Get-Location).Path
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'SilentlyContinue'

$HostName = $env:COMPUTERNAME
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) { $ScriptDir = (Get-Location).Path }

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " [Watcher-Daemon] Windows 端點異常背景守護器已啟動 " -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "監控主機: $HostName | 檢查頻率: 每 $CheckIntervalSec 秒一次"
Write-Host "觸發門檻: CPU > $CpuThreshold% (連續超標 $ConsecutiveHits 次) 或 偵測到異常公網外聯"
Write-Host "警報冷卻時間: $AlertCooldownSec 秒 (避免頻繁快照造成磁碟負載)"
Write-Host "輸出目錄: $OutputDir`n"

$HighCpuStreak = 0
$LastAlertTime = [DateTime]::MinValue

function Get-TotalCpuPercentage {
    try {
        $sample = Get-Counter '\Processor(_Total)\% Processor Time' -ErrorAction Stop
        return [math]::Round($sample.CounterSamples[0].CookedValue, 1)
    } catch {
        # 降級備用：以 1 秒差分計算
        $p1 = (Get-Process | Measure-Object -Property CPU -Sum).Sum
        Start-Sleep -Seconds 1
        $p2 = (Get-Process | Measure-Object -Property CPU -Sum).Sum
        $pct = ($p2 - $p1) / 1 * 100 / [Environment]::ProcessorCount
        return [math]::Round([math]::Max(0, [math]::Min(100, $pct)), 1)
    }
}

function Test-AnomalyTriggers {
    $triggersFired = @()

    # 1. 檢測全機 CPU 使用率
    $totalCpu = Get-TotalCpuPercentage
    if ($totalCpu -ge $CpuThreshold) {
        $script:HighCpuStreak++
        if ($script:HighCpuStreak -ge $ConsecutiveHits) {
            $triggersFired += "CPU 佔用持續過高 ($totalCpu%, 連續 $HighCpuStreak 次超標)"
        }
    } else {
        $script:HighCpuStreak = 0
    }

    # 2. 檢測常見遠端木馬與穿透工具進程
    $remoteKeywords = @('gameviewer', 'anydesk', 'teamviewer', 'todesk', 'rustdesk', 'sunlogin', 'frpc', 'ngrok', 'softether')
    $runningProcesses = Get-Process
    foreach ($p in $runningProcesses) {
        foreach ($kw in $remoteKeywords) {
            if ($p.ProcessName -like "*$kw*") {
                $triggersFired += "偵測到活躍穿透/遠端工具進程: $($p.ProcessName) (PID: $($p.Id))"
                break
            }
        }
    }

    return @{
        TotalCpu = $totalCpu
        Triggers = $triggersFired
    }
}

$IncidentLogFile = Join-Path $OutputDir "triage_incidents.jsonl"
$TriageScript = Join-Path $ScriptDir "ThreatHunter-Triage.ps1"

Write-Host "[*] 守護程序開始常駐監控（按 Ctrl+C 可停止）...`n" -ForegroundColor Green

while ($true) {
    $now = Get-Date
    $eval = Test-AnomalyTriggers

    $timeStr = $now.ToString("yyyy-MM-dd HH:mm:ss")
    $cpuDisplay = "$($eval.TotalCpu)%".PadLeft(6)
    Write-Host "[$timeStr] 系統狀態正常 | CPU: $cpuDisplay | 守護運行中..." -ForegroundColor DarkGray -NoNewline
    Write-Host "`r" -NoNewline

    if ($eval.Triggers.Count -gt 0) {
        $secSinceLast = ($now - $LastAlertTime).TotalSeconds
        if ($secSinceLast -ge $AlertCooldownSec) {
            Write-Host "`n`n[!] 🚨 偵測到異常觸發條件！" -ForegroundColor Red
            foreach ($t in $eval.Triggers) {
                Write-Host "    - $t" -ForegroundColor Yellow
            }

            Write-Host "[+] 正在自動擷取現場鑑識快照..." -ForegroundColor Cyan
            $snapshotTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"

            if (Test-Path $TriageScript) {
                & powershell.exe -ExecutionPolicy Bypass -File $TriageScript -OutputDir $OutputDir
            } else {
                Write-Host "[-] 找不到鑑識引擎腳本: $TriageScript" -ForegroundColor Red
            }

            # 寫入 JSONL 事件紀錄
            $incidentRecord = [PSCustomObject]@{
                Timestamp = $timeStr
                HostName  = $HostName
                TotalCpu  = $eval.TotalCpu
                Reasons   = $eval.Triggers
            } | ConvertTo-Json -Compress

            Add-Content -Path $IncidentLogFile -Value $incidentRecord -Encoding utf8
            Write-Host "[+] 事件已記錄至黑盒子日誌: $IncidentLogFile" -ForegroundColor Green
            Write-Host "[*] 進入警報冷卻期 ($AlertCooldownSec 秒)，防範重疊告警...`n" -ForegroundColor DarkYellow

            $script:LastAlertTime = $now
            $script:HighCpuStreak = 0
        }
    }

    Start-Sleep -Seconds $CheckIntervalSec
}

