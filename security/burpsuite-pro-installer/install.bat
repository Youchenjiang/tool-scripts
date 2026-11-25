@echo off
title Burp Suite Pro Installer
cd /d "%~dp0"

:: 透過 Bypass 策略呼叫 PowerShell 腳本，支援自訂目標路徑參數 %*
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] 執行中斷或發生錯誤，按任意鍵退出...
    pause >nul
)
