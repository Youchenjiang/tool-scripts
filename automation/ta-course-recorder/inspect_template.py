#!/usr/bin/env python3
"""
inspect_template.py
診斷小工具：未來如果換了新版 Excel 模板，執行此工具即可自動分析儲存格座標！
使用方式：
    python inspect_template.py --file 新範本.xlsx
"""

import argparse
import io
import os
import sys
import openpyxl

# 避免 Windows 終端編碼報錯
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def inspect(file_path):
    if not os.path.isabs(file_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.normpath(os.path.join(script_dir, file_path))

    if not os.path.exists(file_path):
        print(f"[Error] 找不到檔案：{file_path}")
        return

    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active
    print(f"=== 正在分析範本：{file_path} (工作表: {sheet.title}) ===")

    keywords = {
        "學年度": "semester_title (大標題)",
        "課程名稱": "course_name (課程名稱)",
        "授課教師": "teacher_name (教師姓名)",
        "觀課助理": "ta_name (TA姓名)",
        "觀課日期": "date (觀課日期)",
        "觀課時間": "time (觀課時間)",
        "課程長度": "duration (課程長度)",
        "全程參加": "attended (出席狀態)",
        "教學目標": "objective (教學目標欄)",
        "整體觀察與省思": "reflection (整體觀察與省思)",
    }

    found = {}
    for r in range(1, min(sheet.max_row + 1, 30)):
        for c in range(1, min(sheet.max_column + 1, 15)):
            v = sheet.cell(r, c).value
            if v:
                v_str = str(v).strip()
                for kw, label in keywords.items():
                    if kw in v_str and label not in found:
                        coord = sheet.cell(r, c).coordinate
                        found[label] = (coord, v_str.replace("\n", " "))

    print("\n🔍 找到的關鍵欄位對應位置：")
    for label, (coord, text) in found.items():
        print(f"  • {label:30s} -> 儲存格 {coord} (內容: '{text[:25]}')")

    print("\n💡 提示：若發現位置與 config.yaml 中的 cell_mapping 不同，直接更新 config.yaml 即可！")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Excel 模板儲存格座標分析工具")
    parser.add_argument("--file", default="templates/course_record_template.xlsx", help="欲分析的 Excel 樣板路徑")
    args = parser.parse_args()
    inspect(args.file)
