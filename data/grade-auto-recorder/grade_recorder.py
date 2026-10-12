#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
學生成績自動化登記與衝突比對系統 (Grade Auto-Recorder)
向後相容入口點，底層重構轉發至 grade_recorder 模組。
"""

import sys

# 確保在 Windows 控制台正確輸出 UTF-8 中文字
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

from grade_recorder.cli import main
from grade_recorder import Student, Roster, GradeParser, GradeEngine, GradeExporter

# 保留 GradeRecorder 類別向後相容
class GradeRecorder:
    def __init__(self, roster_path=None):
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent
        data_dir = base_dir / "data"
        if not roster_path:
            roster_path = data_dir / "roster.csv" if data_dir.exists() else base_dir / "roster.csv"
            if not roster_path.exists():
                roster_path = base_dir / "data.example" / "roster.example.csv"
        self.roster = Roster(Path(roster_path))
        self.students = self.roster.students

    def process_data(self, input_text: str, interactive: bool = True):
        submissions, _ = GradeParser.extract_submissions(input_text)
        audit = GradeEngine.audit_submissions(submissions, self.roster)
        if interactive:
            from grade_recorder.cli import run_interactive_audit
            return run_interactive_audit(audit, self.roster)
        res = dict(audit["auto_assigned"])
        for sid, (grade, _) in audit["auto_assigned_same_grade"].items():
            res[sid] = grade
        return res


if __name__ == "__main__":
    main()
