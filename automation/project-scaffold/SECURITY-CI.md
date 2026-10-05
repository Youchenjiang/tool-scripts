# Security CI Architecture

The scaffold organizes security automation across three lifecycle stages: **PR Gate**, **Post-Deploy Security (CD Linked)**, and **Runtime & Jitter Schedule (Periodic Audits)**, featuring strict **Actions Quota Protection** and **Hash-Based Jitter Scheduling**.

## 1. Lifecycle model

```text
Pull Request (PR Gate)
├─ policy.yml                 Hard Gate (Conventional Commits validation)
├─ trufflehog.yml             Security Gate (Verified secret detection)
├─ codeql.yml                 Soft Security Signal (SAST data-flow analysis)
├─ sbom.yml                   Artifact-only on PR (CycloneDX SBOM generation)
└─ pr_agent.yml               Optional Soft Review (AI code review)
        │
        ▼
Push / Merge to main / master ➔ Continuous Deployment (Deploy to Staging)
        │
        ▼ (workflow_run: triggered after successful CD deployment)
Post-Deploy Security Validation
├─ nuclei-scan.yml            Ultra-fast DAST (30~60s, targeted CVE scan, SARIF output)
├─ sbom.yml                   Uploads to Dependency-Track (Official SBOM)
└─ post-merge-security.yml     (Optional, Feature: sec-enterprise)
    ├─ Staging readiness      (Fast reachability probe; exits in seconds if unset)
    ├─ ZAP                    (Web DAST baseline scan)
    ├─ Greenbone / OpenVAS    (Bounded polling to prevent runner exhaustion)
    ├─ DefectDojo             (Findings deduplication and aggregation)
    ├─ Faraday                (Pentest collaboration workspace)
    └─ Wazuh health check     (Runtime agent verification)
        │
        ▼
Runtime & Periodic Audits (Jitter Schedule)
├─ Wazuh Agent                (Host-level 24/7 continuous monitoring)
├─ nuclei-scan.yml            (Hash-based jitter: monthly off-peak CVE audit)
└─ codeql.yml                 (Hash-based jitter: weekly off-peak full SAST)
```

## 2. PR Gate

| Workflow | Purpose | PR behavior | Enforcement | Typical Duration |
| :--- | :--- | :--- | :--- | :---: |
| `policy.yml` | Repository policy | Validate PR title, commits, and PR body structure | **Hard Gate** | ~15s |
| `trufflehog.yml` | Secret scanning | Intercept verified tokens and credentials | **Security Gate** | ~30s |
| `codeql.yml` | SAST | AST semantic and data-flow analysis | **Soft Signal** | 3~8m |
| `sbom.yml` | SBOM | Generate CycloneDX JSON artifact (no upload) | **Artifact-only** | ~1m |
| `pr_agent.yml` | AI review | Automated review suggestions | **Optional** | 1~2m |

## 3. Post-Deploy Security (CD Linked)

Direct execution on `push` previously caused race conditions, outdated target scans, and premature timeout failures during container redeployments.

The architecture now adopts **Decoupled CD Linking (Option A)**:
* Listens to CD workflows (`Deploy to Staging`, `Deploy`, `CD`) via `workflow_run`.
* Runs **only after the CD pipeline succeeds**, guaranteeing the target environment is live and running current code.

### Quota Protection (Zero-Waste Guard)
To prevent private repositories from exhausting the 2,000 ~ 3,000 monthly free runner minutes:
1. **Pre-flight Variable Guard**: If `STAGING_URL` or `SCAN_TARGET_URL` is unconfigured, workflows exit in 2 seconds without starting compute-intensive steps.
2. **OpenVAS Polling Limit**: Caps polling at 20 minutes (down from 60+ minutes), eliminating runner starvation.
3. **Nuclei Default**: Uses **Nuclei** for routine post-deploy audits (runs in ~40 seconds, saving >90% of runner quota over full ZAP crawls).

## 4. Hash-Based Jitter Scheduling

Hardcoded cron schedules (e.g. `0 0 1 * *`) cause **Self-DDoS**, target server saturation, and GitHub Actions concurrency bottlenecks across multiple repositories.

`init-project.ps1` hashes the project name during initialization to generate a unique, non-overlapping cron schedule:
* **Monthly Audits (Nuclei)**: Distributed between **Days 1 to 28**, during off-peak **UTC 01:00 ~ 04:00**, with randomized minutes (0..58).
* **Weekly Audits (CodeQL)**: Distributed across **Days of the week (Sun..Sat)** during off-peak hours.

### Example Distribution:
* `Clickra` ➔ `17 2 4 * *` (Monthly, Day 4 at 02:17 UTC)
* `Youchen` ➔ `42 3 11 * *` (Monthly, Day 11 at 03:42 UTC)
* `Wildwatch` ➔ `09 1 19 * *` (Monthly, Day 19 at 01:09 UTC)

## 5. External Platform Configurations

| Platform | Variables | Secrets | Notes |
| :--- | :--- | :--- | :--- |
| **Scan Targets** | `STAGING_URL`, `SCAN_TARGET_URL` | - | Target endpoints for DAST/Nuclei (skipped if unset) |
| **Dependency-Track** | `DTRACK_URL`, `DTRACK_PROJECT_UUID` | `DTRACK_API_KEY` | Component tracking repository |
| **DefectDojo** | `DEFECTDOJO_URL` | `DEFECTDOJO_API_TOKEN` | Centralized vulnerability management |
| **Faraday** | `FARADAY_URL`, `FARADAY_WORKSPACE` | `FARADAY_API_TOKEN` | Penetration test collaboration |
| **Greenbone / OpenVAS** | `OPENVAS_HOST`, `OPENVAS_TASK_ID`, `OPENVAS_SSH_PORT` | `OPENVAS_GMP_USERNAME`, `OPENVAS_GMP_PASSWORD`, `OPENVAS_SSH_PASSWORD` | Infrastructure vulnerability scans |
| **Wazuh** | `WAZUH_URL`, `WAZUH_AGENT_NAME` | `WAZUH_API_USER`, `WAZUH_API_PASSWORD` | Runtime agent health and alerts |
