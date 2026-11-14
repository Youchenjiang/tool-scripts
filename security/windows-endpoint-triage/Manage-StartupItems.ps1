<#
.SYNOPSIS
    Manage-StartupItems.ps1 - Windows 三大類開機自啟管理工具（完全自主掌握，無需第三方工具）
.DESCRIPTION
    原生鑑識與管理 Windows 三大類開機自動啟動項：
      1. 啟動項目 (Startup Items - Registry Run 鍵值與 Startup 資料夾捷徑)
      2. 系統服務 (System Services - Win32 服務開機類型與狀態)
      3. 計劃任務 (Scheduled Tasks - 工作排程器開機/登入自啟排程)
    支援清單列出 (-List)、關鍵字搜尋 (-Search)、無效項目篩選 (-InvalidOnly) 以及狀態切換 (-EnableName / -DisableName)。
    具備微軟 PE 檔案資訊分析與官方說明提取功能，能精準標記「該啟動項目無效（目標不存在）」與程式真實廠商說明。
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateSet('All', 'Startup', 'Service', 'Task')]
    [string]$Category = 'All',

    [string]$Search = '',

    [switch]$List,

    [switch]$InvalidOnly,

    [string]$EnableName = '',
    [string]$DisableName = '',
    [ValidateSet('Startup', 'Service', 'Task')]
    [string]$TargetCategory = 'Startup'
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'SilentlyContinue'

