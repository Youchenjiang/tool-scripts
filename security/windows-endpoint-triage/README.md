# Windows Endpoint Forensic Triage Tool

[繁體中文版](README.zh-TW.md)

A native Windows emergency forensic triage script designed for Incident Response (DFIR) and Blue Team Threat Hunting. Built purely with native Windows PowerShell, it requires zero external dependencies, runtimes, or installations. It rapidly inspects exposed listening ports, active WAN connections, high-CPU processes, remote administration tools (RAT), and process masquerading in under 10 seconds, automatically generating a standalone styled HTML report with risk level badges.

## Key Forensic Dimensions

- **0.0.0.0 Listening Port Triage**:
  - Excludes internal local loopback interfaces (`127.0.0.1` / `::1`) to eliminate noise.
  - Highlights high-value attack surfaces (e.g., RDP 3389, SMB 445, MySQL 3306, MSSQL 1433, VNC 5900) and unmapped high ports.
- **Active Established WAN Connections**:
  - Filters out RFC 1918 private subnets and identifies processes communicating with public external IPs.
- **Instantaneous CPU Sampling & Resource Tracking**:
  - Uses a 1.5-second differential calculation to detect active high-CPU consumers.
  - Profiles top processes by cumulative processor time and memory working set.
- **Remote Administration & Tunneling Tool Detection (RAT)**:
  - Scans for commercial and open-source remote tools (GameViewer, AnyDesk, TeamViewer, ToDesk, RustDesk, Sunlogin, Tailscale, FRP, SoftEther, etc.).
- **Process Path Anomalies & Masquerading**:
  - Detects binaries running from suspicious temporary directories (`AppData\Local\Temp`, `Windows\Temp`, `Users\Public`).
  - Identifies masquerading Windows system binaries (e.g., `svchost.exe`, `csrss.exe`, `lsass.exe` outside `System32`).
- **Standalone Styled HTML Report Generation**:
  - Self-contained HTML report with responsive styling and severity badges.

## Requirements

- **Windows 10 / 11 / Server 2016+**
- **PowerShell 5.1+** (Built-in)
- Recommended to execute with **Administrator** privileges to inspect protected SYSTEM processes.

## Usage

### A. Manual On-Demand Triage (`ThreatHunter-Triage.ps1`)

Ideal for immediate, on-scene incident investigation.

```powershell
# Basic triage scan (outputs HTML report to current directory)
powershell -ExecutionPolicy Bypass -File .\ThreatHunter-Triage.ps1

# Output to custom directory
powershell -ExecutionPolicy Bypass -File .\ThreatHunter-Triage.ps1 -OutputDir "C:\Forensics"

# Terminal only (suppress HTML generation)
powershell -ExecutionPolicy Bypass -File .\ThreatHunter-Triage.ps1 -NoHtml
```

---

### B. Automated Watcher Daemon (`Watcher-Daemon.ps1`)

Eliminates the need for physical presence during anomalies. Continuously monitors system health in the background and automatically takes forensic snapshots upon high-CPU incidents or suspicious outbound tunneling.

#### 1. Interactive Foreground Monitoring

```powershell
# Default monitoring (CPU > 85% for 2 consecutive hits or detected remote tools)
powershell -ExecutionPolicy Bypass -File .\Watcher-Daemon.ps1

# Custom thresholds: 5-second interval, 80% CPU threshold, 60-second cooldown
powershell -ExecutionPolicy Bypass -File .\Watcher-Daemon.ps1 -CheckIntervalSec 5 -CpuThreshold 80 -AlertCooldownSec 60 -OutputDir "C:\Forensics"
```

#### 2. Background Windows Scheduled Task Deployment (Silent Autostart)

```powershell
# Install and start silent background scheduled task (Requires Administrator)
powershell -ExecutionPolicy Bypass -File .\Watcher-Daemon.ps1 -InstallTask -OutputDir "C:\Forensics"

# Check background task execution state
powershell -ExecutionPolicy Bypass -File .\Watcher-Daemon.ps1 -StatusTask

# Stop and uninstall scheduled task
powershell -ExecutionPolicy Bypass -File .\Watcher-Daemon.ps1 -UninstallTask
```

---

### C. Retrospective Historical Artifacts Analysis (`Get-HistoricalArtifacts.ps1`)

Enables post-incident investigations even after malicious processes terminate, connections drop, or binaries delete themselves.

```powershell
# Investigate historical artifacts over the last 7 days (default)
powershell -ExecutionPolicy Bypass -File .\Get-HistoricalArtifacts.ps1

# Expand lookback window to 30 days and extract 50 recent prefetch records
powershell -ExecutionPolicy Bypass -File .\Get-HistoricalArtifacts.ps1 -EventLookbackDays 30 -TopPrefetchCount 50 -OutputDir "C:\Forensics"
```

* Output Artifact: `Historical_Report_<HostName>_<Timestamp>.html`
* Forensic Coverage:
  1. **External Inbound Logons & RDP Source IPs** (Event 4624 Logon Auditing)
  2. **Newly Installed Windows Services** (Event 7045 Service Creation)
  3. **Windows Prefetch Execution Artifacts** (Evidence of deleted binaries)
  4. **DNS Client Resolution Cache** (Resolved domains post-disconnection)
  5. **Persistence Scheduled Tasks** (Tasks running from Temp, Public, or obfuscated scripts)

---

### D. Native Autostart Management Across 3 Pillars (`Manage-StartupItems.ps1`)

Enables native auditing and state modification across all 3 autostart pillars without relying on third-party security software (e.g. Huorong):

1. **Startup Items**: Audits `HKCU\Run`, `HKLM\Run` (32-bit & 64-bit), and Startup folders. Manipulates native Windows `StartupApproved\Run` binary flags (`0x02` Enabled, `0x03` Disabled) safely without destructive registry key deletion.
2. **System Services**: Audits Win32 service start types (`Automatic`, `Manual`, `Disabled`) and manages runtime states.
3. **Scheduled Tasks**: Audits and manages task scheduler items configured for boot or logon triggers.

```powershell
# 1. Audit all autostart items across all 3 categories (with vendor info and validity checks)
powershell -ExecutionPolicy Bypass -File .\Manage-StartupItems.ps1

# 2. Filter invalid / orphaned startup entries only
powershell -ExecutionPolicy Bypass -File .\Manage-StartupItems.ps1 -InvalidOnly

# 3. Filter by category or search by keyword
powershell -ExecutionPolicy Bypass -File .\Manage-StartupItems.ps1 -Category Startup -Search "GameViewer"
powershell -ExecutionPolicy Bypass -File .\Manage-StartupItems.ps1 -Category Service -Search "KDService"
powershell -ExecutionPolicy Bypass -File .\Manage-StartupItems.ps1 -Category Task -Search "ACC"

# 4. Modify item state (Enable / Disable)
# Disable a startup registry item (modifies StartupApproved without deleting run key)
powershell -ExecutionPolicy Bypass -File .\Manage-StartupItems.ps1 -DisableName "GameViewer" -TargetCategory Startup

# Disable a Windows service (sets startup type to Disabled and stops service)
powershell -ExecutionPolicy Bypass -File .\Manage-StartupItems.ps1 -DisableName "KDService" -TargetCategory Service

# Disable a scheduled task
powershell -ExecutionPolicy Bypass -File .\Manage-StartupItems.ps1 -DisableName "ACC" -TargetCategory Task

# Re-enable an item
powershell -ExecutionPolicy Bypass -File .\Manage-StartupItems.ps1 -EnableName "GameViewer" -TargetCategory Startup
```


