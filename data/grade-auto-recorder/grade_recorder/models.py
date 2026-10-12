#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
學生成績管理系統 - 資料模型 (Models)
定義 Student 與 Roster 資料結構，支援學號前綴學制推導與多維度索引。
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict


class Student:
    """學生資料模型"""
    def __init__(self, sid: str, name: str, program: Optional[str] = None):
        self.sid = sid.strip()
        self.name = name.strip()
        self.suffix = self.sid[-2:] if len(self.sid) >= 2 else self.sid
        self.program = program or self.infer_program(self.sid)

    @staticmethod
    def infer_program(sid: str) -> str:
        """依學號特徵推導學制（博士班 / 碩士班）"""
        if len(sid) >= 6:
            code = sid[3:6]
            if "83" in code or code.startswith("8"):
                return "博班"
            elif "23" in code or code.startswith("2"):
                return "碩班"
        return "一般"

    def __repr__(self) -> str:
        return f"Student({self.sid}, {self.name}, {self.program})"

    def to_dict(self) -> Dict[str, str]:
        return {
            "帳號": self.sid,
            "姓名": self.name,
            "學制": self.program,
            "末兩碼": self.suffix
        }


class Roster:
    """課程名冊模型，提供學號、末兩碼、姓名等多維度快速索引"""
    def __init__(self, csv_path: Path):
        self.csv_path = Path(csv_path)
        self.students: List[Student] = []
        self.by_sid: Dict[str, Student] = {}
        self.by_suffix: Dict[str, List[Student]] = defaultdict(list)
        self.by_name: Dict[str, List[Student]] = defaultdict(list)
        self.load()

    def load(self) -> None:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"找不到學生名冊檔案: {self.csv_path}")

        self.students.clear()
        self.by_sid.clear()
        self.by_suffix.clear()
        self.by_name.clear()

        with open(self.csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sid = row.get("帳號", "").strip()
                name = row.get("姓名", "").strip()
                if not sid:
                    continue
                student = Student(sid=sid, name=name)
                self.students.append(student)
                self.by_sid[student.sid] = student
                self.by_suffix[student.suffix].append(student)
                self.by_name[student.name].append(student)

    def __len__(self) -> int:
        return len(self.students)
