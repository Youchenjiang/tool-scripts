# Domain Certificate & Attack Surface Auditor

[中文版本 (Traditional Chinese)](README.zh-TW.md)

An automated security audit and external attack surface management (EASM) tool designed to inventory external subdomains, detect expired or expiring SSL/TLS certificates, identify self-signed certificates, and flag unencrypted plaintext HTTP transmissions.

## Features

- **Passive Asset Discovery**: Queries Certificate Transparency (CT) logs via `crt.sh` to extract all historical subdomains with zero network packet noise towards the target.
- **Custom List Support**: Accepts custom subdomain wordlists or outputs from external reconnaissance tools (e.g. `subfinder`, `amass`).
- **High-Performance Multi-Threading**: Concurrently probes ports 80 (HTTP) and 443 (HTTPS) across hundreds or thousands of hosts with configurable thread pools.
- **Deep Certificate Lifecycle Inspection**:
  - Flags expired certificates and calculates days overdue.
  - Generates early warnings for certificates expiring within 14 days.
  - Distinguishes between Let's Encrypt (DV), commercial (OV/EV), and self-signed certificates.
- **Plaintext HTTP Leak Detection**: Identifies web servers listening on port 80 that return `200 OK` without enforcing 301/302 redirection to HTTPS.
- **Automated Markdown Reporting**: Generates a structured executive audit report with risk dashboards, issue breakdowns, and a full asset inventory.

## Prerequisites

- **Python 3.8+**
- **Internet connection** (for crt.sh and remote host probing)

## Installation

1. Navigate to the tool directory:
   ```bash
   cd security/domain-cert-auditor
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Audit (Passive Discovery via crt.sh)

```bash
python cert_auditor.py -d example.com
```

### Audit with an Existing Subdomain List

```bash
python cert_auditor.py -d target.edu.tw -f subdomains.txt
```

### Advanced Options (Workers, Timeout & Output)

```bash
python cert_auditor.py -d target.gov.tw -f subdomains.txt -w 50 -t 2.5 -o audit_report.md
```

## CLI Options

| Option | Flag | Description | Default |
| :--- | :---: | :--- | :--- |
| `--domain` | `-d` | **(Required)** Target root domain (e.g. `example.com`) | None |
| `--file` | `-f` | Path to text file containing subdomains to audit | None |
| `--workers` | `-w` | Concurrent worker threads | `30` |
| `--timeout` | `-t` | Socket connection timeout in seconds | `3.0` |
| `--output` | `-o` | Output Markdown report file path | `audit_report_<domain>.md` |
| `--no-crtsh` | - | Skip crt.sh query (audit only domains from `-f`) | `False` |

## Example Output

### Console Execution

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

### Markdown Report Preview

The generated report contains an executive risk summary and structured issue tables:

```markdown
## Risk Dashboard
| Metric | Count | Severity | Description |
| :--- | :---: | :---: | :--- |
| **Expired Certificates** | **3** | 🔴 High | Certificate has expired; clients blocked |
| **Expiring Soon (<= 14 Days)** | **2** | 🟡 Warning | Requires immediate renewal |
| **Plaintext HTTP (No HTTPS Redirect)** | **4** | 🔴 High | Port 80 serves 200 OK without redirect |
| **Self-Signed Certificates** | **1** | 🟡 Warning | Untrusted root CA |
```

## License

This project is licensed under the MIT License as part of the [Script-List](../../LICENSE) repository.
