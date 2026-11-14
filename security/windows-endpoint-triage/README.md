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

### 1. Basic Triage (Generates HTML Report in Current Directory)

```powershell
powershell -ExecutionPolicy Bypass -File .\ThreatHunter-Triage.ps1
```

### 2. Custom Output Directory

```powershell
powershell -ExecutionPolicy Bypass -File .\ThreatHunter-Triage.ps1 -OutputDir "C:\Forensics"
```

### 3. Terminal Only (Suppress HTML Generation)

```powershell
powershell -ExecutionPolicy Bypass -File .\ThreatHunter-Triage.ps1 -NoHtml
```
