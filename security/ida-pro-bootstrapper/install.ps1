# ==============================================================================
# IDA Professional 9.1 - 自動化安裝、環境配置與維護精靈 (初始版本)
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

$global:IdaInstallDir = if ($IdaPath) { $IdaPath.Trim('"') } else { $ScriptDir }

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      IDA Pro 9.1 一鍵自動化配置與維護工具箱" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  - 目標目錄 : $global:IdaInstallDir" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Cyan
