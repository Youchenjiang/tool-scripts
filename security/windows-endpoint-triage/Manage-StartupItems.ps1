<#
.SYNOPSIS
    Manage-StartupItems.ps1 - Windows 三大類開機自啟管理工具（完全自主掌握，無需第三方工具）
.DESCRIPTION
    原生鑑識與管理 Windows 三大類開機自動啟動項：
      1. 啟動項目 (Startup Items - Registry Run 鍵值與 Startup 資料夾捷徑)
      2. 系統服務 (System Services - Win32 服務開機類型與狀態)
      3. 計劃任務 (Scheduled Tasks - 工作排程器開機/登入自啟排程)
    
    支援三種操作方式：
      A. 互動選單模式 (-i / -Interactive)：如同火絨一樣，只需輸入編號即可切換啟用/禁用！
      B. 智慧極簡指令 (-Toggle / -T, -Disable / -D, -Enable / -E)：自動跨三大類別比對名稱，無需輸入長參數！
      C. 清單列出與搜尋 (-List, -Search, -InvalidOnly)：快速盤點與過濾無效殘留項。
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [Alias('C')]
    [ValidateSet('All', 'Startup', 'Service', 'Task')]
    [string]$Category = 'All',

    [Alias('S')]
    [string]$Search = '',

    [switch]$List,

    [switch]$InvalidOnly,

    # 快捷切換（智慧跨三大類別識別，無需指定 Category）
    [Alias('T')]
    [string]$Toggle = '',

    [Alias('D')]
    [string]$Disable = '',

    [Alias('E')]
    [string]$Enable = '',

    # 互動式選單模式（像火絨一樣只需輸入編號即可切換）
    [Alias('i', 'Menu')]
    [switch]$Interactive,

    # 傳統指定參數相容
    [string]$EnableName = '',
    [string]$DisableName = '',
    [ValidateSet('Startup', 'Service', 'Task', '')]
    [string]$TargetCategory = ''
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
                [byte[]]$newBytes = if ($existing) { [byte[]]$existing } else { [byte[]]@(0x02,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00) }
                
                # 0x02 = 啟用 (Enabled), 0x03 = 禁用 (Disabled)
                $newBytes[0] = if ($Enable) { [byte]0x02 } else { [byte]0x03 }
                
                $reg.SetValue($TargetName, [byte[]]$newBytes, [Microsoft.Win32.RegistryValueKind]::Binary)
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
# 智慧搜尋與切換輔助 (自動判定類別，使用者免輸入長參數)
# -------------------------------------------------------------
function Find-StartupItem {
    param([string]$Query)
    $all = @()
    $all += Get-RegistryAndFolderStartupItems
    $all += Get-SystemServicesStartup
    $all += Get-ScheduledTasksStartup

    $exact = $all | Where-Object { $_.Name -eq $Query }
    if ($exact) { return $exact[0] }

    $fuzzy = $all | Where-Object { $_.Name -like "*$Query*" -or $_.DisplayName -like "*$Query*" }
    if ($fuzzy.Count -eq 1) { return $fuzzy[0] }
    if ($fuzzy.Count -gt 1) {
        Write-Host "[!] 找到多個相符項目：" -ForegroundColor Yellow
        for ($i = 0; $i -lt $fuzzy.Count; $i++) {
            Write-Host "  [$($i + 1)] [$($fuzzy[$i].Category)] $($fuzzy[$i].Name) ($($fuzzy[$i].Status)) - $($fuzzy[$i].Description)"
        }
        $choice = Read-Host "請輸入欲操作的編號 (1-$($fuzzy.Count))"
        $idx = [int]$choice - 1
        if ($idx -ge 0 -and $idx -lt $fuzzy.Count) {
            return $fuzzy[$idx]
        }
        return $null
    }
    Write-Host "[-] 找不到名稱或關鍵字為 '$Query' 的開機項目！" -ForegroundColor Red
    return $null
}

