#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
學生成績管理系統 - 命令列互動介面 (CLI)
負責終端輸入、選單確認、警報呈現與流程控制。
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .models import Roster
from .parser import GradeParser
from .engine import GradeEngine
from .exporter import GradeExporter


def run_interactive_audit(audit_data: Dict, roster: Roster) -> Dict[str, str]:
    """執行終端互動流程以解決衝突與警報"""
    final_assigned = dict(audit_data["auto_assigned"])

    # 加上同等級自動分配
    for sid, (grade, student) in audit_data["auto_assigned_same_grade"].items():
        final_assigned[sid] = grade
        print(f"  -> [自動配對] {sid} {student.name} ({student.program}) 登記為: {grade}")

    # 1. 處理單一學生超額警報
    alerts = audit_data["duplicate_single_alerts"]
    if alerts:
        print("\n" + "!" * 50)
        print(f"【🚨 嚴重警告：單一學生重複提交 / 疑似誤填學號】(共 {len(alerts)} 組)")
        for idx, alert in enumerate(alerts, 1):
            st = alert["student"]
            grades = alert["grades"]
            tokens = alert["tokens"]
            print(f"\n({idx}) 學生: {st.sid} {st.name} ({st.program})")
            print(f"    名冊中僅此 1 位同學，但本次輸入中出現了 {len(grades)} 次！")
            print(f"    輸入標記: {tokens} | 對應成績: {grades}")
            print(f"    ⚠️ 原因分析: 可能是該生被重複打分，或有其他同學誤填了該學號！")

            print(f"    >> 請選擇如何處理此學生成績：")
            for g_idx, g in enumerate(grades, 1):
                print(f"       輸入 {g_idx}: 採用成績 [{g}] (輸入為: {tokens[g_idx-1]})")
            print(f"       輸入 0: 暫不登記 (保留空白，留待查對)")

            while True:
                choice = input("    請選擇 (0/1/2...): ").strip()
                if choice == "0":
                    print(f"    [SKIP] 跳過 {st.name} 之成績，暫不寫入。")
                    break
                elif choice.isdigit() and 1 <= int(choice) <= len(grades):
                    chosen_grade = grades[int(choice) - 1]
                    final_assigned[st.sid] = chosen_grade
                    print(f"    [OK] 已設定 {st.name} -> {chosen_grade}")
                    break
                else:
                    print("    無效選項，請重新輸入！")

    # 2. 處理多候選人衝突
    conflicts = audit_data["pending_conflicts"]
    if conflicts:
        print(f"\n【需確認的重複名單】(共 {len(conflicts)} 組):")
        for idx, conf in enumerate(conflicts, 1):
            suffix = conf["suffix"]
            grades = conf["grades"]
            cands = conf["candidates"]

            is_over = conf["is_over_quota"]
            warning = f" ⚠️【警告：提交次數 ({len(grades)}) 大於候選人數 ({len(cands)})！】" if is_over else ""
            print(f"\n({idx}) 號碼 [{suffix}]: 本次出現的成績標記為 {grades}{warning}")
            print("    候選同學:")
            for c_idx, cand in enumerate(cands, 1):
                print(f"      [{c_idx}] {cand.sid} {cand.name} ({cand.program})")

            for grade in grades:
                print(f"\n  >> 請問獲得 [{grade}] 的是哪一位同學？")
                valid_choices = {str(i + 1): cands[i] for i in range(len(cands))}
                valid_choices["0"] = None
                for k, c in valid_choices.items():
                    if c:
                        print(f"     輸入 {k}: {c.name} ({c.sid} - {c.program})")
                    else:
                        print(f"     輸入 0: 暫不指定 / 跳過")

                while True:
                    choice = input("  請選擇 (0/1/2...): ").strip()
                    if choice in valid_choices:
                        chosen = valid_choices[choice]
                        if chosen:
                            final_assigned[chosen.sid] = grade
                            print(f"  [OK] 已設定 {chosen.sid} {chosen.name} ({chosen.program}) -> {grade}")
                        else:
                            print("  [SKIP] 跳過此筆登記。")
                        break
                    else:
                        print("  無效選項，請重新輸入！")

    # 3. 輸出缺繳統計
    resolved_sids = set(final_assigned.keys())
    missing = [s for s in roster.students if s.sid not in resolved_sids]
    print("\n" + "=" * 50)
    print("【缺繳 / 未登記名單統計】")
    if missing:
        print(f"共有 {len(missing)} 位同學本次未登記到成績：")
        for s in missing:
            print(f"  - {s.sid} {s.name} ({s.program}, 末兩碼: {s.suffix})")
    else:
        print(f"全班 {len(roster.students)} 位同學均已全數登記完畢！")

    return final_assigned


