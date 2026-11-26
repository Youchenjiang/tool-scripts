#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
學生成績管理系統 - 學期歷次成績彙整模組 (Consolidator)
自動掃描指定目錄下所有 grade_YYYYMMDD.csv，彙整全學期歷次成績，
計算缺繳次數、實繳次數、繳交率、各等第次數及平均等第積分，並產出專業 Excel 與 CSV。
"""

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from .models import Roster, Student

# 等第至 GPA 積分對照表 (4.3 制)
GRADE_POINT_MAP = {
    "A++": 4.3,
    "A+": 4.0,
    "A": 3.7,
    "A-": 3.3,
    "B+": 3.0,
    "B": 2.7,
    "B-": 2.3,
    "C+": 2.0,
    "C": 1.7,
    "C-": 1.0,
    "F": 0.0,
}


class SemesterConsolidator:
    """全學期歷次成績彙整器"""

    @classmethod
    def find_grade_csv_files(cls, directory: Path) -> List[Tuple[str, Path]]:
        """
        掃描目錄下所有符合 grade_YYYYMMDD.csv 格式之檔案，
        回傳已依日期遞增排序之 [(date_str, file_path)] 清單。
        """
        directory = Path(directory)
        if not directory.exists():
            return []

        pattern = re.compile(r"^grade_(\d{8})\.csv$", re.IGNORECASE)
        matched_files = []

        for p in directory.glob("*.csv"):
            m = pattern.match(p.name)
            if m:
                raw_date = m.group(1)
                formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
                matched_files.append((formatted_date, p))

        matched_files.sort(key=lambda x: x[0])
        return matched_files

    @classmethod
    def load_session_grades(cls, csv_path: Path) -> Dict[str, str]:
        """從單次成績 CSV 讀取 {sid: grade} 對照表"""
        grades = {}
        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            # 定位成績欄位：排除帳號、姓名、備註
            score_col = None
            for col in fieldnames:
                if col not in ("帳號", "姓名", "備註", "學號"):
                    score_col = col
                    break
            if not score_col and len(fieldnames) >= 3:
                score_col = fieldnames[2]

            for row in reader:
                sid = row.get("帳號") or row.get("學號")
                if not sid:
                    continue
                sid = sid.strip()
                val = row.get(score_col, "").strip() if score_col else ""
                grades[sid] = val
        return grades

    @classmethod
    def consolidate(
        cls,
        data_dir: Path,
        roster: Roster,
        output_dir: Optional[Path] = None,
        custom_prefix: Optional[str] = "semester_grades_summary"
    ) -> Tuple[Path, Path, Dict[str, Any]]:
        """
        執行全學期成績彙整：
        1. 掃描所有歷次 CSV
        2. 計算全班每位同學統計數據
        3. 輸出彙整 CSV 與美化 Excel
        """
        data_dir = Path(data_dir)
        output_dir = Path(output_dir) if output_dir else data_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        session_files = cls.find_grade_csv_files(data_dir)
        if not session_files:
            raise FileNotFoundError(f"在目錄 {data_dir} 中找不到任何 grade_YYYYMMDD.csv 檔案")

        dates = [d for d, _ in session_files]
        session_data = {d: cls.load_session_grades(p) for d, p in session_files}

        # 彙整每位同學歷次成績及統計
        student_rows = []
        class_summary = {
            "total_students": len(roster.students),
            "total_sessions": len(dates),
            "sessions": dates,
            "perfect_submission_count": 0,
            "average_submission_rate": 0.0,
            "average_gpa": 0.0
        }

        total_submission_rates = []
        total_gpas = []

        for student in roster.students:
            record: Dict[str, Any] = {
                "帳號": student.sid,
                "姓名": student.name,
                "學制": student.program,
            }

            grades_list = []
            submitted_count = 0
            grade_counts = defaultdict(int)
            point_list = []

            for d in dates:
                g = session_data[d].get(student.sid, "")
                record[d] = g
                if g:
                    submitted_count += 1
                    grades_list.append(g)
                    grade_counts[g] += 1
                    if g in GRADE_POINT_MAP:
                        point_list.append(GRADE_POINT_MAP[g])

            total_sess = len(dates)
            missing_count = total_sess - submitted_count
            submission_rate = (submitted_count / total_sess * 100.0) if total_sess > 0 else 0.0
            avg_gpa = (sum(point_list) / len(point_list)) if point_list else 0.0

            if missing_count == 0:
                class_summary["perfect_submission_count"] += 1

            total_submission_rates.append(submission_rate)
            if point_list:
                total_gpas.append(avg_gpa)

            record["應繳次數"] = total_sess
            record["實繳次數"] = submitted_count
            record["缺繳次數"] = missing_count
            record["繳交率"] = f"{submission_rate:.1f}%"
            record["A++"] = grade_counts.get("A++", 0)
            record["A+"] = grade_counts.get("A+", 0)
            record["A"] = grade_counts.get("A", 0)
            record["A-"] = grade_counts.get("A-", 0)
            record["平均等第積分"] = f"{avg_gpa:.2f}" if point_list else "-"

            # 保存數值型給 Excel 運算
            record["_submission_rate_num"] = submission_rate / 100.0
            record["_avg_gpa_num"] = avg_gpa

            student_rows.append(record)

        if total_submission_rates:
            class_summary["average_submission_rate"] = sum(total_submission_rates) / len(total_submission_rates)
        if total_gpas:
            class_summary["average_gpa"] = sum(total_gpas) / len(total_gpas)

        # 寫出 CSV
        stat_headers = ["應繳次數", "實繳次數", "缺繳次數", "繳交率", "A++", "A+", "A", "A-", "平均等第積分"]
        csv_headers = ["帳號", "姓名", "學制"] + dates + stat_headers

        csv_path = output_dir / f"{custom_prefix}.csv"
        with open(csv_path, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(csv_headers)
            for r in student_rows:
                row_vals = [r.get(h, "") for h in csv_headers]
                writer.writerow(row_vals)

        # 寫出專業美化版 Excel
        xlsx_path = output_dir / f"{custom_prefix}.xlsx"
        cls.export_excel(
            headers=csv_headers,
            rows=student_rows,
            dates=dates,
            stat_headers=stat_headers,
            xlsx_path=xlsx_path
        )

        return csv_path, xlsx_path, class_summary

    @classmethod
    def export_excel(
        cls,
        headers: List[str],
        rows: List[Dict[str, Any]],
        dates: List[str],
        stat_headers: List[str],
        xlsx_path: Path
    ) -> Path:
        """產出專業深藍、凍結雙向窗格、標註缺繳的 Excel 總表"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "全學期成績總表"

        # 凍結前 3 欄 (帳號, 姓名, 學制) 與第 1 行 (表頭)
        ws.freeze_panes = "D2"

        header_font = Font(name="微軟正黑體", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        stat_header_fill = PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid")

        data_font = Font(name="微軟正黑體", size=10)
        bold_font = Font(name="微軟正黑體", size=10, bold=True)
        missing_font = Font(name="微軟正黑體", size=10, color="C00000", bold=True)

        zebra_fill = PatternFill(start_color="F2F5F9", end_color="F2F5F9", fill_type="solid")
        white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        missing_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

        thin_border = Border(
            left=Side(style="thin", color="D9D9D9"),
            right=Side(style="thin", color="D9D9D9"),
            top=Side(style="thin", color="D9D9D9"),
            bottom=Side(style="thin", color="D9D9D9")
        )

        center_align = Alignment(horizontal="center", vertical="center")
        left_align = Alignment(horizontal="left", vertical="center")

        # 寫入表頭
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.font = header_font
            cell.alignment = center_align
            cell.border = thin_border
            if h in stat_headers:
                cell.fill = stat_header_fill
            else:
                cell.fill = header_fill

        # 寫入資料
        for row_idx, r in enumerate(rows, start=2):
            is_zebra = (row_idx % 2 == 1)
            base_fill = zebra_fill if is_zebra else white_fill

            for col_idx, h in enumerate(headers, start=1):
                raw_val = r.get(h, "")
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.font = data_font
                cell.border = thin_border
                cell.fill = base_fill

                if h == "姓名":
                    cell.value = raw_val
                    cell.alignment = left_align
                elif h in dates:
                    cell.value = raw_val
                    cell.alignment = center_align
                    if not raw_val:
                        # 標註缺繳
                        cell.value = "-"
                        cell.font = missing_font
                        cell.fill = missing_fill
                elif h == "繳交率":
                    cell.value = r.get("_submission_rate_num", 0.0)
                    cell.number_format = "0.0%"
                    cell.alignment = center_align
                elif h == "平均等第積分":
                    cell.value = r.get("_avg_gpa_num", 0.0)
                    cell.number_format = "0.00"
                    cell.alignment = center_align
                elif h in ("應繳次數", "實繳次數", "缺繳次數", "A++", "A+", "A", "A-"):
                    cell.value = int(raw_val) if str(raw_val).isdigit() else raw_val
                    cell.alignment = center_align
                    if h == "缺繳次數" and int(raw_val or 0) > 0:
                        cell.font = missing_font
                else:
                    cell.value = raw_val
                    cell.alignment = center_align

        # 自動調整欄寬
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                # 計算中文字寬度 (中文字佔 2 單位寬度)
                cell_len = sum(2 if ord(c) > 127 else 1 for c in val_str)
                if cell_len > max_len:
                    max_len = cell_len
            ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

        wb.save(xlsx_path)
        return xlsx_path
