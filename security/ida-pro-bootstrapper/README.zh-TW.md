# IDA Pro 9.1 自動化配置與維護工具箱

基於 PowerShell 的 Windows 平台 IDA Professional 9.1 本地環境隔離、IDAPython、idalib、外掛與授權一鍵全自動配置與維護工具。

---

## 🏗️ 系統架構圖 (Architecture Overview)

工具箱採用本地隔離 `.conda` 規範，將 Python 3.11 與所有相依性完全封裝於 IDA 安裝目錄下：

```mermaid
flowchart TD
    User(["使用者操作\n(桌面捷徑 / Win 鍵搜尋 'ida')"]) --> Launcher["ida.exe\n(IDA Pro 9.1 主程式)"]

    subgraph IDA_Core ["IDA Professional 9.1 核心架構"]
        IDA_GUI["IDA GUI / Engine\n(ida.dll / ida32.dll - 已套用 RSA 模組補丁)"]
        Lic["idapro.hexlic\n(全反編譯器架構解鎖: x86/ARM/MIPS/PPC/RV64)"]
        IDA_GUI --> Lic
    end

    Launcher --> IDA_Core

    subgraph Local_Env [".conda 本地隔離環境 (Python 3.11)"]
        PyEnv["python.exe / python311.dll\n(完全獨立於系統，零版本衝突)"]
        IdaPy["IDAPython 核心綁定\n(HKCU:\\Software\\Hex-Rays\\IDA)"]
        IdaLib["idalib (idapro Python 套件)\n(Headless 無介面自動化分析庫)"]
        FeedsDep["ida_feeds 相依套件\n(PyQt5, rpyc, requests)"]
        PyEnv --> IdaPy
        PyEnv --> IdaLib
        PyEnv --> FeedsDep
    end

    IDA_Core <-->|動態調用| Local_Env

    subgraph Plugins ["外掛與工具組"]
        Feeds["plugins/ida_feeds\n(符號特徵管理外掛)"]
        FlairConfig["config.json\n(指定真實 tools/flair 路徑)"]
        FlairTools["tools/flair\n(dumpsig, sigmake, pcf)"]
        Feeds --> FlairConfig
        FlairConfig --> FlairTools
    end

    IDA_Core --> Plugins
```

---

## 🔄 一鍵自動化配置生命週期流程 (Lifecycle Flow)

```mermaid
flowchart TD
    Start(["執行 install.bat / install.ps1"]) --> CheckIDA["自動定位 IDA Pro 9.1 安裝目錄"]
    CheckIDA --> Step1{"[1/6] 檢測本地 .conda"}
    Step1 -->|未建立| CreateConda["調用 Miniforge 建立 Python 3.11\n(目錄前綴模式: .\\.conda)"]
    Step1 -->|已就緒| Step2{"[2/6] 檢測 IDAPython"}
    CreateConda --> Step2

    Step2 --> SwitchPy["調用 idapyswitch.exe --force-path\n綁定至 .conda\\python3.dll"]
    SwitchPy --> Step3["[3/6] 安裝與啟用 idalib\n(pip install idalib/python + py-activate)"]

    Step3 --> Step4["[4/6] 安裝 ida_feeds 依賴 (PyQt5, rpyc)\n自動寫入 config.json (flair 路徑)"]

    Step4 --> Step5["[5/6] 執行 keygen3.py 授權\n自動備份原版 DLL 覆蓋模組補丁\n同步部署 idapro.hexlic 至 %APPDATA%"]

    Step5 --> Step6["[6/6] 建立桌面與開始功能表雙捷徑\n(綁定 ida.ico，按 Win 鍵搜 ida 秒開)"]

    Step6 --> Complete(["配置完成！IDA Pro 9.1 全功能激活就緒"])
```

---

## ✨ 功能特點

- **專案本地前綴隔離 (`.conda`)**：遵循 `tool-scripts` 規範，環境建立在 `IDA Professional 9.1\.conda`，徹底避免系統 Python 3.14 衝突，隨插即用。
- **IDAPython 自動對齊**：調用 `idapyswitch.exe` 精確寫入註冊表，徹底解決安裝時 `No suitable Python installations were found` 報錯。
- **Headless `idalib` 啟用**：自動建置 `idapro` wheel 並完成動態庫連線，支援在背景以 Python 批次逆向分析。
- **`ida_feeds` 與 `flair` 整合**：自動安裝 PyQt5/rpyc，自動偵測真實工具路徑並生成 `config.json`。
- **防禦性授權與補丁套用**：自動備份原版 `ida.dll` / `ida32.dll` 為 `.bak`，安全套用公鑰補丁，全開 x86/ARM/MIPS/PPC 等所有架構反編譯器。
- **開始功能表即搜即開**：自動註冊雙捷徑，按鍵盤 `Win` 鍵打 `ida` 秒開，無污染系統全域變數。
- **互動式 TUI 維護選單**：支援即時看板巡檢、一鍵修復、重新激活、重建捷徑。

---

## 🚀 快速使用

1. 將本工具箱放置於 IDA 安裝目錄下（或指定參數執行）。
2. 雙擊執行 **`install.bat`**。
3. 依選單提示輸入 **`1`** 進行一鍵全自動配置！