def main():
    import argparse
    parser = argparse.ArgumentParser(description="學生成績自動化登記與衝突比對系統 (Modular Edition)")
    parser.add_argument("--roster", default=None, help="指定課程學生名冊 CSV 路徑")
    parser.add_argument("--name", default=None, help="指定輸出檔案名稱字首（例如 HW1，預設為 grade_YYYYMMDD）")
    args, unknown = parser.parse_known_args()

    # 自動定位基準名冊
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"

    if args.roster:
        roster_path = Path(args.roster)
    else:
        roster_path = data_dir / "roster.csv" if data_dir.exists() else base_dir / "roster.csv"
        if not roster_path.exists():
            for fallback in [base_dir / "data.example" / "roster.example.csv"]:
                if fallback.exists():
                    roster_path = fallback
                    break

    roster = Roster(roster_path)
    print("=" * 60)
    print("  學生成績自動化登記與衝突比對系統 (Grade Auto-Recorder)")
    print(f"  名冊路徑: {roster_path.name} (共 {len(roster)} 位學生)")
    print("=" * 60)

    print("\n請選擇操作方式：")
    print("1. 貼上文字資料（支援多欄表格、快捷標記 1博/1碩、鍵值對）")
    print("2. 載入文字檔案 (.txt)")
    print("3. 更換/切換其他課程名冊")
    print("4. 結束離開")

    choice = input("\n請選擇 (1/2/3/4): ").strip()
    raw_text = ""

    if choice == "1":
        print("\n請貼上成績資料，貼上完成後輸入獨立一行的 'END' 並按 Enter 送出：")
        lines = []
        while True:
            try:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            except EOFError:
                break
        raw_text = "\n".join(lines)
    elif choice == "2":
        fpath = input("\n請輸入文字檔案路徑: ").strip()
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                raw_text = f.read()
        else:
            print("找不到該檔案！")
            return
    elif choice == "3":
        new_roster_path = input("\n請輸入新課程名冊 CSV 路徑: ").strip()
        if os.path.exists(new_roster_path):
            roster = Roster(Path(new_roster_path))
            print(f"[OK] 已成功載入新名冊: {new_roster_path} (共 {len(roster)} 人)")
            return
        else:
            print("找不到該名冊檔案！")
            return
    else:
        print("已結束程式。")
        return

    if not raw_text.strip():
        print("未輸入任何有效資料。")
        return

    submissions, fmt_type = GradeParser.extract_submissions(raw_text)
    if not submissions:
        print("[ERROR] 無法解析任何成績提交項目，請檢查格式。")
        return

    print(f"\n[INFO] 成功解析 {len(submissions)} 筆提交項目 (格式: {fmt_type})")
    audit = GradeEngine.audit_submissions(submissions, roster)

    final_map = run_interactive_audit(audit, roster)
    if final_map:
        custom_name = input(f"\n請輸入儲存檔名 (按 Enter 預設為 'grade_{datetime.now().strftime('%Y%m%d')}'): ").strip()
        col_name = input("請輸入成績欄位名稱 (按 Enter 預設為 '成績'): ").strip() or "成績"

        out_dir = data_dir if data_dir.exists() else base_dir
        csv_p, xlsx_p = GradeExporter.export_full(
            roster=roster,
            grades_map=final_map,
            output_dir=out_dir,
            custom_name=custom_name or None,
            column_name=col_name
        )
        print(f"\n[SUCCESS] CSV 寫入成功: {csv_p}")
        print(f"[SUCCESS] 美化 Excel 匯出成功: {xlsx_p}")
