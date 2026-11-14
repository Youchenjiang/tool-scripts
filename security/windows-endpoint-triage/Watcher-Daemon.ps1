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
