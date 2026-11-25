# Burp Suite Pro Bootstrapper & Maintenance Toolkit

A PowerShell-based portable installer, environment automator, and lifecycle maintenance tool for Burp Suite Professional on Windows.

## Features

- **Portable OpenJDK 21 Option**: 100% portable setup without requiring Windows Administrator rights.
- **Resilient Multi-Threaded Downloads**: Uses `aria2c` (16 connections with breakpoint resume) or `curl` with minimum file size validation.
- **Fully Portable Launchers**: `Burp.bat` and `Burp-Suite-Pro.vbs` use dynamic `%~dp0` relative paths.
- **JVM Performance Tuning**: Default `-Xms1024m -Xmx4096m -XX:+UseG1GC` configuration with customizable memory limits.
- **Desktop Shortcut Automation**: Automatically creates a silent background launch shortcut with custom icon binding.
- **Interactive Maintenance TUI**:
  - Live status dashboard (JDK, Burp JAR, Loader, Shortcut).
  - One-click setup & repair.
  - One-click PortSwigger JAR update.
  - Memory tuning and temp file cleaning.

## Quick Start

1. Place your `loader.jar` and `aria2c.exe` in the root folder.
2. Double-click `install.bat` (automatically bypasses Windows ExecutionPolicy).
3. Follow the menu prompt `[1]` to initialize the environment and launch the software.
