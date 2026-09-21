# Security CI Architecture

本腳手架將安全檢查分成三個生命週期：**PR Gate、Post-Merge Security、Runtime Monitoring**。每種工具在最適合的時間執行，避免把需要部署環境或長時間掃描的工作塞進 Pull Request。

## 1. 三層安全模型

```text
Pull Request
├─ policy.yml                 Hard Gate
├─ trufflehog.yml             Security Gate
├─ codeql.yml                 Soft Security Signal
├─ sbom.yml                   Artifact-only on PR
└─ pr_agent.yml               Optional Soft Review
        │
        ▼
Push / Merge to main or master
├─ sbom.yml
│   └─ Dependency-Track       Optional SBOM backend
└─ post-merge-security.yml
    ├─ Staging readiness
    ├─ ZAP                    Web DAST
    ├─ Greenbone / OpenVAS    Infrastructure scan
    ├─ DefectDojo             Findings aggregation
    ├─ Faraday                Pentest collaboration
    └─ Wazuh health check     Runtime verification
        │
        ▼
Running Environment
└─ Wazuh Agent                Continuous 24/7 monitoring
```

## 2. PR Gate

PR 階段只執行能直接對原始碼、Git 歷史或相依資訊進行檢查的工作。

| Workflow | 類型 | PR 行為 | Enforcement |
| :--- | :--- | :--- | :--- |
| `policy.yml` | Repository policy | 驗證 PR 標題與 Commit 規範 | **Hard Gate** |
| `trufflehog.yml` | Secret scanning | 掃描 verified secrets | **Security Gate** |
| `codeql.yml` | SAST | 語意與資料流分析 | **Soft Signal by default** |
| `sbom.yml` | SBOM | 產生 CycloneDX JSON Artifact | **Artifact-only** |
| `pr_agent.yml` | AI review | PR 摘要與建議 | **Optional Soft Review** |

### Policy

`policy.yml` 是合併前硬性規則。格式不符會呼叫 `core.setFailed()`，可搭配 GitHub Branch Protection / Ruleset 設為 Required Check。

### TruffleHog

PR 時優先攔截已驗證的 API Key、Token、Private Key 等機敏資訊，主要分支 Push 時再巡檢一次。

### CodeQL

CodeQL 在 PR 階段及早回報 SQL Injection、Command Injection、XSS、Path Traversal 等問題。模板目前分析步驟使用 `continue-on-error: true`，因此預設屬於軟性安全訊號。

### SBOM

PR 會產生 `sbom.cdx.json` 並保存 Artifact，但 **PR 不會上傳 Dependency-Track**。只有非 PR 的 main/master Push 才會在有設定 API 的情況下送出正式 SBOM，避免短命 PR branch 汙染正式元件庫。

## 3. Post-Merge Security

`post-merge-security.yml` 在 Push / Merge 進 `main` 或 `master` 後執行，適合需要可運行環境、網路目標或較長掃描時間的工具。

### Staging readiness 與 ZAP

若有設定 `STAGING_URL`，workflow 會最多等待 5 分鐘確認端點可連線，再執行 ZAP Baseline。ZAP 報告可送往 DefectDojo 與 Faraday。

`zap-scan.yml` 仍保留為手動 DAST，方便針對任意 Dev / Staging URL 臨時測試。

### Greenbone / OpenVAS

Greenbone 使用已建立的 `OPENVAS_TASK_ID`。CI 透過 GMP over SSH：

1. 啟動既有 Task。
2. 輪詢直到完成。
3. 匯出 XML Report。
4. 保存 GitHub Actions Artifact。
5. 可選送往 DefectDojo 與 Faraday。

OpenVAS 不放在一般 PR，因為它需要實際網路目標、掃描時間較長，而且結果代表部署環境狀態。

### Dependency-Track

`sbom.yml` 在 main/master Push 時，若已設定 `DTRACK_URL` 與 `DTRACK_API_KEY`，會上傳正式 CycloneDX SBOM。可用 `DTRACK_PROJECT_UUID` 綁定既有 Project；未指定時使用 Repository 名稱與版本資訊 auto-create。

### DefectDojo

`defectdojo-upload.yml` 是 reusable connector，本身不掃描。它使用 `/api/v2/reimport-scan/` 匯入 scanner Artifact，讓週期性掃描可沿用 Test 並處理 Findings 去重與狀態變化。

### Faraday

`faraday-upload.yml` 同樣是 reusable connector，將 ZAP、OpenVAS 等報告送進指定 workspace，供 Pentest / Red Team 人工驗證與協作。

## 4. Runtime Monitoring

Wazuh 不屬於一次性 CI scanner。部署主機或工作負載上的 Wazuh Agent 應持續 24/7 運作：

```text
Application / Host
      │
      └─ Wazuh Agent
            │
            └─ Wazuh Server / Indexer / Dashboard
```

`wazuh-health.yml` 在部署後只負責取得 Wazuh API JWT、查詢 `WAZUH_AGENT_NAME`，並確認 Agent 仍為 `active`。

## 5. 外部平台設定

| 平台 | Variables | Secrets |
| :--- | :--- | :--- |
| Dependency-Track | `DTRACK_URL`, optional `DTRACK_PROJECT_UUID` / `DTRACK_PROJECT_NAME` / `DTRACK_PROJECT_VERSION` | `DTRACK_API_KEY` |
| DefectDojo | `DEFECTDOJO_URL` | `DEFECTDOJO_API_TOKEN` |
| Staging | `STAGING_URL` | - |
| Greenbone | `OPENVAS_HOST`, `OPENVAS_TASK_ID`, optional `OPENVAS_SSH_PORT` / `OPENVAS_SSH_USERNAME` | `OPENVAS_GMP_USERNAME`, `OPENVAS_GMP_PASSWORD`, `OPENVAS_SSH_PASSWORD` |
| Faraday | `FARADAY_URL`, `FARADAY_WORKSPACE` | `FARADAY_API_TOKEN` |
| Wazuh | `WAZUH_URL`, `WAZUH_AGENT_NAME`, optional `WAZUH_TLS_INSECURE` | `WAZUH_API_USER`, `WAZUH_API_PASSWORD` |

外部平台均採 optional integration；沒有設定對應 URL / Secret 時會跳過，不要求每個使用 Scaffold 的 Repository 都部署完整安全平台。

## 6. 建議導入順序

```text
Level 1: Policy + TruffleHog + CodeQL
Level 2: + SBOM
Level 3: + Dependency-Track / DefectDojo
Level 4: + Staging ZAP / OpenVAS / Faraday
Level 5: + Wazuh Runtime Monitoring
```

## 7. PR Preview Environment

預設不在 PR 自動跑 ZAP / OpenVAS。如果專案未來會為每個 PR 建立獨立 Preview Environment，可把 ZAP 延伸為：

```text
PR
 -> Deploy Preview
 -> Wait Preview Ready
 -> ZAP against Preview URL
```

OpenVAS 仍建議保留在 merge 後或排程掃描，避免每個 PR 都產生高成本的主機與網路掃描。
