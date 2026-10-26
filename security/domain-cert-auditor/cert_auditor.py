#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Domain Certificate & Attack Surface Auditor (網域資產與憑證安全稽核工具)
----------------------------------------------------------------------
Features:
- Passive subdomain enumeration via crt.sh (Certificate Transparency logs)
- Multi-threaded concurrent port & TLS probing (80 HTTP & 443 HTTPS)
- Certificate lifecycle analysis (expiration detection, days remaining, DV/OV/EV/Self-signed classification)
- Plaintext transmission detection (checks whether HTTP port 80 enforces 301/302 HTTPS redirection)
- Automated Markdown risk & audit report generation
"""

import sys
import os
import argparse
import socket
import ssl
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from cryptography import x509
except ImportError:
    print("[!] Missing required package: cryptography. Please install with: pip install cryptography")
    sys.exit(1)


class CertAuditor:
    def __init__(self, target_domain, workers=30, timeout=3.0, output_file=None):
        self.domain = target_domain.strip().lower()
        self.workers = workers
        self.timeout = timeout
        self.output_file = output_file or f"audit_report_{self.domain.replace('.', '_')}.md"
        self.subdomains = set()
        self.results = []

    def fetch_subdomains_crtsh(self):
        """Fetch historical subdomains from crt.sh Certificate Transparency logs."""
        print(f"[*] Querying crt.sh Certificate Transparency logs for {self.domain}...")
        url = f"https://crt.sh/?q=%25.{urllib.parse.quote(self.domain)}&output=json"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                for item in data:
                    name_val = item.get("name_value", "")
                    for name in name_val.split("\n"):
                        name = name.strip().lower()
                        if name.endswith(self.domain) and "*" not in name:
                            self.subdomains.add(name)
            print(f"[+] Retrieved {len(self.subdomains)} unique subdomains from crt.sh")
        except Exception as e:
            print(f"[-] crt.sh query timed out or failed ({e}). Using existing list or primary domain.")

    def load_subdomains_from_file(self, filepath):
        """Load subdomains from an existing text file."""
        if not os.path.exists(filepath):
            print(f"[-] File not found: {filepath}")
            return
        print(f"[*] Loading subdomains from file: {filepath}")
        count = 0
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                d = line.strip().lower()
                if d and d.endswith(self.domain):
                    self.subdomains.add(d)
                    count += 1
        print(f"[+] Loaded {count} subdomains from file")

    def probe_host(self, domain):
        """Probe a single host for HTTP redirection and TLS certificate status."""
        host_info = {
            "domain": domain,
            "ip": None,
            "port_80": False,
            "port_443": False,
            "http_status": None,
            "http_redirects_to_https": False,
            "tls_expired": None,
            "tls_not_before": None,
            "tls_not_after": None,
            "days_left": None,
            "issuer": None,
            "subject": None,
            "cert_type": "Unknown",
            "is_self_signed": False,
            "error": None
        }

        # 1. DNS Resolution
        try:
            ip = socket.gethostbyname(domain)
            host_info["ip"] = ip
        except socket.gaierror:
            host_info["error"] = "DNS Resolution Failed"
            return host_info
        except Exception as e:
            host_info["error"] = str(e)
            return host_info

        # 2. Port 80 (HTTP) Redirection Probe
        try:
            with socket.create_connection((domain, 80), timeout=self.timeout) as s:
                host_info["port_80"] = True
                req = f"HEAD / HTTP/1.1\r\nHost: {domain}\r\nUser-Agent: CertAuditor/1.0\r\nConnection: close\r\n\r\n"
                s.sendall(req.encode("ascii"))
                s.settimeout(self.timeout)
                resp = s.recv(1024).decode("utf-8", errors="ignore")
                if resp:
                    lines = resp.split("\r\n")
                    if lines and len(lines[0].split()) >= 2:
                        host_info["http_status"] = lines[0].split()[1]
                    for line in lines:
                        if line.lower().startswith("location:"):
                            loc = line.split(":", 1)[1].strip()
                            if loc.lower().startswith("https://"):
                                host_info["http_redirects_to_https"] = True
                            break
        except Exception:
            pass

        # 3. Port 443 (HTTPS) & TLS Certificate Analysis
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with socket.create_connection((domain, 443), timeout=self.timeout) as sock:
                host_info["port_443"] = True
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    der = ssock.getpeercert(binary_form=True)
                    cert = x509.load_der_x509_certificate(der)

                    now = datetime.now(timezone.utc)
                    not_before = getattr(cert, "not_valid_before_utc", None) or cert.not_valid_before.replace(tzinfo=timezone.utc)
                    not_after = getattr(cert, "not_valid_after_utc", None) or cert.not_valid_after.replace(tzinfo=timezone.utc)

                    host_info["tls_not_before"] = str(not_before)
                    host_info["tls_not_after"] = str(not_after)
                    host_info["days_left"] = (not_after - now).days
                    host_info["tls_expired"] = now > not_after

                    issuer_str = cert.issuer.rfc4514_string()
                    subject_str = cert.subject.rfc4514_string()
                    host_info["issuer"] = issuer_str
                    host_info["subject"] = subject_str

                    if cert.issuer == cert.subject or "localhost" in issuer_str.lower():
                        host_info["is_self_signed"] = True
                        host_info["cert_type"] = "Self-Signed"
                    elif "Let's Encrypt" in issuer_str:
                        host_info["cert_type"] = "Let's Encrypt (Free DV)"
                    elif "O=" in issuer_str and "C=" in issuer_str:
                        host_info["cert_type"] = "Commercial/OV"
                    else:
                        host_info["cert_type"] = "Standard CA"

        except Exception as e:
            if not host_info["error"]:
                host_info["error"] = f"HTTPS Connection Failed ({type(e).__name__})"

        return host_info

    def run_audit(self):
        """Run multi-threaded audit against all discovered targets."""
        targets = sorted(list(self.subdomains))
        if not targets:
            targets = [self.domain]

        print(f"[*] Starting concurrent security audit across {len(targets)} targets (Workers: {self.workers})...")
        completed = 0
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_dom = {executor.submit(self.probe_host, dom): dom for dom in targets}
            for future in as_completed(future_to_dom):
                res = future.result()
                if res and (res["port_80"] or res["port_443"] or res["ip"]):
                    self.results.append(res)
                completed += 1
                if completed % 50 == 0 or completed == len(targets):
                    print(f"    - Progress: {completed}/{len(targets)} ({completed*100//len(targets)}%)")

        print(f"[+] Probing complete! {len(self.results)} active endpoints detected.")
        self.generate_report()

    def generate_report(self):
        """Generate a structured Markdown audit report."""
        print(f"[*] Generating Markdown audit report: {self.output_file} ...")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        total_alive = len(self.results)
        https_alive = [r for r in self.results if r["port_443"] and r["tls_not_after"]]
        expired = [r for r in https_alive if r["tls_expired"]]
        expiring_soon = [r for r in https_alive if not r["tls_expired"] and r["days_left"] <= 14]
        le_certs = [r for r in https_alive if "Let's Encrypt" in str(r["issuer"])]
        self_signed = [r for r in https_alive if r["is_self_signed"]]
        no_redirect = [r for r in self.results if r["port_80"] and not r["http_redirects_to_https"] and r["http_status"] == "200"]

        md = []
        md.append(f"# Domain Certificate & Attack Surface Audit Report ({self.domain})")
        md.append(f"* **Audit Date**: `{now_str}`")
        md.append(f"* **Target Domain**: `{self.domain}`")
        md.append(f"* **Total Endpoints Probed**: {len(self.subdomains)} | **Active Servers**: {total_alive}\n")

        md.append("## Risk Dashboard\n")
        md.append("| Metric | Count | Severity | Description |")
        md.append("| :--- | :---: | :---: | :--- |")
        md.append(f"| **Expired Certificates** | **{len(expired)}** | 🔴 High | Certificate has expired; clients blocked by security warnings |")
        md.append(f"| **Expiring Soon (<= 14 Days)** | **{len(expiring_soon)}** | 🟡 Warning | Requires immediate renewal to prevent service interruption |")
        md.append(f"| **Plaintext HTTP (No HTTPS Redirect)** | **{len(no_redirect)}** | 🔴 High | Port 80 serves 200 OK without redirecting to HTTPS |")
        md.append(f"| **Self-Signed Certificates** | **{len(self_signed)}** | 🟡 Warning | Untrusted root CA; prone to MitM and compliance violations |")
        md.append(f"| **Let's Encrypt (DV) Usage** | **{len(le_certs)}** | 🔵 Info | Short 90-day validity; represents {len(le_certs)*100//max(1, len(https_alive))}% of HTTPS endpoints |")
        md.append("")

        if expired:
            md.append("## 🚨 Expired Certificates\n")
            md.append("| Domain | Expiration (UTC) | Days Expired | Type | IP Address |")
            md.append("| :--- | :--- | :---: | :--- | :--- |")
            for r in sorted(expired, key=lambda x: x["days_left"]):
                days_ago = -r["days_left"]
                md.append(f"| `{r['domain']}` | `{r['tls_not_after']}` | **Expired {days_ago} days ago** | {r['cert_type']} | `{r['ip']}` |")
            md.append("")

        if expiring_soon:
            md.append("## ⚠️ Expiring Soon (Within 14 Days)\n")
            md.append("| Domain | Expiration (UTC) | Days Remaining | Type | IP Address |")
            md.append("| :--- | :--- | :---: | :--- | :--- |")
            for r in sorted(expiring_soon, key=lambda x: x["days_left"]):
                md.append(f"| `{r['domain']}` | `{r['tls_not_after']}` | Only {r['days_left']} days left | {r['cert_type']} | `{r['ip']}` |")
            md.append("")

        if no_redirect:
            md.append("## 🔓 Plaintext HTTP Endpoints (Missing HTTPS Redirection)\n")
            md.append("| Domain | Port 80 Status | Port 443 Status | Impact |")
            md.append("| :--- | :---: | :---: | :--- |")
            for r in no_redirect:
                p443 = "Open" if r["port_443"] else "Closed"
                md.append(f"| `{r['domain']}` | HTTP {r['http_status']} | {p443} | Credentials transmitted in cleartext; configure 301 redirect to HTTPS |")
            md.append("")

        md.append("## 📋 Complete Asset Inventory & TLS Status\n")
        md.append("| Domain | IP | TLS Status | Days Remaining/Expired | Type | Issuer |")
        md.append("| :--- | :--- | :---: | :---: | :--- | :--- |")
        for r in sorted(self.results, key=lambda x: x["domain"]):
            if r["tls_not_after"]:
                status = "🔴 Expired" if r["tls_expired"] else "🟢 Valid"
                days = f"{r['days_left']}d"
                ctype = r["cert_type"]
                issuer = r["issuer"].split(",")[0] if r["issuer"] else "-"
            else:
                status = "⚪ No TLS"
                days = "-"
                ctype = "-"
                issuer = "-"
            md.append(f"| `{r['domain']}` | `{r['ip']}` | {status} | {days} | {ctype} | {issuer} |")

        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(md))

        print(f"[+] Audit report successfully saved to: {self.output_file}")


def main():
    parser = argparse.ArgumentParser(description="Automated Domain Asset & SSL/TLS Certificate Security Auditor")
    parser.add_argument("-d", "--domain", required=True, help="Target root domain (e.g. example.com or ncu.edu.tw)")
    parser.add_argument("-f", "--file", help="Path to existing subdomain list text file (optional)")
    parser.add_argument("-w", "--workers", type=int, default=30, help="Concurrent worker threads (default: 30)")
    parser.add_argument("-t", "--timeout", type=float, default=3.0, help="Socket connection timeout in seconds (default: 3.0)")
    parser.add_argument("-o", "--output", help="Output Markdown report filename")
    parser.add_argument("--no-crtsh", action="store_true", help="Skip crt.sh online querying")

    args = parser.parse_args()

    auditor = CertAuditor(
        target_domain=args.domain,
        workers=args.workers,
        timeout=args.timeout,
        output_file=args.output
    )

    if args.file:
        auditor.load_subdomains_from_file(args.file)

    if not args.no_crtsh:
        auditor.fetch_subdomains_crtsh()

    auditor.run_audit()


if __name__ == "__main__":
    main()
