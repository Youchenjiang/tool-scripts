"""
學生成績登記輔助指令碼
支援以「後兩碼」或「完整學號」輸入成績，自動偵測衝突並提示需確認的名單。
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
GRADES_CSV = BASE_DIR / "grades.csv"

# 重複後兩碼名單（需特別確認）
CONFLICTING_SUFFIXES = {"01", "02", "04", "07", "11"}

def load_students():
    with open(GRADES_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        students = list(reader)
    return students

def get_mapping(students):
    by_suffix = defaultdict(list)
    by_id = {}
    for s in students:
        sid = s["帳號"]
        suffix = sid[-2:]
        by_suffix[suffix].append(s)
        by_id[sid] = s
    return by_suffix, by_id

def parse_input_lines(text: str):
    """
    解析文字輸入，支援格式如：
    05 85
    115423001 90
    01, 88
    """
    entries = []
    lines = text.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"[\s,:\t]+", line)
        if len(parts) >= 2:
            key, score = parts[0], parts[1]
            extra = " ".join(parts[2:]) if len(parts) > 2 else ""
            entries.append((key, score, extra))
    return entries

def process_grades(input_text: str):
    students = load_students()
    by_suffix, by_id = get_mapping(students)

    entries = parse_input_lines(input_text)
    auto_assigned = []
    need_confirm = []
    not_found = []

    for key, score, extra in entries:
        if len(key) == 9 and key in by_id:
            # 完整學號
            s = by_id[key]
            s["成績"] = score
            if extra:
                s["備註"] = extra
            auto_assigned.append((s["帳號"], s["姓名"], score))
        elif len(key) <= 3:
            # 後兩碼或後三碼
            suffix = key[-2:].zfill(2)
            matched = by_suffix.get(suffix, [])
            if len(matched) == 1:
                s = matched[0]
                s["成績"] = score
                if extra:
                    s["備註"] = extra
                auto_assigned.append((s["帳號"], s["姓名"], score))
            elif len(matched) > 1:
                need_confirm.append({
                    "input_key": key,
                    "score": score,
                    "candidates": [(s["帳號"], s["姓名"]) for s in matched]
                })
            else:
                not_found.append((key, score))
        else:
            not_found.append((key, score))

    return auto_assigned, need_confirm, not_found

if __name__ == "__main__":
    print("已載入登記系統。需確認之重複後兩碼:", sorted(CONFLICTING_SUFFIXES))
