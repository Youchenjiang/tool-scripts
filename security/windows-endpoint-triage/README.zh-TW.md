# Windows 本機端點快速應急鑑識工具 (Windows Endpoint Triage)

[English Version](README.md)

專為資安應變 (DFIR) 與藍隊威脅獵捕 (Threat Hunting) 設計的 Windows 原生端點應急鑑識腳本。無需安裝 Python 或任何第三方軟體套件，利用 Windows 內建之 PowerShell 即可在 10 秒內快速排查全網卡暴露通訊埠、活躍外聯、高 CPU 異常進程、內網穿透工具 (RAT) 與系統核心進程偽裝，並自動產生帶有風險評級的獨立 HTML 鑑識報告。

## 核心鑑識維度

- **全網卡開放監聽鑑識 (`0.0.0.0` / `::`)**：
  - 自動排除純本機內部通訊之迴環位址 (`127.0.0.1` / `::1`)，避免雜訊干擾。
  - 自動標記全球高危攻擊面通訊埠（如 RDP 3389、SMB 445、MySQL 3306、MSSQL 1433、VNC 5900 等）與非標準高埠。
- **活躍對外公網連線 (Established WAN)**：
  - 自動過濾 RFC 1918 私有區域網路 IP，即時抓取正在向外部 Public IP 建立長連線的進程與二進位檔案路徑。
- **異常執行率與資源佔用分析**：
  - 透過 1.5 秒差分採樣演算法，即時計算當前佔用 CPU 的活躍進程百分比。
  - 統計歷史累計 CPU 消耗最高與實體記憶體佔用 (Working Set) 最高的進程清單。
- **遠端控制軟體與穿透隧道偵測 (RAT / Tunnel)**：
  - 比對常見的商業遠端控制與穿透工具特徵（如 GameViewer, AnyDesk, TeamViewer, ToDesk, RustDesk, Sunlogin, Tailscale, FRP, SoftEther 等）。
- **可疑路徑執行與微軟系統進程偽裝檢查 (Masquerading)**：
  - 檢測從 `AppData\Local\Temp`、`Windows\Temp`、`Users\Public` 等高危臨時目錄執行的二進位檔案。
  - 檢測偽裝微軟核心系統名稱但未位於 `C:\Windows\System32\` 的異常進程（如 `svchost.exe`, `csrss.exe`, `lsass.exe` 等）。
- **獨立 HTML 鑑識報告自動生成**：
  - 免依賴外部 CSS 框架，自動生成帶有紅/橙/黃/綠風險標籤的完整 HTML 鑑識報告。

## 環境需求

- **Windows 10 / 11 / Server 2016+**
- **PowerShell 5.1+** (Windows 內建，無需另行安裝)
- 建議使用**系統管理員 (Administrator)** 權限執行，以取得 SYSTEM 級別受保護行程之檔案路徑與完整資訊。

## 使用方式

### A. 即時手動鑑識模式 (`ThreatHunter-Triage.ps1`)

適用於當前操作中的端點應急現場快速調查。

```powershell
# 基本掃描（自動生成 HTML 報告於當前目錄）
powershell -ExecutionPolicy Bypass -File .\ThreatHunter-Triage.ps1

# 指定報告輸出目錄
powershell -ExecutionPolicy Bypass -File .\ThreatHunter-Triage.ps1 -OutputDir "C:\Forensics"

# 僅終端輸出（不產出 HTML 檔案）
powershell -ExecutionPolicy Bypass -File .\ThreatHunter-Triage.ps1 -NoHtml
```

---

### B. 常駐守護與自動快照模式 (`Watcher-Daemon.ps1`)

使用者**不需要在發生異常當下衝過去手動按**。守護程序常駐於背景輪詢，一旦 CPU 飆高或出現穿透工具，**立即自動拍下鑑識快照**並記錄於 `triage_incidents.jsonl` 黑盒子日誌。

#### 1. 前景終端執行（附帶即時監控狀態列）

```powershell
# 以預設條件常駐監控 (CPU > 85% 且連續 2 次超標，或偵測到未知外聯穿透工具)
powershell -ExecutionPolicy Bypass -File .\Watcher-Daemon.ps1

# 自訂門檻：每 5 秒檢查一次、CPU > 80% 觸發、冷卻期 60 秒
powershell -ExecutionPolicy Bypass -File .\Watcher-Daemon.ps1 -CheckIntervalSec 5 -CpuThreshold 80 -AlertCooldownSec 60 -OutputDir "C:\Forensics"
```

#### 2. 安裝為 Windows 背景排程任務（開機/登入時自動靜默常駐）

```powershell
# 安裝並立即啟動背景排程 (需要系統管理員權限)
powershell -ExecutionPolicy Bypass -File .\Watcher-Daemon.ps1 -InstallTask -OutputDir "C:\Forensics"

# 查看排程運行狀態
powershell -ExecutionPolicy Bypass -File .\Watcher-Daemon.ps1 -StatusTask

# 停止並移除背景排程
powershell -ExecutionPolicy Bypass -File .\Watcher-Daemon.ps1 -UninstallTask
```


## 鑑識報告產出說明

掃描完成後，將在指定目錄產出格式為 `Forensic_Report_<HostName>_<Timestamp>.html` 之報告檔案，雙擊即可使用任一瀏覽器檢視：
1. **全網卡開放監聽矩陣**：列出 Port、PID、對應進程、服務推測、風險等級與實體路徑。
2. **遠端工具命中矩陣**：列出受檢電腦上的穿透軟體與所屬公司。
3. **路徑與進程偽裝警示**：高亮標註位於臨時目錄或偽冒微軟核心之程式。
4. **資源消耗排行榜**：列出累計 CPU 時間與記憶體 WorkingSet 排行。
5. **活躍公網連線清單**：列出連線外部 Public IP 的端點紀錄。
