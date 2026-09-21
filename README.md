# Script List - A Collection of Practical Python, Node.js and Shell Scripts

[閱讀繁體中文版](README.zh-TW.md)

[![GitHub](https://img.shields.io/badge/GitHub-Script--List-blue)](https://github.com/Youchenjiang/Script-List)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/Node.js-16+-green.svg)](https://nodejs.org/)

> A curated collection of practical Python, Node.js, and Shell scripts for everyday tasks. This is the sister project of [Method-List](https://github.com/Youchenjiang/Method-List), providing ready-to-use tools that complement the knowledge base.

## Introduction

Script List is a curated collection of practical scripts and automation tools. It serves as the companion project to Method-List:

- **[Method-List](https://github.com/Youchenjiang/Method-List)**: 📚 Technical knowledge base (documentation)
- **Script-List**: 🛠️ Practical script tools (executable programs)

**Method-List teaches you "how to do it", Script-List gives you "tools to use directly".**

## Table of Contents

- [Script List - A Collection of Practical Python, Node.js and Shell Scripts](#script-list---a-collection-of-practical-python-nodejs-and-shell-scripts)
  - [Introduction](#introduction)
  - [Table of Contents](#table-of-contents)
  - [Folder Structure](#folder-structure)
  - [🛠️ Available Tools](#️-available-tools)
    - [🤖 AI & LLM](#-ai--llm)
    - [⚙️ Automation](#️-automation)
    - [📊 Data & Verification](#-data--verification)
    - [📁 Media & Documents](#-media--documents)
    - [🛡️ Security](#️-security)
    - [📝 Text & Encoding](#-text--encoding)
  - [🚀 Quick Start](#-quick-start)
  - [Usage Guidelines](#usage-guidelines)
  - [🤝 Contributing](#-contributing)
  - [📜 License](#-license)
  - [🔗 Related Projects](#-related-projects)
  - [👤 Author](#-author)
  - [⭐ Show Your Support](#-show-your-support)

## Folder Structure

```
Script-List/
├── README.md
├── README.zh-TW.md
├── LICENSE
├── .gitignore
├── ai/                         # Artificial Intelligence & LLM tools
│   ├── openai-chat-cli/        # OpenAI Chat CLI with custom personas
│   └── A2-Reproduction/        # Agentic Android Analysis reproduction
├── automation/                 # Workflow & GUI automation
│   ├── code-split/             # Codebase text splitting utility
│   ├── discord-news-bot/       # Scheduled Discord news notification bot
│   ├── tapster/                # Lightweight input automation utility (typer, key hold, clicker)
│   ├── sync-github-stars/      # GitHub Star Lists Sync Utility
│   ├── url-health-checker/     # Concurrent URL availability and HTTP status checker
│   ├── bannerlord-mod-checker/ # Mount & Blade II Bannerlord localization checker
│   └── project-scaffold/       # Project scaffolding and engineering standard initializer
├── data/                       # Data verification & extraction
│   ├── homework-submission-analyzer/ # Homework submission analysis utility
│   └── image-text-verifier/    # Questionnaire image to CSV verification tool
├── media/                      # Media & Document converters
│   ├── aac-to-mp3/             # AAC/M4A to MP3 batch audio converter
│   ├── hyread-scraper/         # HyRead eBook text scraper & converter
│   ├── image-downloader-pdf/   # Web image downloader and PDF merger
│   ├── image-to-pdf/           # Simple image to PDF converter
│   ├── mhtml-to-pdf/           # MHTML to PDF converter (Google Slides)
│   ├── pdf-merger/             # PDF file merging utility
│   ├── pdf-to-markdown/        # PDF text and metadata to Markdown extractor
│   ├── photo-splitter/         # Student photo extraction/splitting tool
│   └── ppt-to-pdf/             # PowerPoint to PDF converter
├── security/                   # Security & Analysis tools
│   ├── android-intent-dast-suite/ # Android Intent Redirection DAST scanner & testbed suite
│   ├── password-security-checker/ # HIBP breach and strength checker
│   ├── pdf-password-cracker/   # High-performance PDF password recovery & crypto tool
│   ├── frida-apk-tool/         # Android APK patching with Frida hooks
│   ├── cybersec-slide-downloader/ # CYBERSEC 2026 slide downloader
│   ├── hacker-news-scraper/    # The Hacker News 3-week article scraper & digest builder
│   ├── local-https-cert-helper/ # Local HTTPS self-signed certificate helper
│   └── cylab-challenge-exporter/ # CyLab Security Academy challenge exporter & checklist generator
└── text/                       # Text transformation & encoding
    ├── markdown-toolkit/       # Markdown conversion, formatting, code extraction & TOC toolkit
    ├── text-converter-zh/      # Chinese Simplified ↔ Traditional converter
    ├── base64-converter/       # Base64 encoding/decoding utility
    └── hex-to-ascii/           # Hexadecimal to ASCII converter
```

## 🛠️ Available Tools

Practical script tools categorized by function:

### 🤖 AI & LLM
- **OpenAI Chat CLI** ([ai/openai-chat-cli/](ai/openai-chat-cli/)) - Command-line interface for OpenAI Chat API with customizable conversation styles. Features include Zhuge Liang persona, multi-language support, and history management. → [Details](ai/openai-chat-cli/README.md)
- **A2: Agentic Android Analysis** ([ai/A2-Reproduction/](ai/A2-Reproduction/)) - Reproduction of the A2 framework for automated mobile app vulnerability discovery and validation using multi-agent systems. → [Details](ai/A2-Reproduction/README.md)

### ⚙️ Automation
- **Code Split Utility** ([automation/code-split/](automation/code-split/)) - A tool to filter, chunk, and split large codebase files into smaller text files for context window-limited AI models. → [Details](automation/code-split/README.md)
- **Discord News Bot** ([automation/discord-news-bot/](automation/discord-news-bot/)) - Periodically fetch The Hacker News and push unseen articles to a Discord channel, with persistent deduplication, configurable scheduling, embeds, and slash commands. → [Details](automation/discord-news-bot/README.md)
- **Tapster (Input Automation Helper)** ([automation/tapster/](automation/tapster/)) - Lightweight input automation utility supporting auto typing, key holding, mouse auto-clicking, and macro replay with GUI & CLI. → [Details](automation/tapster/README.md)
- **GitHub Star Lists Sync Utility** ([automation/sync-github-stars/](automation/sync-github-stars/)) - Synchronize starred repositories into custom categorized GitHub Star Lists based on Markdown headings. → [Details](automation/sync-github-stars/README.md)
- **URL Health Checker** ([automation/url-health-checker/](automation/url-health-checker/)) - High-performance concurrent URL availability and HTTP status verification in Python & PowerShell. → [Details](automation/url-health-checker/README.md)
- **Bannerlord Mod Localization Checker** ([automation/bannerlord-mod-checker/](automation/bannerlord-mod-checker/)) - Inspect localization status across all Mount & Blade II game modules. → [Details](automation/bannerlord-mod-checker/README.md)
- **Project Scaffolding System** ([automation/project-scaffold/](automation/project-scaffold/)) - Automated engineering standards, git hooks, and three-stage security CI covering PR gates, post-merge validation, SBOM, DefectDojo, Dependency-Track, Greenbone, Faraday, and Wazuh. → [Details](automation/project-scaffold/README.md) · [Security CI](automation/project-scaffold/SECURITY-CI.md)

### 📊 Data & Verification
- **Homework Submission Analyzer** ([data/homework-submission-analyzer/](data/homework-submission-analyzer/)) - A Node.js utility for eeclass assignments that automatically parses PDF certificates, matches names, and generates a CSV report. → [Details](data/homework-submission-analyzer/README.md)
- **Image-Text Verifier** ([data/image-text-verifier/](data/image-text-verifier/)) - Extract answers from scanned questionnaire images and automatically verify/fix them against an existing CSV dataset with targeted risk management. → [Details](data/image-text-verifier/README.md)

### 📁 Media & Documents
- **AAC to MP3 Converter** ([media/aac-to-mp3/](media/aac-to-mp3/)) - High-performance multithreaded audio converter to batch convert AAC, M4A, and ADTS audio files into high-quality MP3s with metadata preservation. → [Details](media/aac-to-mp3/README.md)
- **HyRead eBook Scraper** ([media/hyread-scraper/](media/hyread-scraper/)) - Extract text content from HyRead eBook platform via Chrome DevTools Protocol (CDP) iframe piercing and convert to Markdown. → [Details](media/hyread-scraper/README.md)
- **Image Downloader & PDF Converter** ([media/image-downloader-pdf/](media/image-downloader-pdf/)) - Batch download web images and automatically merge them into a PDF document. Supports smart sorting. → [Details](media/image-downloader-pdf/README.md)
- **MHTML to PDF Converter** ([media/mhtml-to-pdf/](media/mhtml-to-pdf/)) - Convert Google Slides MHTML exports into zero-whitespace 16:9 PDFs. Features GUI file picker and offline mode. → [Details](media/mhtml-to-pdf/README.md)
- **PDF Merger** ([media/pdf-merger/](media/pdf-merger/)) - Simple utility to merge multiple PDF files into a single document with customizable order. → [Details](media/pdf-merger/README.md)
- **PDF to Markdown Converter** ([media/pdf-to-markdown/](media/pdf-to-markdown/)) - Extract textual content and metadata from PDF files into clean Markdown format. → [Details](media/pdf-to-markdown/README.md)
- **Image to PDF** ([media/image-to-pdf/](media/image-to-pdf/)) - Convert a directory of images into a single PDF document. → [Details](media/image-to-pdf/README.md)
- **PPT to PDF** ([media/ppt-to-pdf/](media/ppt-to-pdf/)) - Batch convert PowerPoint presentations (.pptx) to PDF format. → [Details](media/ppt-to-pdf/README.md)
- **Photo Splitter** ([media/photo-splitter/](media/photo-splitter/)) - Extract individual student portraits from group photos using face detection and roster mapping. → [Details](media/photo-splitter/README.md)

### 🛡️ Security
- **Android Intent DAST Suite** ([security/android-intent-dast-suite/](security/android-intent-dast-suite/)) - Dynamic application security testing scanner, automated verification scripts, and companion vulnerable/attacker testbed apps for Android Intent Redirection vulnerabilities. → [Details](security/android-intent-dast-suite/README.md)
- **Password Security Checker** ([security/password-security-checker/](security/password-security-checker/)) - PowerShell tool to check if passwords have been exposed in data breaches using HIBP API. → [Details](security/password-security-checker/README.md)
- **PDF Password Cracker** ([security/pdf-password-cracker/](security/pdf-password-cracker/)) - High-performance Python tool for cracking Standard Security Handler (R2-R4, 40/128-bit RC4) password-protected PDFs. → [Details](security/pdf-password-cracker/README.md)
- **Frida APK Tool** ([security/frida-apk-tool/](security/frida-apk-tool/)) - Toolkit for patching Android APKs with Frida hooks for dynamic analysis and instrumentation. → [Details](security/frida-apk-tool/README.md)
- **CYBERSEC 2026 Slide Downloader** ([security/cybersec-slide-downloader/](security/cybersec-slide-downloader/)) - Node.js utility to fetch and download all presentation slides from the CYBERSEC 2026 conference backend. → [Details](security/cybersec-slide-downloader/README.md)
- **Hacker News Scraper** ([security/hacker-news-scraper/](security/hacker-news-scraper/)) - Node.js scraper utility to batch download the last 3 weeks of articles from The Hacker News as Markdown. → [Details](security/hacker-news-scraper/README.md)
- **Local HTTPS Certificate Helper** ([security/local-https-cert-helper/](security/local-https-cert-helper/)) - OpenSSL tool to quickly generate local Root CA and server certificates, with a Node.js test server. → [Details](security/local-https-cert-helper/README.md)
- **CyLab Challenge Exporter** ([security/cylab-challenge-exporter/](security/cylab-challenge-exporter/)) - Export all challenges from CyLab Security Academy (picoCTF) and generate progress checklists. → [Details](security/cylab-challenge-exporter/README.md)

### 📝 Text & Encoding
- **Markdown Toolkit** ([text/markdown-toolkit/](text/markdown-toolkit/)) - Lightweight utility toolkit for Markdown conversions (TXT/HTML to MD), quote-safe paragraph formatting, code block extraction, and TOC generation. → [Details](text/markdown-toolkit/README.md)
- **Text Converter (Simplified ↔ Traditional Chinese)** ([text/text-converter-zh/](text/text-converter-zh/)) - Selective Chinese text conversion toolkit with review-before-convert workflow. → [Details](text/text-converter-zh/README.md)
- **Base64 Converter** ([text/base64-converter/](text/base64-converter/)) - Utility for encoding and decoding strings or files to/from Base64 format. → [Details](text/base64-converter/README.md)
- **Hex to ASCII** ([text/hex-to-ascii/](text/hex-to-ascii/)) - Convert hexadecimal strings to their ASCII text equivalents. → [Details](text/hex-to-ascii/README.md)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Node.js 16.0 or higher
- pip / npm

### Installation

1. Clone the repository:

```bash
git clone https://github.com/Youchenjiang/Script-List.git
cd Script-List
```

2. Navigate to the script you want to use:

```bash
cd category/script-name
```

3. Install dependencies (if required):

```bash
pip install -r requirements.txt
# or for Node.js tools:
npm install
```

4. Run the script according to its dedicated README instructions.

---

## Usage Guidelines

Each script includes:

- **README.md / README.zh-TW.md**: Detailed documentation and usage instructions
- **requirements.txt / package.json**: List of dependencies
- **examples/**: Sample inputs and outputs

Please read the individual script's README for specific usage instructions.

---

## 🤝 Contributing

Contributions are welcome! Here's how to contribute:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-script`)
3. Make your changes
4. Commit your changes (`git commit -m 'Add amazing script'`)
5. Push to the branch (`git push origin feature/amazing-script`)
6. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔗 Related Projects

- [Method-List](https://github.com/Youchenjiang/Method-List) - Technical knowledge base and solutions
- [Clickra](https://github.com/Youchenjiang/Clickra) - Windows modern context menu extension utility (promoted to a standalone repository)

---

## 👤 Author

**Youchen Jiang**

- GitHub: [@Youchenjiang](https://github.com/Youchenjiang)

---

## ⭐ Show Your Support

Give a ⭐️ if this project helped you!
