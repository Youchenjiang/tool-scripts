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
        5. 姓名包含/簡稱 (如 "大明" in "王大明")
        6. 近似姓名比對 (容許 1 個錯別字，例如 陳祈睿 vs 陳祈叡)
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

        # 4.5 單字姓氏比對 (優先比對以該字為姓氏的同學，避免匹配到名中含該字者)
        if len(token) == 1 and '\u4e00' <= token <= '\u9fff':
            surname_matches = [s for s in roster.students if s.name.startswith(token)]
            if surname_matches:
                return surname_matches, "surname"

        # 5. 姓名包含/模糊比對
        partial = [s for s in roster.students if token in s.name]
        if partial:
            return partial, "partial_name"

        # 6. 近似姓名比對 (同長度容許 1 個錯別字，例如 陳祈睿 vs 陳祈叡)
        if len(token) >= 2:
            near_matches = []
            for s in roster.students:
                if len(s.name) == len(token):
                    diff = sum(1 for c1, c2 in zip(token, s.name) if c1 != c2)
                    if diff == 1:
                        near_matches.append(s)
            if len(near_matches) == 1:
                return near_matches, "near_name"

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

        # 2. 審查多候選人組別（含同等級配對與排除法自動定錨）
        auto_assigned_same_grade = {}
        auto_assigned_deductive = {}
        pending_conflicts = []

        all_resolved_sids = (
            set(auto_assigned.keys())
            | set(auto_assigned_same_grade.keys())
            | set(auto_assigned_deductive.keys())
        )

        unresolved_suffixes = dict(suffix_map)
        changed = True

        while changed:
            changed = False
            for suffix in list(unresolved_suffixes.keys()):
                entries = unresolved_suffixes[suffix]
                candidates = entries[0][2]
                grades = [e[0] for e in entries]

                # 檢查候選人中是否已有被鎖定者 (anchored)
                anchored_cands = [c for c in candidates if c.sid in all_resolved_sids]
                remaining_cands = [c for c in candidates if c.sid not in all_resolved_sids]

                # 排除法條件：若有候選人已被定錨，且剩餘未定錨候選人數等於未定錨提交數
                if anchored_cands and len(remaining_cands) == len(grades):
                    anchored_names = "、".join(c.name for c in anchored_cands)
                    is_surname_group = not suffix.isdigit()
                    peer_desc = f"同姓同學 {anchored_names} 已由學號/代碼鎖定" if is_surname_group else f"同組 {anchored_names} 已由精確標記鎖定"

                    if len(remaining_cands) == 1:
                        target = remaining_cands[0]
                        auto_assigned_deductive[target.sid] = (
                            grades[0],
                            target,
                            peer_desc
                        )
                        all_resolved_sids.add(target.sid)
                        del unresolved_suffixes[suffix]
                        changed = True
                        continue
                    elif len(set(grades)) == 1:
                        for target in remaining_cands:
                            auto_assigned_deductive[target.sid] = (
                                grades[0],
                                target,
                                peer_desc + "且等第相同"
                            )
                            all_resolved_sids.add(target.sid)
                        del unresolved_suffixes[suffix]
                        changed = True
                        continue

                # 情況 A：同等級且次數吻合候選人數 -> 自動安全配對
                if len(grades) == len(candidates) and len(set(grades)) == 1:
                    target_grade = grades[0]
                    for cand in candidates:
                        auto_assigned_same_grade[cand.sid] = (target_grade, cand)
                        all_resolved_sids.add(cand.sid)
                    del unresolved_suffixes[suffix]
                    changed = True
                    continue

        # 迴圈收斂後，仍無法自動消解的組別放入 pending_conflicts
        for suffix, entries in unresolved_suffixes.items():
            candidates = entries[0][2]
            grades = [e[0] for e in entries]
            anchored_cands = [c for c in candidates if c.sid in all_resolved_sids]
            remaining_cands = [c for c in candidates if c.sid not in all_resolved_sids]
            effective_cands = remaining_cands if anchored_cands else candidates
            pending_conflicts.append({
                "suffix": suffix,
                "grades": grades,
                "candidates": effective_cands,
                "is_over_quota": len(grades) > len(effective_cands)
            })

        unrecorded = [s for s in roster.students if s.sid not in all_resolved_sids]

        # 3. 智慧筆誤猜測 (當單一學生超額提交且缺繳人數 <= 2 時)
        if duplicate_single_alerts and len(unrecorded) <= 3 and len(unrecorded) > 0:
            for alert in duplicate_single_alerts:
                alert["typo_guesses"] = [s for s in unrecorded if s.sid != alert["student"].sid]
        else:
            for alert in duplicate_single_alerts:
                alert["typo_guesses"] = []

        return {
            "auto_assigned": auto_assigned,
            "auto_assigned_same_grade": auto_assigned_same_grade,
            "auto_assigned_deductive": auto_assigned_deductive,
            "duplicate_single_alerts": duplicate_single_alerts,
            "pending_conflicts": pending_conflicts,
            "not_found": not_found,
            "unrecorded": unrecorded
        }
