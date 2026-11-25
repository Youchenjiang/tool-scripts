@echo off
title IDA Pro 9.1 Bootstrapper
cd /d "%~dp0"

:: Launch PowerShell script with ExecutionPolicy Bypass
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Execution interrupted or error occurred. Press any key to exit...
    pause >nul
)
