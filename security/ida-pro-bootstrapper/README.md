# IDA Pro 9.1 Bootstrapper & Maintenance Toolkit

A PowerShell-based automated setup, isolated environment configuration, and lifecycle maintenance tool for IDA Professional 9.1 on Windows.

---

## 🏗️ Architecture Overview

The toolkit adopts a project-local prefix (`.conda`) standard, fully encapsulating Python 3.11 and dependencies inside the IDA directory:

```mermaid
flowchart TD
    User(["User Action\n(Desktop Shortcut / Win Search 'ida')"]) --> Launcher["ida.exe\n(IDA Pro 9.1 GUI Launcher)"]

    subgraph IDA_Core ["IDA Professional 9.1 Core"]
        IDA_GUI["IDA GUI & Analysis Engine\n(ida.dll / ida32.dll with RSA Modulus Patch)"]
        Lic["idapro.hexlic\n(All Decompilers Unlocked: x86/ARM/MIPS/PPC/RV64)"]
        IDA_GUI --> Lic
    end

    Launcher --> IDA_Core

    subgraph Local_Env [".conda Local Isolated Environment (Python 3.11)"]
        PyEnv["python.exe / python311.dll\n(Isolated from host Python 3.14)"]
        IdaPy["IDAPython Registry Binding\n(HKCU:\\Software\\Hex-Rays\\IDA)"]
        IdaLib["idalib (idapro Python package)\n(Headless Analysis Library)"]
        FeedsDep["ida_feeds Dependencies\n(PyQt5, rpyc, requests)"]
        PyEnv --> IdaPy
        PyEnv --> IdaLib
        PyEnv --> FeedsDep
    end

    IDA_Core <-->|Dynamic Invocation| Local_Env

    subgraph Plugins ["Plugins & Tooling"]
        Feeds["plugins/ida_feeds\n(FLIRT & Signature Manager)"]
        FlairConfig["config.json\n(Directs to tools/flair)"]
        FlairTools["tools/flair\n(dumpsig, sigmake, pcf)"]
        Feeds --> FlairConfig
        FlairConfig --> FlairTools
    end

    IDA_Core --> Plugins
```

---

## 🔄 Lifecycle Workflow

```mermaid
flowchart TD
    Start(["Run install.bat / install.ps1"]) --> CheckIDA["Resolve IDA Pro 9.1 Directory"]
    CheckIDA --> Step1{"[1/6] Check Local .conda"}
    Step1 -->|Missing| CreateConda["Invoke Miniforge to create Python 3.11\n(Prefix: .\\.conda)"]
    Step1 -->|Ready| Step2{"[2/6] Check IDAPython"}
    CreateConda --> Step2

    Step2 --> SwitchPy["Call idapyswitch.exe --force-path\nBind to .conda\\python3.dll"]
    SwitchPy --> Step3["[3/6] Install & Activate idalib\n(pip install idalib/python + py-activate)"]

    Step3 --> Step4["[4/6] Install ida_feeds Dependencies (PyQt5, rpyc)\nWrite config.json (flair path)"]

    Step4 --> Step5["[5/6] Run keygen3.py\nBackup original DLLs, apply modulus patch\nDeploy idapro.hexlic to %APPDATA%"]

    Step5 --> Step6["[6/6] Register Desktop & Start Menu Shortcuts\n(Instant Windows Search 'ida')"]

    Step6 --> Complete(["Setup Complete! IDA Pro 9.1 fully activated"])
```

---

## ✨ Features

- **Project-Local Prefix (`.conda`)**: Strictly follows the isolated environment standard without system Python 3.14 conflicts.
- **IDAPython Auto-Alignment**: Invokes `idapyswitch.exe` to bind registry keys, fixing `No suitable Python installations were found`.
- **Headless `idalib` Activation**: Builds `idapro` wheel and links dynamic libraries for background batch reverse engineering.
- **`ida_feeds` & `flair` Integration**: Auto-installs PyQt5/rpyc and writes correct `tools/flair` paths to `config.json`.
- **Defensive License & Patch Application**: Safely backups `ida.dll` / `ida32.dll` to `.bak`, unlocks all arch decompilers.
- **Start Menu Instant Search**: Creates shortcuts on Desktop and Windows Start Menu (Win key search `ida`).
- **Interactive TUI Wizard**: Real-time status monitoring, one-click repair, re-activation, and launcher options.

---

## 🚀 Quick Start

1. Place this toolkit in the IDA directory (or pass `-IdaPath`).
2. Double-click `install.bat`.
3. Select `[1]` to run full automatic configuration.