function Toggle-ItemStatus ($item) {
    if (-not $item) { return }
    $typeMap = @{
        '啟動項目' = 'Startup'
        '系統服務' = 'Service'
        '計劃任務' = 'Task'
    }
    $tType = $typeMap[$item.Category]
    $enable = if ($item.Status -like "*已啟用*") { $false } else { $true }
    Set-StartupState -TargetName $item.Name -TargetType $tType -Enable $enable
}

# -------------------------------------------------------------
# 互動式選單模式 (TUI Menu) - 像火絨一樣直接輸入編號切換
# -------------------------------------------------------------
function Start-InteractiveMenu {
    $currentCategory = 'Startup'
    $filter = ''
    $invalidOnly = $false

    while ($true) {
        Clear-Host
        Write-Host "==========================================================================================" -ForegroundColor Cyan
        Write-Host " [Manage-StartupItems] Windows 開機自啟項目互動管理中心 (像火絨一樣直接輸入編號切換) " -ForegroundColor Yellow
        Write-Host "==========================================================================================" -ForegroundColor Cyan
        Write-Host "當前類別: [$currentCategory] | 關鍵字: [$(if($filter){$filter}else{'全部'})] | 僅無效: [$(if($invalidOnly){'是'}else{'否'})] | 身分: $(if($IsAdmin){'系統管理員'}else{'一般使用者'})"
        Write-Host ""

        $items = @()
        switch ($currentCategory) {
            'Startup' { $items = Get-RegistryAndFolderStartupItems }
            'Service' { $items = Get-SystemServicesStartup }
            'Task'    { $items = Get-ScheduledTasksStartup }
            'All'     {
                $items += Get-RegistryAndFolderStartupItems
                $items += Get-SystemServicesStartup
                $items += Get-ScheduledTasksStartup
            }
        }

        if ($filter) {
            $items = $items | Where-Object { $_.Name -like "*$filter*" -or $_.DisplayName -like "*$filter*" -or $_.Description -like "*$filter*" }
        }
        if ($invalidOnly) {
            $items = $items | Where-Object { $_.IsValid -eq $false }
        }

        if ($items.Count -eq 0) {
            Write-Host "  （目前查無相符項目）" -ForegroundColor DarkGray
        } else {
            Write-Host ("{0,-5} {1,-8} {2,-10} {3,-32} {4}" -f "編號", "類別", "當前狀態", "項目名稱", "功能說明與發行商") -ForegroundColor Cyan
            Write-Host ("-" * 96) -ForegroundColor DarkGray
            for ($i = 0; $i -lt $items.Count; $i++) {
                $it = $items[$i]
                $color = if ($it.Status -like "*無效*") { "Red" } elseif ($it.Status -eq "已啟用") { "Green" } else { "Yellow" }
                $shortDesc = if ($it.Description.Length -gt 40) { $it.Description.Substring(0, 37) + "..." } else { $it.Description }
                $shortName = if ($it.Name.Length -gt 30) { $it.Name.Substring(0, 27) + "..." } else { $it.Name }
                
                Write-Host ("[{0,2}] " -f ($i + 1)) -NoNewline -ForegroundColor White
                Write-Host ("{0,-8}" -f $it.Category) -NoNewline -ForegroundColor DarkCyan
                Write-Host ("[{0}] " -f $it.Status) -NoNewline -ForegroundColor $color
                Write-Host ("{0,-32} " -f $shortName) -NoNewline -ForegroundColor White
                Write-Host $shortDesc -ForegroundColor Gray
            }
        }

        Write-Host ("-" * 96) -ForegroundColor DarkGray
        Write-Host "【快速指令】" -ForegroundColor Yellow
        Write-Host "  輸入 [編號] (例如 1)     : 立即切換該項目的 啟用/禁用 狀態"
        Write-Host "  輸入 [/s 關鍵字] (如 /s uu): 依關鍵字搜尋過濾"
        Write-Host "  輸入 [/c 類別] (1:啟動, 2:服務, 3:排程, 4:全部) : 切換類別"
        Write-Host "  輸入 [/inv]              : 切換僅顯示無效項目開關"
        Write-Host "  輸入 [Q]                 : 離開互動管理中心"
        Write-Host ""

        $inputCmd = Read-Host "請輸入指令或項目編號"
        if (-not $inputCmd) { continue }
        $trimmed = $inputCmd.Trim()

        if ($trimmed -eq 'Q' -or $trimmed -eq 'q') {
            break
        } elseif ($trimmed -match '^\d+$') {
            $selIdx = [int]$trimmed - 1
            if ($selIdx -ge 0 -and $selIdx -lt $items.Count) {
                Toggle-ItemStatus $items[$selIdx]
                Start-Sleep -Milliseconds 1000
            } else {
                Write-Host "[!] 無效的編號！" -ForegroundColor Red
                Start-Sleep -Milliseconds 800
            }
        } elseif ($trimmed.StartsWith('/s ') -or $trimmed.StartsWith('/S ')) {
            $filter = $trimmed.Substring(3).Trim()
        } elseif ($trimmed -eq '/s' -or $trimmed -eq '/S') {
            $filter = ''
        } elseif ($trimmed.StartsWith('/c ') -or $trimmed.StartsWith('/C ')) {
            $catArg = $trimmed.Substring(3).Trim()
            switch ($catArg) {
                '1' { $currentCategory = 'Startup' }
                '2' { $currentCategory = 'Service' }
                '3' { $currentCategory = 'Task' }
                '4' { $currentCategory = 'All' }
                'Startup' { $currentCategory = 'Startup' }
                'Service' { $currentCategory = 'Service' }
                'Task' { $currentCategory = 'Task' }
                'All' { $currentCategory = 'All' }
                default { Write-Host "[!] 未知類別！" -ForegroundColor Red; Start-Sleep -Milliseconds 500 }
            }
        } elseif ($trimmed -eq '/inv' -or $trimmed -eq '/INV') {
            $invalidOnly = -not $invalidOnly
        }
    }
}

