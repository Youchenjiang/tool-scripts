# Security CI Architecture

本腳手架將安全檢查分成三個生命週期：**PR Gate、Post-Deploy Security（CD 連動）、Runtime & Jitter Schedule（週期性巡檢）**。每種工具在最適合的時間執行，避免把需要部署環境或長時間掃描的工作塞進 Pull Request，並具備嚴格的 **Actions 配額保護 (Quota Protection)** 與 **動態錯峰機制 (Hash-based Jitter)**。

## 1. 三層安全模型

```text
Pull Request (PR Gate)
├─ policy.yml                 Hard Gate (Conventional Commits 規範)
├─ trufflehog.yml             Security Gate (密鑰防外洩)
├─ codeql.yml                 Soft Security Signal (SAST 資料流分析)
├─ sbom.yml                   Artifact-only on PR (元件清單生成)
└─ pr_agent.yml               Optional Soft Review (AI 代碼審查)
        │
        ▼
Push / Merge to main / master ➔ CD 部署流程 (Deploy to Staging)
        │
        ▼ (workflow_run: 部署成功後觸發，解耦不打架)
Post-Deploy Security Validation
├─ nuclei-scan.yml            極速 DAST (30~60秒，特徵巡檢，SARIF 輸出)
├─ sbom.yml                   上傳 Dependency-Track (正式 SBOM)
└─ post-merge-security.yml     (可選，Features: sec-enterprise)
    ├─ Staging readiness      (輕量探測，未設定則秒退 0 消耗)
    ├─ ZAP                    (Web DAST 基準掃描)
    ├─ Greenbone / OpenVAS    (限時輪詢，防止耗盡 Actions 額度)
    ├─ DefectDojo             (Findings 去重匯總)
    ├─ Faraday                (滲透測試協作)
    └─ Wazuh health check     (Agent 健康度確認)
        │
        ▼
Runtime & 週期性巡檢 (Jitter Schedule)
├─ Wazuh Agent                (主機端 24/7 持續監控)
├─ nuclei-scan.yml            (動態錯峰：每月專屬日期凌晨巡檢最新 CVE)
└─ codeql.yml                 (動態錯峰：每週專屬工作日凌晨全量 SAST)
```

## 2. PR Gate (合併前看門狗)

PR 階段只執行能直接對原始碼、Git 歷史或相依資訊進行檢查的輕量工作。

| Workflow | 類型 | PR 行為 | Enforcement | 平均耗時 |
| :--- | :--- | :--- | :--- | :---: |
| `policy.yml` | Repository policy | 驗證 PR 標題、Commit 格式與 PR Body 結構 | **Hard Gate** | ~15 秒 |
| `trufflehog.yml` | Secret scanning | 攔截已驗證的 API Key、Token、私鑰 | **Security Gate** | ~30 秒 |
| `codeql.yml` | SAST | 語意與資料流分析 (continue-on-error) | **Soft Signal** | 3~8 分鐘 |
| `sbom.yml` | SBOM | 產生 CycloneDX JSON Artifact (PR 不上傳) | **Artifact-only** | ~1 分鐘 |
| `pr_agent.yml` | AI review | PR 摘要與建議 (可選) | **Optional** | 1~2 分鐘 |

## 3. Post-Deploy Security (CD 部署後連動)

過去「Merge 當下立刻執行安全掃描」存在**掃描到舊版本**、**伺服器重啟中斷**以及**等待超時**等時序競態（Race Condition）。

本架構全面改採 **CD 解耦連動方案（方案 A）**：
* 透過 GitHub Actions `workflow_run`，監聽 CD 工作流（如 `Deploy to Staging`、`Deploy`、`CD`）。
* **只有在 CD 成功發布後才啟動安全驗證**，保證受測目標為最新版本。

### 零額度浪費保護 (Zero-Waste Guard)
為避免私有倉庫每月的 GitHub Actions 免費分鐘數（2,000 ~ 3,000 分鐘）被無端耗盡：
1. **變數前置檢驗**：若專案未設定 `STAGING_URL` 或 `SCAN_TARGET_URL`，工作流在 3 秒內自動結束，**不啟動任何大型 Runner，消耗為 0**。
2. **OpenVAS 輪詢限縮**：輪詢時間嚴格限制在 20 分鐘以內，杜絕 Runner 長時間 `sleep` 空等 1 小時的額度黑洞。
3. **輕量化替換 (Nuclei)**：常態部署後優先採用 **Nuclei**（執行僅 30~60 秒，節省 90% 以上時間與資源）。

## 4. 動態錯峰排程機制 (Hash-based Jitter Cron)

若數十個專案在模板中寫死相同排程時間（如每週一 00:00），會引發**自我拒絕服務 (Self-DDoS)**、打垮測試伺服器與擠爆 GitHub 並發上限。

腳手架 `init-project.ps1` 在初始化專案時，會**依據專案名稱計算雜湊值 (Hash)**，動態生成專屬錯開的 Cron 時間：

* **月度排程 (如 Nuclei CVE 巡檢)**：
  * 自動分散於每月的 **1 ~ 28 號**（避開大小月差異）。
  * 執行時間分散於夜間離峰期 **UTC 01:00 ~ 04:00**，並搭配隨機分鐘（0 ~ 58 分）。
* **週度排程 (如 CodeQL SAST)**：
  * 自動分散於每週的 **週日 ~ 週六**，搭配夜間離峰時段。

### 範例效果：
* 專案 `Clickra` ➔ 自動配置：`17 2 4 * *`（每月 4 號 02:17）
* 專案 `Youchen` ➔ 自動配置：`42 3 11 * *`（每月 11 號 03:42）
* 專案 `Wildwatch` ➔ 自動配置：`09 1 19 * *`（每月 19 號 01:09）

## 5. 外部平台設定

| 平台 | Variables | Secrets | 說明 |
| :--- | :--- | :--- | :--- |
| **目標站點** | `STAGING_URL`, `SCAN_TARGET_URL` | - | DAST 與 Nuclei 掃描目標（未配置則自動跳過） |
| **Dependency-Track** | `DTRACK_URL`, `DTRACK_PROJECT_UUID` | `DTRACK_API_KEY` | 正式 SBOM 元件庫儲存 |
| **DefectDojo** | `DEFECTDOJO_URL` | `DEFECTDOJO_API_TOKEN` | 弱點報告統一聚合與追蹤 |
| **Faraday** | `FARADAY_URL`, `FARADAY_WORKSPACE` | `FARADAY_API_TOKEN` | 滲透測試協作工作區 |
| **Greenbone / OpenVAS** | `OPENVAS_HOST`, `OPENVAS_TASK_ID`, `OPENVAS_SSH_PORT` | `OPENVAS_GMP_USERNAME`, `OPENVAS_GMP_PASSWORD`, `OPENVAS_SSH_PASSWORD` | 基礎設施定期掃描 |
| **Wazuh** | `WAZUH_URL`, `WAZUH_AGENT_NAME` | `WAZUH_API_USER`, `WAZUH_API_PASSWORD` | 運行時 24/7 Agent 監控 |

> 所有外部平台均為 **可選掛載 (Optional)**。無配置時工作流安全略過，不影響專案建置與發布。
