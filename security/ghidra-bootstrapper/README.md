# Ghidra SRE Bootstrapper & Shortcut Manager

Automated installer, environment bootstrapper, silent zero-console launcher generator, and dual shortcut registration toolkit for the **NSA Ghidra Software Reverse Engineering Framework (Ghidra 12.2 + JDK 25 LTS)**.

---

## 1. Architecture & Dual-JDK Isolation

```mermaid
graph TD
    User["User Trigger (Shortcut / Win Search)"] --> VBS["Ghidra.vbs (Silent WScript Wrapper)"]
    VBS --> BAT["Ghidra.bat (JDK Path Binder)"]
    BAT --> RUN["ghidraRun.bat (Ghidra Launcher)"]
    RUN --> Launch["support/launch.bat (JVM Engine)"]
    Launch --> JVM25["javaw.exe (JDK 25 LTS at C:/MyAPP/Dev/Env/jdk-25)"]
    JVM25 --> GUI["Ghidra SRE 12.2 GUI Window"]

    BurpUser["Burp Trigger (Desktop / Win Search)"] --> BurpBAT["Burp.bat"]
    BurpBAT --> JVM21["javaw.exe (JDK 21 LTS at C:/Program Files/Java/jdk-21)"]
    JVM21 --> BurpGUI["Burp Suite Pro GUI Window"]
```

---

## 2. Bootstrapper Lifecycle

```mermaid
flowchart TD
    Start(["Start install.bat"]) --> CheckJDK["1. Detect Compatible JDK (JDK 25+ / Auto-fetch OpenJDK 25)"]
    CheckJDK --> Engine["2. Detect High-Speed Engine (aria2c / curl)"]
    Engine --> Download["3. Download Ghidra 12.2 Release"]
    Download --> Extract["4. Fast Extraction via tar.exe & Rename to 'Ghidra'"]
    Extract --> Config["5. Configure JAVA_HOME_OVERRIDE in launch.properties (UTF-8 No BOM)"]
    Config --> Patch["6. Patch launch.bat background spawn parameters"]
    Patch --> GenLaunchers["7. Generate Ghidra.bat & Ghidra.vbs (Zero Console)"]
    GenLaunchers --> Shortcuts["8. Register Dual Shortcuts (Desktop + Start Menu)"]
    Shortcuts --> End(["Done (Instant Win + Ghidra Search Ready)"])
```

---

## 3. Key Features

- **Ghidra 12.2 & JDK 25 LTS Native Support**: Fully compiled for and paired with the latest OpenJDK 25 LTS release.
- **Dual-JDK Safe Coexistence**: Keeps Burp Suite Pro strictly pinned to stable JDK 21, while Ghidra runs on JDK 25.
- **Capitalized Clean Hierarchy**: Ensures standard uppercase naming convention (`C:\MyAPP\Sec\Ghidra`).
- **Silent Zero-Console Launcher**: Wraps execution inside `Ghidra.vbs` and `javaw.exe`, preventing annoying black terminal windows from flashing or remaining open.
- **Dual Shortcut Registration**:
  - **Desktop**: Fast double-click access with high-resolution `ghidra.ico`.
  - **Start Menu (`Programs`)**: Fully indexed by Windows Search. Press `Win`, type `ghidra`, and press `Enter` to launch immediately.
- **Pure ASCII Batch Wrapper**: `install.bat` uses strictly ASCII characters to prevent Windows CP950/CP437 multi-byte parsing errors.

---

## 4. Usage

### Interactive / Quick Run
Double-click `install.bat` or run in terminal:
```cmd
install.bat
```

### CLI Parameters (PowerShell)
```powershell
.\install.ps1 -InstallPath "C:\MyAPP\Sec\Ghidra" -SkipDownload
```

| Parameter | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `-InstallPath` | String | Target directory for Ghidra installation | `C:\MyAPP\Sec\Ghidra` |
| `-SkipDownload` | Switch | Skip downloading if Ghidra already exists | `False` |
| `-Help` | Switch | Display detailed help | `False` |
