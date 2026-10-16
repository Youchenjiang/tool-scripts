@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================================
echo    Windows 底層直接列印工具 (免開瀏覽器，絕不卡死)
echo ========================================================

if "%~1"=="" (
    powershell -ExecutionPolicy Bypass -File "%~dp0direct_print.ps1"
) else (
    powershell -ExecutionPolicy Bypass -File "%~dp0direct_print.ps1" -PdfPath "%~1"
)

echo.
pause
