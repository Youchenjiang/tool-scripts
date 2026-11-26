#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""單元測試 - GradeEngine 核心防呆仲裁測試"""

import sys
import unittest
from pathlib import Path

_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from grade_recorder.models import Roster
from grade_recorder.engine import GradeEngine


class TestGradeEngine(unittest.TestCase):
    def setUp(self):
        base_dir = Path(__file__).resolve().parent.parent
        example_csv = base_dir / "data.example" / "roster.example.csv"
        self.roster = Roster(example_csv)

    def test_single_student_over_quota_alert(self):
        """測試單一學生重複提交（一人相符卻交了多次）是否精準觸發嚴重警報"""
        # 04 在範例名冊中只有 115423004 林志強 1 人
        submissions = [("04", "A+"), ("04", "A-")]
        audit = GradeEngine.audit_submissions(submissions, self.roster)

        # 驗證不會自動分配到 auto_assigned
        self.assertNotIn("115423004", audit["auto_assigned"])
        # 驗證被加入 duplicate_single_alerts
        alerts = audit["duplicate_single_alerts"]
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["student"].sid, "115423004")
        self.assertEqual(alerts[0]["count"], 2)
        self.assertEqual(alerts[0]["grades"], ["A+", "A-"])

    def test_smart_suffix_recognition(self):
        """測試 1博、1碩 快捷後綴識別"""
        # 01 有 115423001 王小明 (碩) 與 115483001 張小美 (博)
        matches_phd, mtype1 = GradeEngine.match_token("1博", self.roster)
        self.assertEqual(len(matches_phd), 1)
        self.assertEqual(matches_phd[0].sid, "115483001")

        matches_master, mtype2 = GradeEngine.match_token("1碩", self.roster)
        self.assertEqual(len(matches_master), 1)
        self.assertEqual(matches_master[0].sid, "115423001")

    def test_collision_same_grade_auto_assign(self):
        """測試重複號碼同等級次數吻合時，自動安全配對"""
        # 02 有 2 位學生：陳大華 (碩) 與 李雅婷 (博)
        submissions = [("02", "A"), ("02", "A")]
        audit = GradeEngine.audit_submissions(submissions, self.roster)

        same_grade = audit["auto_assigned_same_grade"]
        self.assertIn("115423002", same_grade)
        self.assertIn("115483002", same_grade)
        self.assertEqual(same_grade["115423002"][0], "A")
        self.assertEqual(same_grade["115483002"][0], "A")


    def test_deductive_auto_resolution(self):
        """測試具名定錨後，同組純數字自動排除法配對給剩餘候選人"""
        # 02 候選人為 115423002 陳大華 (碩) 與 115483002 李雅婷 (博)
        # 陳大華以姓名具名提交獲得 A，純數字 02 獲得 A+
        submissions = [("陳大華", "A"), ("02", "A+")]
        audit = GradeEngine.audit_submissions(submissions, self.roster)

        # 驗證陳大華直接進入 auto_assigned
        self.assertEqual(audit["auto_assigned"].get("115423002"), "A")
        # 驗證李雅婷透過排除法進入 auto_assigned_deductive 獲得 A+
        deductive = audit["auto_assigned_deductive"]
        self.assertIn("115483002", deductive)
        grade, cand, reason = deductive["115483002"]
        self.assertEqual(grade, "A+")
        self.assertEqual(cand.name, "李雅婷")
        # 驗證 pending_conflicts 不含 02
        self.assertEqual(len(audit["pending_conflicts"]), 0)

    def test_surname_unique_match(self):
        """測試全班唯一姓氏單字簡稱直接精確匹配"""
        # 在範例名冊中，姓「林」者僅有 115423004 林志強
        matches, mtype = GradeEngine.match_token("林", self.roster)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].sid, "115423004")
        self.assertEqual(mtype, "surname")

    def test_surname_deductive_resolution(self):
        """測試同姓氏多候選人時，當其中一位學號已出現，單字姓氏自動關聯至未出現之同學"""
        import tempfile
        # 建立含兩位同姓「朱」同學的測試名冊
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8-sig", delete=False, suffix=".csv") as tf:
            tf.write("帳號,姓名\n")
            tf.write("115423058,朱大智\n")
            tf.write("115423082,朱小勇\n")
            tf_path = Path(tf.name)

        try:
            chu_roster = Roster(tf_path)
            # 58 號以學號後綴提交 A+，另一項以姓氏簡稱「朱」提交 A
            submissions = [("58", "A+"), ("朱", "A")]
            audit = GradeEngine.audit_submissions(submissions, chu_roster)

            # 驗證 58 號朱大智直接配對 A+
            self.assertEqual(audit["auto_assigned"].get("115423058"), "A+")
            # 驗證「朱」透過排除法自動關聯給未出現的朱小勇 (115423082)，獲得 A
            deductive = audit["auto_assigned_deductive"]
            self.assertIn("115423082", deductive)
            grade, cand, reason = deductive["115423082"]
            self.assertEqual(grade, "A")
            self.assertEqual(cand.name, "朱小勇")
            self.assertIn("同姓同學", reason)
            # 驗證無衝突殘留
            self.assertEqual(len(audit["pending_conflicts"]), 0)
        finally:
            if tf_path.exists():
                tf_path.unlink()


    def test_smart_typo_guess_alert(self):
        """測試單人重複提交且缺繳人數 <= 2 時自動生成智慧筆誤猜測"""
        # 範例名冊有 5 位學生：
        # 115423001, 115423002, 115423004, 115483001, 115483002
        # 若 115423004 被重複提交兩次，115423001, 115483001, 115483002 正常提交
        # 只有 115423002 (陳大華) 缺繳 (缺繳人數為 1 <= 2)
        submissions = [
            ("04", "A+"),
            ("04", "A"),
            ("1碩", "A"),
            ("1博", "A+"),
            ("2博", "A")
        ]
        audit = GradeEngine.audit_submissions(submissions, self.roster)
        alerts = audit["duplicate_single_alerts"]
        self.assertEqual(len(alerts), 1)
        # 驗證智慧筆誤猜測清單包含缺繳的 115423002 陳大華
        guesses = alerts[0]["typo_guesses"]
        self.assertEqual(len(guesses), 1)
        self.assertEqual(guesses[0].sid, "115423002")


if __name__ == "__main__":
    unittest.main()
