"""
ta_course_recorder.recorder
核心引擎：負責唯讀載入樣板、複製分頁、維持精確格式並注入每週教學紀錄。
支援：
1. 儲存格座標動態映射 (Cell Mapping) 與精確拆欄 (C, D, E 等)
2. 自動高度自適應 (Auto-fit Row Height)：依字數動態放大列高，絕不腰斬文字
3. 垂直居中對齊，徹底消除 Row 4 / Row 5 出席狀態字體疊壓
"""

import copy
from datetime import date, datetime, time, timedelta
import math
import os
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# 原樣板標準標楷體字型（絕不縮小字體）
FONT_TITLE = Font(name="DFKai-SB", size=18, bold=True)
FONT_BOLD_14 = Font(name="DFKai-SB", size=14, bold=True)
FONT_REGULAR_14 = Font(name="DFKai-SB", size=14, bold=False)
FONT_REGULAR_12 = Font(name="DFKai-SB", size=12, bold=False)

# 對齊方式：垂直居中 (center)，避免靠底 (bottom) 導致壓字
ALIGN_CENTER_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
ALIGN_LEFT_CENTER = Alignment(horizontal="left", vertical="center", wrap_text=True)

# 細外框定義，取消合併後重新補上邊框保證美觀
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def calculate_required_height(text, col_width, font_size=12, line_spacing=18, min_height=80):
    """
    根據文字長度、欄位寬度與換行數，動態計算所需的最適列高
    """
    if not text:
        return min_height

    lines = str(text).split("\n")
    total_visual_lines = 0

    # 粗估：繁體中文在指定欄寬下約能容納的字數
    chars_per_line = max(int(col_width * 0.8), 4)

    for line in lines:
        if not line:
            total_visual_lines += 1
        else:
            total_visual_lines += math.ceil(len(line) / chars_per_line)

    needed_height = total_visual_lines * line_spacing + 15
    return max(needed_height, min_height)