$IsAdmin = ([System.Security.Principal.WindowsPrincipal][System.Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)

# -------------------------------------------------------------
# 輔助函式：解析指令目標檔案、驗證有效性並提取官方說明 (FileVersion / Description)
# -------------------------------------------------------------
function Resolve-ExecutableMetadata {
    param(
        [string]$RawCommand,
        [string]$ShortcutFilePath = ''
    )

    $meta = @{
        ExePath     = ''
        Exists      = $false
        Description = ''
        Company     = ''
        IsValid     = $true
    }

    if ($ShortcutFilePath -and (Test-Path $ShortcutFilePath)) {
        try {
            $wscript = New-Object -ComObject WScript.Shell
            $shortcut = $wscript.CreateShortcut($ShortcutFilePath)
            $target = $shortcut.TargetPath
            $shortcutDesc = $shortcut.Description
            
            if ($target) {
                $expandedTarget = [Environment]::ExpandEnvironmentVariables($target).Trim()
                $meta.ExePath = $expandedTarget
                $meta.Exists = Test-Path $expandedTarget -PathType Leaf
            }

            if (-not $meta.Exists) {
                $meta.IsValid = $false
                $meta.Description = "該啟動項目無效（捷徑指向的檔案不存在或已解除安裝）"
                return $meta
            }

            if ($shortcutDesc) {
                $meta.Description = $shortcutDesc
            }
        } catch {}
    }

    if (-not $meta.ExePath -and $RawCommand) {
        $expanded = [Environment]::ExpandEnvironmentVariables($RawCommand).Trim()
        
        # 處理帶引號路徑 "C:\Path\To\file.exe" args...
        if ($expanded.StartsWith('"')) {
            $endQuote = $expanded.IndexOf('"', 1)
            if ($endQuote -gt 1) {
                $meta.ExePath = $expanded.Substring(1, $endQuote - 1)
            }
        } else {
            # 處理無引號路徑 (可能帶有空格)
            $firstSpace = $expanded.IndexOf(' ')
            if ($firstSpace -gt 0) {
                $candidate = $expanded.Substring(0, $firstSpace)
                if (Test-Path $candidate) {
                    $meta.ExePath = $candidate
                } else {
                    $parts = $expanded.Split(' ')
                    $accum = ""
                    foreach ($p in $parts) {
                        $accum = if ($accum) { "$accum $p" } else { $p }
                        if (Test-Path $accum) { $meta.ExePath = $accum; break }
                    }
                    if (-not $meta.ExePath) { $meta.ExePath = $candidate }
                }
            } else {
                $meta.ExePath = $expanded
            }
        }

        # 檢查檔案是否存在
        if ($meta.ExePath) {
            $meta.Exists = Test-Path $meta.ExePath -PathType Leaf
        }
    }

    if (-not $meta.Exists) {
        $meta.IsValid = $false
        if (-not $meta.Description) {
            $meta.Description = "該啟動項目無效（目標檔案不存在或已解除安裝）"
        }
    } else {
        # 檔案存在，嘗試讀取 PE 標頭之 FileDescription / Company / Product
        try {
            $fileVer = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($meta.ExePath)
            $desc = $fileVer.FileDescription
            if (-not $desc) { $desc = $fileVer.ProductName }
            
            $comp = $fileVer.CompanyName
            if ($comp -and $desc -and ($desc -notlike "*$comp*")) {
                $meta.Description = "$desc ($comp)"
            } elseif ($desc) {
                $meta.Description = $desc
            } elseif ($comp) {
                $meta.Description = $comp
            }
            $meta.Company = $comp
        } catch {}
    }

    if (-not $meta.Description) {
        $meta.Description = "無附加說明"
    }

    return $meta
}

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

                $meta = Resolve-ExecutableMetadata -RawCommand $command
                $itemStatus = if (-not $meta.IsValid) { "該啟動項目無效" } else { $status }

                $results += [PSCustomObject]@{
                    Category    = "啟動項目"
                    SubLocation = $target.Name
                    Name        = $valueName
                    DisplayName = $valueName
                    Status      = $itemStatus
                    IsValid     = $meta.IsValid
                    Description = $meta.Description
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

                $meta = Resolve-ExecutableMetadata -RawCommand $item.FullName -ShortcutFilePath $item.FullName
                $itemStatus = if (-not $meta.IsValid) { "該啟動項目無效" } else { $status }

                $results += [PSCustomObject]@{
                    Category    = "啟動項目"
                    SubLocation = $f.Scope
                    Name        = $item.Name
                    DisplayName = $item.Name
                    Status      = $itemStatus
                    IsValid     = $meta.IsValid
                    Description = $meta.Description
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

        # 檢驗服務執行檔二進位路徑是否存在
        $meta = Resolve-ExecutableMetadata -RawCommand $svc.PathName
        $desc = if ($svc.Description) { $svc.Description } else { $meta.Description }
        $itemStatus = if (-not $meta.IsValid) { "該啟動項目無效" } else { $status }

        $results += [PSCustomObject]@{
            Category    = "系統服務"
            SubLocation = "Win32_Service"
            Name        = $svc.Name
            DisplayName = $svc.DisplayName
            Status      = $itemStatus
            IsValid     = $meta.IsValid
            Description = $desc
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
        $firstAction = $t.Actions | Select-Object -First 1
        
        $meta = if ($firstAction -and $firstAction.Execute) {
            Resolve-ExecutableMetadata -RawCommand $firstAction.Execute
        } else {
            @{ IsValid = $true; Description = '' }
        }

        $desc = if ($t.Description) { $t.Description } elseif ($meta.Description) { $meta.Description } else { "無詳細說明" }
        $status = if ($t.State -eq 'Disabled') { "已禁用" } else { "已啟用" }
        $itemStatus = if (-not $meta.IsValid) { "該啟動項目無效" } else { $status }

        $results += [PSCustomObject]@{
            Category    = "計劃任務"
            SubLocation = $t.TaskPath
            Name        = $t.TaskName
            DisplayName = $t.TaskName
            Status      = $itemStatus
            IsValid     = $meta.IsValid
            Description = $desc
            State       = "$($t.State)"
            Command     = $actionStr
            Hive        = "Task"
            RegPath     = $t.TaskPath
        }
    }

    return $results
}

# -------------------------------------------------------------
# 修改與狀態切換邏輯 (Enable / Disable)
# -------------------------------------------------------------
function Set-StartupState {
    param(
        [string]$TargetName,
        [string]$TargetType, # Startup, Service, Task
        [bool]$Enable
    )

    $actionName = if ($Enable) { "啟用" } else { "禁用" }
    Write-Host "[*] 正在將 [$TargetType] -> '$TargetName' 設定為: $actionName..." -ForegroundColor Cyan

    switch ($TargetType) {
        'Startup' {
            # 修改 Windows 原生 StartupApproved 登錄檔標記（如同工作管理員與火絨）
            $hive = 'CurrentUser'
            $subPath = "Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
            
            # 若為 HKLM 則切換
            $runKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey("Software\Microsoft\Windows\CurrentVersion\Run")
            $foundInUser = $runKey -and ($runKey.GetValue($TargetName) -ne $null)
            if ($runKey) { $runKey.Close() }

            if (-not $foundInUser) {
                $hive = 'LocalMachine'
            }

            try {
                $reg = [Microsoft.Win32.Registry]::($hive).OpenSubKey($subPath, $true)
                if (-not $reg) {
                    $reg = [Microsoft.Win32.Registry]::($hive).CreateSubKey($subPath)
                }

                $existing = $reg.GetValue($TargetName)
                $newBytes = if ($existing) { [byte[]]$existing } else { [byte[]]@(0x02,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00) }
                
                # 0x02 = 啟用 (Enabled), 0x03 = 禁用 (Disabled)
                $newBytes[0] = if ($Enable) { [byte]0x02 } else { [byte]0x03 }
                
                $reg.SetValue($TargetName, $newBytes, [Microsoft.Win32.RegistryValueKind]::Binary)
                $reg.Close()
                Write-Host "[+] 成功更新啟動項目 '$TargetName' 狀態為 [$actionName]！" -ForegroundColor Green
            } catch {
                Write-Host "[-] 修改啟動項目失敗: $($_.Exception.Message)" -ForegroundColor Red
            }
        }

        'Service' {
            $startType = if ($Enable) { 'Automatic' } else { 'Disabled' }
            try {
                Set-Service -Name $TargetName -StartupType $startType -ErrorAction Stop
                if (-not $Enable) {
                    Stop-Service -Name $TargetName -ErrorAction SilentlyContinue
                }
                Write-Host "[+] 成功更新系統服務 '$TargetName' 啟動類型為 [$startType]！" -ForegroundColor Green
            } catch {
                Write-Host "[-] 修改系統服務失敗: $($_.Exception.Message) (請確認是否具備系統管理員權限)" -ForegroundColor Red
            }
        }

        'Task' {
            try {
                if ($Enable) {
                    Enable-ScheduledTask -TaskName $TargetName -ErrorAction Stop | Out-Null
                } else {
                    Disable-ScheduledTask -TaskName $TargetName -ErrorAction Stop | Out-Null
                }
                Write-Host "[+] 成功更新計劃任務 '$TargetName' 狀態為 [$actionName]！" -ForegroundColor Green
            } catch {
                Write-Host "[-] 修改計劃任務失敗: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
}

# -------------------------------------------------------------
# 執行修改指令 (-EnableName / -DisableName)
# -------------------------------------------------------------
if ($EnableName) {
    Set-StartupState -TargetName $EnableName -TargetType $TargetCategory -Enable $true
    return
}

if ($DisableName) {
    Set-StartupState -TargetName $DisableName -TargetType $TargetCategory -Enable $false
    return
}

# -------------------------------------------------------------
# 預設執行：清單列出與搜尋 (-List)
# -------------------------------------------------------------
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " [Manage-StartupItems] Windows 三大類開機自啟項目管理盤點 " -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "執行身分: $([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) $(if($IsAdmin){'[系統管理員]'}else{'[非管理員-修改服務需提升權限]'})"
if ($Search) { Write-Host "搜尋關鍵字: '$Search'" -ForegroundColor Yellow }
if ($InvalidOnly) { Write-Host "過濾模式: 僅顯示無效/殘留啟動項目" -ForegroundColor Magenta }
Write-Host ""

$allRecords = @()

if ($Category -in @('All', 'Startup')) {
    $allRecords += Get-RegistryAndFolderStartupItems
}
if ($Category -in @('All', 'Service')) {
    $allRecords += Get-SystemServicesStartup
}
if ($Category -in @('All', 'Task')) {
    $allRecords += Get-ScheduledTasksStartup
}

if ($InvalidOnly) {
    $allRecords = $allRecords | Where-Object { $_.IsValid -eq $false }
}

if ($Search) {
    $allRecords = $allRecords | Where-Object {
        $_.Name -like "*$Search*" -or $_.DisplayName -like "*$Search*" -or $_.Description -like "*$Search*" -or $_.Command -like "*$Search*"
    }
}

$grouped = $allRecords | Group-Object Category
foreach ($g in $grouped) {
    Write-Host "=== 【$($g.Name)】(共 $($g.Count) 項) ===" -ForegroundColor Cyan
    $g.Group | ForEach-Object {
        $statusColor = if ($_.Status -like "*無效*") { 'Red' } elseif ($_.Status -eq "已啟用") { 'Green' } else { 'Yellow' }
        Write-Host "  項目名稱: $($_.Name)" -ForegroundColor White
        Write-Host "  當前狀態: " -NoNewline; Write-Host "$($_.Status)" -ForegroundColor $statusColor
        Write-Host "  功能說明: $($_.Description)" -ForegroundColor Gray
        Write-Host "  註冊位置: $($_.SubLocation)" -ForegroundColor DarkGray
        Write-Host "  啟動指令: $($_.Command)" -ForegroundColor DarkGray
        Write-Host "  -------------------------------------------------------------" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "修改狀態指令範例：" -ForegroundColor Yellow
Write-Host "  禁用啟動項目: .\Manage-StartupItems.ps1 -DisableName 'GameViewer' -TargetCategory Startup"
Write-Host "  禁用系統服務: .\Manage-StartupItems.ps1 -DisableName 'KDService' -TargetCategory Service"
Write-Host "  禁用計劃任務: .\Manage-StartupItems.ps1 -DisableName 'ACC' -TargetCategory Task"
Write-Host "  重新啟用項目: .\Manage-StartupItems.ps1 -EnableName 'GameViewer' -TargetCategory Startup"
