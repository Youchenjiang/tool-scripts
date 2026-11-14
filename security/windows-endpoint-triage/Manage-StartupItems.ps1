<#
.SYNOPSIS
    Manage-StartupItems.ps1 - Windows 三大類開機自啟管理工具（完全自主掌握，無需第三方工具）
.DESCRIPTION
    原生鑑識與管理 Windows 三大類開機自動啟動項：
      1. 啟動項目 (Startup Items - Registry Run 鍵值與 Startup 資料夾捷徑)
      2. 系統服務 (System Services - Win32 服務開機類型與狀態)
      3. 計劃任務 (Scheduled Tasks - 工作排程器開機/登入自啟排程)
    支援清單列出 (-List)、關鍵字搜尋 (-Search) 以及狀態切換 (-Enable / -Disable)。
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateSet('All', 'Startup', 'Service', 'Task')]
    [string]$Category = 'All',

    [string]$Search = '',

    [switch]$List,

    [string]$EnableName = '',
    [string]$DisableName = '',
    [ValidateSet('Startup', 'Service', 'Task')]
    [string]$TargetCategory = 'Startup'
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'SilentlyContinue'

$IsAdmin = ([System.Security.Principal.WindowsPrincipal][System.Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)

# -------------------------------------------------------------
# 類別一：啟動項目 (Registry Run & Startup Folders)
# -------------------------------------------------------------
function Get-RegistryAndFolderStartupItems {
    $results = @()

    $regTargets = @(
        @{ Hive = 'CurrentUser'; Path = 'Software\Microsoft\Windows\CurrentVersion\Run'; Name = 'HKCU:Run' },
        @{ Hive = 'LocalMachine'; Path = 'Software\Microsoft\Windows\CurrentVersion\Run'; Name = 'HKLM:Run' },
        @{ Hive = 'LocalMachine'; Path = 'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run'; Name = 'HKLM:Run(x86)' }
    )

    foreach ($target in $regTargets) {
        $regKey = [Microsoft.Win32.Registry]::($target.Hive).OpenSubKey($target.Path)
        if ($regKey) {
            # 讀取 Windows 原生 StartupApproved 禁用標記 (第 0 位元組: 02=啟用, 03=禁用)
            $approvedKey = [Microsoft.Win32.Registry]::($target.Hive).OpenSubKey("Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run")
            
            foreach ($valueName in $regKey.GetValueNames()) {
                $command = $regKey.GetValue($valueName)
                $status = "已啟用"
                if ($approvedKey) {
                    $approvedBytes = $approvedKey.GetValue($valueName)
                    if ($approvedBytes -and $approvedBytes[0] -eq 3) {
                        $status = "已禁用"
                    }
                }

                $results += [PSCustomObject]@{
                    Category    = "啟動項目"
                    SubLocation = $target.Name
                    Name        = $valueName
                    Status      = $status
                    Command     = $command
                    Hive        = $target.Hive
                    RegPath     = $target.Path
                }
            }
            $regKey.Close()
            if ($approvedKey) { $approvedKey.Close() }
        }
    }

    # 檢查開機啟動資料夾 (Startup Folder)
    $folders = @(
        @{ Path = [Environment]::GetFolderPath('Startup'); Scope = 'User Startup Folder' },
        @{ Path = [Environment]::GetFolderPath('CommonStartup'); Scope = 'Common Startup Folder' }
    )

    foreach ($f in $folders) {
        if (Test-Path $f.Path) {
            $approvedFolderKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey("Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder")
            $items = Get-ChildItem -Path $f.Path -File
            foreach ($item in $items) {
                $status = "已啟用"
                if ($approvedFolderKey) {
                    $b = $approvedFolderKey.GetValue($item.Name)
                    if ($b -and $b[0] -eq 3) { $status = "已禁用" }
                }
                $results += [PSCustomObject]@{
                    Category    = "啟動項目"
                    SubLocation = $f.Scope
                    Name        = $item.Name
                    Status      = $status
                    Command     = $item.FullName
                    Hive        = "File"
                    RegPath     = $f.Path
                }
            }
            if ($approvedFolderKey) { $approvedFolderKey.Close() }
        }
    }

    return $results
}

# -------------------------------------------------------------
# 類別二：系統服務 (System Services)
# -------------------------------------------------------------
function Get-SystemServicesStartup {
    $results = @()
    $services = Get-CimInstance Win32_Service

    foreach ($svc in $services) {
        $status = switch ($svc.StartMode) {
            'Auto'     { "已啟用" }
            'Disabled' { "已禁用" }
            'Manual'   { "手動啟動" }
            default    { $svc.StartMode }
        }

        $results += [PSCustomObject]@{
            Category    = "系統服務"
            SubLocation = "Win32_Service"
            Name        = $svc.Name
            DisplayName = $svc.DisplayName
            Status      = $status
            State       = $svc.State
            Command     = $svc.PathName
            Hive        = "Service"
            RegPath     = "HKLM:\SYSTEM\CurrentControlSet\Services\$($svc.Name)"
        }
    }

    return $results
}

# -------------------------------------------------------------
# 類別三：計劃任務 (Scheduled Tasks)
# -------------------------------------------------------------
function Get-ScheduledTasksStartup {
    $results = @()
    $tasks = Get-ScheduledTask

    foreach ($t in $tasks) {
        $actionStr = ($t.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)".Trim() }) -join " ; "
        $status = if ($t.State -eq 'Disabled') { "已禁用" } else { "已啟用" }

        $results += [PSCustomObject]@{
            Category    = "計劃任務"
            SubLocation = $t.TaskPath
            Name        = $t.TaskName
            DisplayName = $t.TaskName
            Status      = $status
            State       = "$($t.State)"
            Command     = $actionStr
            Hive        = "Task"
            RegPath     = $t.TaskPath
        }
    }

    return $results
}

