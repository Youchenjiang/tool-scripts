#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""單元測試 - GradeEngine 核心防呆仲裁測試"""

import unittest
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
