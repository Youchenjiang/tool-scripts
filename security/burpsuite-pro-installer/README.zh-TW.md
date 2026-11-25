# Burp Suite Pro 自動化安裝與維護工具箱

基於 PowerShell 的 Windows 平台 Burp Suite Professional 綠色安裝、環境配置與生命週期維護工具。

## 功能特點

- **支援綠色免安裝 OpenJDK 21**：可選下載解壓至本地 `jdk-21\`，**100% 免系統管理員權限**，隨身碟隨插即用。
- **穩健多線程斷點續傳**：優先調用 `aria2c` 16 線程續傳，具備最低檔案大小門檻校驗，防範防盜鏈與無效重定向。
- **全動態相對路徑**：`Burp.bat` 與 `Burp-Suite-Pro.vbs` 使用動態 `%~dp0` 相對路徑，任意搬移不失效。
- **JVM 記憶體與垃圾回收調優**：預設設定 `-Xms1024m -Xmx4096m -XX:+UseG1GC`，杜絕大量封包檢測時的 OOM 崩潰。
- **桌面快捷方式自動建立**：自動在 Windows 桌面建立無黑框背景啟動捷徑，綁定 `installer.ico`。
- **互動式 TUI 維護選單**：
  - 即時環境狀態儀表板（JDK、Burp JAR、Loader、捷徑）。
  - 一鍵全新安裝與環境修復。
  - 一鍵更新 PortSwigger 官方最新 JAR。
  - 自訂記憶體上限與下載暫存檔清理。

## 快速使用

1. 將 `loader.jar` 與 `aria2c.exe` 置於腳本同目錄下。
2. 雙擊執行 `install.bat`（自動以 Bypass 策略呼叫 PowerShell，免去手動輸入指令）。
3. 依選單提示輸入 `1` 進行一鍵配置並啟動。
