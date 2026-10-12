#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
學生成績管理系統 - 仲裁與防呆引擎 (Engine)
實現純函數/無副作用的核心匹配、重複提交檢驗、配額審計與衝突消解。
"""

import re
from typing import Dict, List, Tuple, Any
from collections import defaultdict
from .models import Student, Roster


class GradeEngine:
    """成績仲裁與防呆引擎"""

    @staticmethod
    def match_token(token: str, roster: Roster) -> Tuple[List[Student], str]:
        """
        將輸入 token 匹配到學生：
        1. 完整 9 碼學號 (115423001)
        2. 帶學制快捷標記 (1博, 01碩, 4博, 7碩)
        3. 後兩碼/三碼數字 (01, 1, 59)
        4. 姓名精確比對
        5. 姓名包含/簡稱 (如 "聲樂" in "吳聲樂")
        """
        token = token.strip()
        if not token:
            return [], "empty"

        # 1. 完整學號比對
        if token in roster.by_sid:
            return [roster.by_sid[token]], "exact_id"

        # 2. 帶學制標記
        m_prog = re.match(r"^(\d{1,3})(博|碩)$", token)
        if m_prog:
            num, prog_flag = m_prog.group(1), m_prog.group(2)
            suffix = num[-2:].zfill(2)
            prog_name = "博班" if prog_flag == "博" else "碩班"
            candidates = roster.by_suffix.get(suffix, [])
            matched = [c for c in candidates if c.program == prog_name]
            if matched:
                return matched, f"suffix_{prog_name}"

        # 3. 純數字末兩碼/三碼
        if token.isdigit():
            suffix = token[-2:].zfill(2)
            if suffix in roster.by_suffix:
                return roster.by_suffix[suffix], "suffix"
            return [], "not_found"

        # 4. 姓名精確比對
        exact_names = roster.by_name.get(token, [])
        if exact_names:
            return exact_names, "exact_name"

        # 5. 姓名包含/模糊比對
        partial = [s for s in roster.students if token in s.name]
        if partial:
            return partial, "partial_name"

        return [], "not_found"

    @classmethod
    def audit_submissions(cls, submissions: List[Tuple[str, str]], roster: Roster) -> Dict[str, Any]:
        """
        審計所有提交項目，分類為：
        - auto_assigned: 唯一且無衝突的指派 {sid: grade}
        - auto_assigned_same_grade: 重複號碼且同等級自動配對的指派 {sid: grade}
        - duplicate_single_alerts: 單一學生被交了多次的嚴重警報 [AlertDict]
        - pending_conflicts: 需要確認的多候選人組別 [ConflictDict]
        - not_found: 未在名冊找到的項目 [(token, grade)]
        - unrecorded: 完全未登記/缺繳之學生列表 [Student]
        """
        single_student_map = defaultdict(list)  # sid -> list of (grade, token, student)
        suffix_map = defaultdict(list)          # suffix -> list of (grade, token, candidates)
        not_found = []

        for token, grade_label in submissions:
            matches, mtype = cls.match_token(token, roster)
            if not matches:
                not_found.append((token, grade_label))
            elif len(matches) == 1:
                s = matches[0]
                single_student_map[s.sid].append((grade_label, token, s))
            else:
                suffix = token[-2:].zfill(2) if token.isdigit() else token
                suffix_map[suffix].append((grade_label, token, matches))

        auto_assigned = {}
        duplicate_single_alerts = []

        # 1. 審查單一學生重複提交
        for sid, entries in single_student_map.items():
            s = entries[0][2]
            grades = [e[0] for e in entries]
            if len(entries) == 1:
                auto_assigned[sid] = grades[0]
            else:
                duplicate_single_alerts.append({
                    "student": s,
                    "grades": grades,
                    "tokens": [e[1] for e in entries],
                    "count": len(grades)
                })

        # 2. 審查多候選人組別
        auto_assigned_same_grade = {}
        pending_conflicts = []

        for suffix, entries in suffix_map.items():
            candidates = entries[0][2]
            grades = [e[0] for e in entries]

            # 情況 A：同等級且次數吻合候選人數 -> 自動安全配對
            if len(grades) == len(candidates) and len(set(grades)) == 1:
                target_grade = grades[0]
                for cand in candidates:
                    auto_assigned_same_grade[cand.sid] = (target_grade, cand)
            else:
                # 情況 B：次數超額或跨等級 -> 需確認
                pending_conflicts.append({
                    "suffix": suffix,
                    "grades": grades,
                    "candidates": candidates,
                    "is_over_quota": len(grades) > len(candidates)
                })

        # 合併確定名單以計算缺繳
        all_resolved_sids = set(auto_assigned.keys()) | set(auto_assigned_same_grade.keys())
        unrecorded = [s for s in roster.students if s.sid not in all_resolved_sids]

        return {
            "auto_assigned": auto_assigned,
            "auto_assigned_same_grade": auto_assigned_same_grade,
            "duplicate_single_alerts": duplicate_single_alerts,
            "pending_conflicts": pending_conflicts,
            "not_found": not_found,
            "unrecorded": unrecorded
        }
