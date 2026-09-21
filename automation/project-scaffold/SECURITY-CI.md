# Security CI Architecture

The scaffold separates security automation into three lifecycle stages: **PR Gate**, **Post-Merge Security**, and **Runtime Monitoring**.

## 1. Lifecycle model

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

| Workflow | Purpose | PR behavior | Enforcement |
| :--- | :--- | :--- | :--- |
| `policy.yml` | Repository policy | Validate PR and commit conventions | **Hard Gate** |
| `trufflehog.yml` | Secret scanning | Detect verified credentials | **Security Gate** |
| `codeql.yml` | SAST | Semantic and data-flow analysis | **Soft Signal by default** |
| `sbom.yml` | SBOM | Generate CycloneDX JSON artifact | **Artifact-only** |
| `pr_agent.yml` | AI review | Review suggestions and summaries | **Optional Soft Review** |

`policy.yml` is the explicit hard gate. CodeQL currently uses `continue-on-error: true` for the analysis step, so this scaffold treats it as a security signal unless repository rules add stronger merge protection.

PR runs of `sbom.yml` preserve the SBOM artifact but do not upload it to Dependency-Track.

## 3. Post-Merge Security

`post-merge-security.yml` runs after a push or merge to `main` / `master`.

- **ZAP** scans `STAGING_URL` after the endpoint becomes reachable.
- **Greenbone / OpenVAS** starts a preconfigured task through GMP over SSH and exports XML.
- **DefectDojo** reimports scanner artifacts for findings aggregation and deduplication.
- **Faraday** imports scanner artifacts into a pentest collaboration workspace.
- **Wazuh** is queried only to verify that the deployed runtime agent remains active.
- **Dependency-Track** receives the official CycloneDX SBOM from non-PR runs of `sbom.yml`.

`zap-scan.yml` remains available as a manual DAST workflow for arbitrary Dev or Staging URLs.

## 4. Runtime Monitoring

Wazuh is a continuously running runtime and endpoint monitoring platform, not a one-shot CI scanner. `wazuh-health.yml` authenticates to the Wazuh Server API and verifies that the configured agent remains `active`.

## 5. Configuration

| Platform | Variables | Secrets |
| :--- | :--- | :--- |
| Dependency-Track | `DTRACK_URL`, optional project variables | `DTRACK_API_KEY` |
| DefectDojo | `DEFECTDOJO_URL` | `DEFECTDOJO_API_TOKEN` |
| Staging | `STAGING_URL` | - |
| Greenbone | `OPENVAS_HOST`, `OPENVAS_TASK_ID`, optional SSH variables | GMP and SSH credentials |
| Faraday | `FARADAY_URL`, `FARADAY_WORKSPACE` | `FARADAY_API_TOKEN` |
| Wazuh | `WAZUH_URL`, `WAZUH_AGENT_NAME`, optional `WAZUH_TLS_INSECURE` | `WAZUH_API_USER`, `WAZUH_API_PASSWORD` |

All external platforms are optional integrations. Missing configuration causes the corresponding integration to skip instead of requiring every repository to deploy the full security stack.

## 6. Progressive adoption

```text
Level 1: Policy + TruffleHog + CodeQL
Level 2: + SBOM
Level 3: + Dependency-Track / DefectDojo
Level 4: + Staging ZAP / OpenVAS / Faraday
Level 5: + Wazuh Runtime Monitoring
```

## 7. PR preview environments

The default scaffold does not automatically run ZAP or OpenVAS for Pull Requests. If a project creates an isolated preview deployment for every PR, ZAP can be added after preview readiness:

```text
PR
 -> Deploy Preview
 -> Wait Preview Ready
 -> ZAP against Preview URL
```

OpenVAS should normally remain post-merge or scheduled because host and network scanning is substantially more expensive than source-level PR checks.
