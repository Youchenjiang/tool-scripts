@echo off
chcp 65001 >nul
echo 正在同步轉換 data 資料夾下的成績檔案為 Excel...
python export_excel.py
echo.
echo [完成] 所有成績 Excel 檔案已成功更新！
pause