class TACourseRecorder:
    def __init__(self, config_dict, base_dir=None):
        self.config = config_dict
        self.base_dir = base_dir or os.getcwd()

        self.template_path = self._resolve_template_path()
        rel_out = self.config["paths"]["output_file"]
        self.output_path = os.path.normpath(os.path.join(self.base_dir, rel_out))

        self.map = self.config.get("cell_mapping", {})

        course_cfg = self.config["course"]
        self.course_name = course_cfg.get("course_name", "電腦網路安全")
        self.teacher_name = course_cfg.get("teacher_name", "陳奕明")
        self.ta_name = course_cfg.get("ta_name", "蔣侑宸")
        self.semester_title = course_cfg.get(
            "semester_title", "115學年度第一學期AI融入課程教學紀錄表"
        )

        start_date_str = course_cfg.get("start_date", "2026-10-09")
        self.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

        st_parts = [int(p) for p in str(course_cfg.get("start_time", "14:07")).split(":")]
        et_parts = [int(p) for p in str(course_cfg.get("end_time", "16:50")).split(":")]
        self.start_time = time(st_parts[0], st_parts[1])
        self.end_time = time(et_parts[0], et_parts[1])

        cfg_duration = course_cfg.get("duration_minutes")
        if cfg_duration:
            self.duration_minutes = int(cfg_duration)
        else:
            diff = datetime.combine(date.min, self.end_time) - datetime.combine(
                date.min, self.start_time
            )
            self.duration_minutes = int(diff.total_seconds() / 60)

        self.default_record = self.config.get("default_record", {})
        self.weeks_data = self.config.get("weeks", {})

    def _resolve_template_path(self):
        rel_tmpl = self.config.get("paths", {}).get("template_file", "")
        candidates = [
            os.path.normpath(os.path.join(self.base_dir, rel_tmpl)),
            os.path.normpath(
                os.path.join(self.base_dir, "templates", "course_record_template.xlsx")
            ),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        raise FileNotFoundError(f"找不到樣板檔案！已搜尋路徑：{candidates}")

    def duplicate_sheet(self, wb, source_sheet, target_title):
        new_sheet = wb.copy_worksheet(source_sheet)
        new_sheet.title = target_title

        for row_idx, row_dim in source_sheet.row_dimensions.items():
            new_sheet.row_dimensions[row_idx].height = row_dim.height

        for col_letter, col_dim in source_sheet.column_dimensions.items():
            new_sheet.column_dimensions[col_letter].width = col_dim.width

        return new_sheet

    def remove_extra_content_rows(self, ws):
        """
        刪除 Row 10 ~ 13 多餘的空白列，將 Row 14 (整體觀察與省思) 緊接移至 Row 10。
        並重新建立完美的合併儲存格與邊框。
        """
        # 先解除 9 列以後的所有合併儲存格
        for rng in list(ws.merged_cells.ranges):
            if rng.min_row >= 9:
                ws.unmerge_cells(str(rng))

        # 刪除 10 ~ 13 列 (共 4 列)
        ws.delete_rows(10, 4)

        # 重新建立 Row 10 的合併儲存格 (A10:E10 標題, F10:K10 省思內容)
        ws.merge_cells("A10:E10")
        ws.merge_cells("F10:K10")

        # 為 Row 9 補上乾淨邊框
        for c in range(1, 12):
            ws.cell(row=9, column=c).border = THIN_BORDER

        # 為 Row 10 補上標準邊框
        for c in range(1, 12):
            ws.cell(row=10, column=c).border = THIN_BORDER

        ws["A10"] = "整體觀察與省思"
        ws["A10"].font = FONT_BOLD_14
        ws["A10"].alignment = ALIGN_CENTER_CENTER

    def populate_week(self, ws, week_num):
        record = copy.deepcopy(self.default_record)
        if week_num in self.weeks_data:
            record.update(self.weeks_data[week_num])

        if "date" in record and record["date"]:
            week_date = datetime.strptime(str(record["date"]), "%Y-%m-%d").date()
        else:
            offset_weeks = week_num - 5 if week_num >= 5 else week_num - 1
            week_date = self.start_date + timedelta(weeks=offset_weeks)

        m = self.map

        # 1. 表頭與基本資訊
        ws[m["semester_title"]] = self.semester_title
        ws[m["semester_title"]].font = FONT_TITLE
        ws[m["semester_title"]].alignment = ALIGN_CENTER_CENTER

        ws[m["course_name"]] = self.course_name
        ws[m["course_name"]].font = FONT_BOLD_14
        ws[m["course_name"]].alignment = ALIGN_CENTER_CENTER

        ws[m["teacher_name"]] = self.teacher_name
        ws[m["teacher_name"]].font = FONT_REGULAR_14
        ws[m["teacher_name"]].alignment = ALIGN_CENTER_CENTER

        ws[m["ta_name"]] = self.ta_name
        ws[m["ta_name"]].font = FONT_REGULAR_14
        ws[m["ta_name"]].alignment = ALIGN_CENTER_CENTER

        ws[m["date"]] = datetime.combine(week_date, time.min)
        ws[m["date"]].font = FONT_REGULAR_14
        ws[m["date"]].alignment = ALIGN_LEFT_CENTER

        ws[m["start_time"]] = self.start_time
        ws[m["start_time"]].font = FONT_REGULAR_14
        ws[m["start_time"]].alignment = ALIGN_CENTER_CENTER

        ws[m["end_time"]] = self.end_time
        ws[m["end_time"]].font = FONT_REGULAR_14
        ws[m["end_time"]].alignment = ALIGN_CENTER_CENTER

        ws[m["duration"]] = self.duration_minutes
        ws[m["duration"]].font = FONT_REGULAR_14
        ws[m["duration"]].alignment = ALIGN_CENTER_CENTER

        # 2. 出席狀態：高度保證自適應、文字垂直置中
        ws.row_dimensions[4].height = 42.0
        ws.row_dimensions[5].height = 36.0

        is_holiday = record.get("is_holiday", False)
        if is_holiday:
            holiday_reason = record.get("holiday_reason", "期中考/國定假日")
            ws[m["attended_yes"]] = "□是，我全程參加這堂課。"
            ws[m["attended_no"]] = (
                f"☑否，0%(請填寫參加比例) ，其他說明:{holiday_reason}"
            )
        else:
            ws[m["attended_yes"]] = "☑是，我全程參加這堂課。"
            ws[m["attended_no"]] = (
                "□否，　　%(請填寫參加比例) ，其他說明:(例如期中考、國定假日、老師請假)"
            )

        ws[m["attended_yes"]].font = FONT_REGULAR_14
        ws[m["attended_yes"]].alignment = ALIGN_LEFT_CENTER
        ws[m["attended_no"]].font = FONT_REGULAR_14
        ws[m["attended_no"]].alignment = ALIGN_LEFT_CENTER

        # 3. 刪除多餘列並整理結構
        self.remove_extra_content_rows(ws)

        crow = m.get("content_row", 9)
        c_obj = f"{m.get('col_objective', 'A')}{crow}"
        c_plat = f"{m.get('col_platform', 'B')}{crow}"

        pre = record.get("pre_class", {})
        in_c = record.get("in_class", {})
        post = record.get("post_class", {})

        if isinstance(pre, str):
            pre = {"name": pre, "content": pre, "eval": "先備檢測"}
        if isinstance(in_c, str):
            in_c = {"name": in_c, "content": in_c, "eval": "課堂實作檢視"}
        if isinstance(post, str):
            post = {"name": post, "content": post, "eval": "作業繳交審查"}

        if is_holiday:
            holiday_reason = record.get("holiday_reason", "期中考/國定假日")
            ws[c_obj] = f"無（{holiday_reason}）"
            ws[c_plat] = "無"
            ws[f"{m.get('col_pre_name', 'C')}{crow}"] = "無"
            ws[f"{m.get('col_pre_content', 'D')}{crow}"] = "無"
            ws[f"{m.get('col_pre_eval', 'E')}{crow}"] = "無"
            ws[f"{m.get('col_in_name', 'F')}{crow}"] = "無"
            ws[f"{m.get('col_in_content', 'G')}{crow}"] = "無"
            ws[f"{m.get('col_in_eval', 'H')}{crow}"] = "無"
            ws[f"{m.get('col_post_name', 'I')}{crow}"] = "無"
            ws[f"{m.get('col_post_content', 'J')}{crow}"] = "無"
            ws[f"{m.get('col_post_eval', 'K')}{crow}"] = "無"
            reflection_text = f"本週為{holiday_reason}，暫停一次課堂實體/線上觀課。"
        else:
            ws[c_obj] = record.get("objective", "")
            ws[c_plat] = record.get("platform", "")
            ws[f"{m.get('col_pre_name', 'C')}{crow}"] = pre.get("name", "")
            ws[f"{m.get('col_pre_content', 'D')}{crow}"] = pre.get("content", "")
            ws[f"{m.get('col_pre_eval', 'E')}{crow}"] = pre.get("eval", "")

            ws[f"{m.get('col_in_name', 'F')}{crow}"] = in_c.get("name", "")
            ws[f"{m.get('col_in_content', 'G')}{crow}"] = in_c.get("content", "")
            ws[f"{m.get('col_in_eval', 'H')}{crow}"] = in_c.get("eval", "")

            ws[f"{m.get('col_post_name', 'I')}{crow}"] = post.get("name", "")
            ws[f"{m.get('col_post_content', 'J')}{crow}"] = post.get("content", "")
            ws[f"{m.get('col_post_eval', 'K')}{crow}"] = post.get("eval", "")
            reflection_text = record.get("reflection", "")

        ref_cell = m.get("reflection", "F10")
        ws[ref_cell] = reflection_text

        # 4. 樣式強化保證 (維持原字體大小 12/14pt，垂直置中)
        # 對齊規則：運用 AI 說明區（Row 9），除非內容是「無」採置中，否則一律「置左」對齊
        ws[c_obj].font = FONT_BOLD_14
        ws[c_plat].font = FONT_BOLD_14

        for col_l in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
            cell = ws[f"{col_l}{crow}"]
            cell_val = str(cell.value or "").strip()
            if cell_val.startswith("無"):
                cell.alignment = ALIGN_CENTER_CENTER
            else:
                cell.alignment = ALIGN_LEFT_CENTER

        for col_l in ["C", "D", "E", "F", "G", "H", "I", "J", "K"]:
            ws[f"{col_l}{crow}"].font = FONT_REGULAR_12

        ref_val = str(ws[ref_cell].value or "").strip()
        ws[ref_cell].font = FONT_REGULAR_12
        if ref_val.startswith("無"):
            ws[ref_cell].alignment = ALIGN_CENTER_CENTER
        else:
            ws[ref_cell].alignment = ALIGN_LEFT_CENTER

        # 5. 只解除 AI 運用表格（Row 9）的高度限制，交由 Excel 原生引擎自動適應
        # 完全不影響其他任何列的既有設定
        if crow in ws.row_dimensions:
            del ws.row_dimensions[crow]

        # Row 10 (整體省思) 維持穩定適當高度 (200pt)，確保 4 點省思完整展示
        ws.row_dimensions[10].height = 200.0

    def generate_all(self, start_week=5, end_week=18):
        print(f"Reading template: {self.template_path}")
        wb = openpyxl.load_workbook(self.template_path)

        template_name = "Week7" if "Week7" in wb.sheetnames else wb.sheetnames[0]
        template_sheet = wb[template_name]

        for w in range(start_week, end_week + 1):
            sheet_title = f"Week{w}"
            if sheet_title in wb.sheetnames:
                ws = wb[sheet_title]
            else:
                ws = self.duplicate_sheet(wb, template_sheet, sheet_title)

            self.populate_week(ws, w)

        target_titles = [f"Week{w}" for w in range(start_week, end_week + 1)]
        wb._sheets = [wb[t] for t in target_titles if t in wb.sheetnames]

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        wb.save(self.output_path)
        print(f"[OK] Record generated successfully with Auto-fit height and Clean Split Columns!")
        print(f"[File] {self.output_path}")
        print(f"[Sheets] Week{start_week} ~ Week{end_week} ({end_week - start_week + 1} weeks)")
        return self.output_path
