# 網域資產與 SSL/TLS 憑證自動化資安稽核工具 (Domain Cert Auditor)

[English Version](README.md)

專為組織外部攻擊面管理 (EASM, External Attack Surface Management) 與資安法規合規性設計的自動化稽核工具。能被動盤點所有外部子網域、多執行緒併發探測存活端點、即時識別過期與即將到期之 SSL/TLS 憑證、檢測自簽憑證以及未強制轉址的明文 HTTP 傳輸風險，並自動生成專業 Markdown 稽核報告。

## 核心功能

- **被動式資產盤點 (Zero-Noise Recon)**：透過 `crt.sh` 查詢憑證透明度日誌 (Certificate Transparency Logs)，零封包發送至目標主機即可被動收集歷史所有子網域。
- **支援自訂字典與清單匯入**：可直接載入既有的子網域名單，或搭配外部情資工具 (`subfinder`、`amass`) 產出的清單。
- **高效能多執行緒併發探測**：可自訂 Worker 執行緒池，同時探測數百至數千個主機的 Port 80 (HTTP) 與 Port 443 (HTTPS) 埠位狀態。
- **深度憑證生命週期檢驗**：
  - 精確計算過期天數並標註高風險。
  - 提早 14 天發出憑證即將到期之預警。
  - 智慧識別憑證簽發單位（區分 Let's Encrypt 自動化憑證、商用 OV/EV 憑證與自簽憑證）。
- **明文傳輸洩漏偵測**：識別 Port 80 監聽中且回傳 `200 OK`、未落實 301/302 強制轉址至 HTTPS 之端點（違反機敏資料加密規範）。
- **結構化 Markdown 報表生成**：自動產出包含風險儀表板、異常清單與完整資產矩陣的審計報表。

## 環境需求

- **Python 3.8+**
- **網際網路連線**（用於查詢 crt.sh 與探測遠端目標）

## 安裝方式

1. 切換至工具目錄：
   ```bash
   cd security/domain-cert-auditor
   ```

2. 安裝必要套件：
   ```bash
   pip install -r requirements.txt
   ```

## 使用方式

### 基本稽核（透過 crt.sh 被動式全面盤點）

```bash
python cert_auditor.py -d example.com
```

### 匯入既有子網域名單稽核

```bash
python cert_auditor.py -d target.edu.tw -f subdomains.txt
```

### 進階參數設定（執行緒、連線超時與自訂報表名稱）

```bash
python cert_auditor.py -d target.gov.tw -f subdomains.txt -w 50 -t 2.5 -o audit_report.md
```

## CLI 命令列參數說明

| 參數名稱 | 縮寫 | 說明 | 預設值 |
| :--- | :---: | :--- | :--- |
| `--domain` | `-d` | **(必填)** 目標主網域 (例如 `example.com`) | 無 |
| `--file` | `-f` | 包含子網域名單的文字檔路徑 (每行一個網域) | 無 |
| `--workers` | `-w` | 併發探測的 Worker 執行緒數量 | `30` |
| `--timeout` | `-t` | Socket 連線超時時間 (秒) | `3.0` |
| `--output` | `-o` | 輸出的 Markdown 稽核報告路徑 | `audit_report_<domain>.md` |
| `--no-crtsh` | - | 跳過 crt.sh 查詢 (僅稽核 `-f` 提供的網域名單) | `False` |

## 執行範例

### 控制台輸出

```text
[*] Querying crt.sh Certificate Transparency logs for example.com...
[+] Retrieved 142 unique subdomains from crt.sh
[*] Starting concurrent security audit across 142 targets (Workers: 30)...
    - Progress: 50/142 (35%)
    - Progress: 100/142 (70%)
    - Progress: 142/142 (100%)
[+] Probing complete! 87 active endpoints detected.
[*] Generating Markdown audit report: audit_report_example_com.md ...
[+] Audit report successfully saved to: audit_report_example_com.md
```

### Markdown 報表示意

產生的審計報表將包含風險摘要與詳細問題表格：

```markdown
## 風險儀表板
| 監控項目 | 異常數量 | 風險等級 | 說明 |
| :--- | :---: | :---: | :--- |
| **已過期憑證 (Expired)** | **3** | 🔴 High | 憑證已失效，使用者連線將遭瀏覽器阻斷 |
| **即將到期憑證 (<= 14 天)** | **2** | 🟡 Warning | 需立即安排續約避免服務中斷 |
| **明文傳輸風險 (未強制 HTTPS)** | **4** | 🔴 High | Port 80 回傳 200 OK 且未配置轉址 |
| **自簽憑證 (Self-Signed)** | **1** | 🟡 Warning | 未經受信任之第三方 CA 簽發 |
```

## 授權條款

本專案採用 MIT 授權條款，為 [Script-List](../../LICENSE) 專案的一部分。