# -------------------------------------------------------------
# 模式分流：互動模式 / 快捷切換 / 查詢列出
# -------------------------------------------------------------
if ($Interactive) {
    Start-InteractiveMenu
    return
}

# 智慧一鍵切換 (-Toggle / -T)
if ($Toggle) {
    $item = Find-StartupItem -Query $Toggle
    if ($item) {
        Toggle-ItemStatus $item
    }
    return
}

# 智慧禁用 (-Disable / -D)
if ($Disable) {
    $item = Find-StartupItem -Query $Disable
    if ($item) {
        $typeMap = @{ '啟動項目' = 'Startup'; '系統服務' = 'Service'; '計劃任務' = 'Task' }
        Set-StartupState -TargetName $item.Name -TargetType $typeMap[$item.Category] -Enable $false
    }
    return
}

# 智慧啟用 (-Enable / -E)
if ($Enable) {
    $item = Find-StartupItem -Query $Enable
    if ($item) {
        $typeMap = @{ '啟動項目' = 'Startup'; '系統服務' = 'Service'; '計劃任務' = 'Task' }
        Set-StartupState -TargetName $item.Name -TargetType $typeMap[$item.Category] -Enable $true
    }
    return
}

# 傳統相容指令
if ($EnableName) {
    $tType = if ($TargetCategory) { $TargetCategory } else { (Find-StartupItem -Query $EnableName).Category }
    Set-StartupState -TargetName $EnableName -TargetType $tType -Enable $true
    return
}

if ($DisableName) {
    $tType = if ($TargetCategory) { $TargetCategory } else { (Find-StartupItem -Query $DisableName).Category }
    Set-StartupState -TargetName $DisableName -TargetType $tType -Enable $false
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
Write-Host "【極簡操作指令】" -ForegroundColor Yellow
Write-Host "  進入互動選單模式 (只需按編號切換): .\Manage-StartupItems.ps1 -i" -ForegroundColor Cyan
Write-Host "  一鍵切換狀態 (免輸入類別):          .\Manage-StartupItems.ps1 -T 'GameViewer'"
Write-Host "  一鍵禁用項目 (免輸入類別):          .\Manage-StartupItems.ps1 -D 'GameViewer'"
Write-Host "  一鍵啟用項目 (免輸入類別):          .\Manage-StartupItems.ps1 -E 'GameViewer'"
