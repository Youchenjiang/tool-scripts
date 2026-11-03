#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
學生成績管理系統 - 命令列介面 (CLI)
支援終端互動選單，以及完整的自動化命令列參數（--input, --audit, --resolve, --yes, --json）。
無論是真人助教互動、批次腳本或 AI 代理人皆能一鍵調用。
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from .models import Roster, Student
from .parser import GradeParser
from .engine import GradeEngine
from .exporter import GradeExporter


def parse_resolve_arg(resolve_str: str, roster: Roster) -> Tuple[Dict[str, str], List[str]]:
    """
    解析 --resolve 參數字串，支援：
    1. 鍵值對格式：'50=A+, 01碩=A, 01博=A+, 04博=A, 04碩=A+, 07碩=A, 07博=A+, 賴彥宏=A, 陳祈睿=A'
    2. 冒號或空白分隔：'50: A+; 115423001: A'
    3. JSON 字串：'{"115423050": "A+", "115423001": "A"}'
    """
    resolved = {}
    warnings = []
    resolve_str = resolve_str.strip()
    if not resolve_str:
        return resolved, warnings

    # 嘗試 JSON 解析
    if resolve_str.startswith("{") and resolve_str.endswith("}"):
        try:
            data = json.loads(resolve_str)
            for k, v in data.items():
                matches, _ = GradeEngine.match_token(str(k), roster)
                if len(matches) == 1:
                    resolved[matches[0].sid] = str(v).strip()
                elif len(matches) > 1:
                    warnings.append(f"標記 '{k}' 匹配到多位同學，請使用完整學號或加註學制（如 {k}碩/{k}博）")
                else:
                    warnings.append(f"找不到標記 '{k}' 對應的學生")
            return resolved, warnings
        except Exception:
            pass

    # 分割各項鍵值對 (支援逗號、分號、換行)
    items = [item.strip() for item in resolve_str.replace(";", ",").replace("\n", ",").split(",") if item.strip()]
    for item in items:
        if "=" in item:
            parts = item.split("=", 1)
        elif ":" in item:
            parts = item.split(":", 1)
        else:
            parts = item.split(None, 1)

        if len(parts) != 2:
            warnings.append(f"無法解析消解項: '{item}' (請使用 key=grade 格式)")
            continue

        token, grade = parts[0].strip(), parts[1].strip()
        matches, _ = GradeEngine.match_token(token, roster)
        if len(matches) == 1:
            resolved[matches[0].sid] = grade
        elif len(matches) > 1:
            warnings.append(f"標記 '{token}' 匹配到多位同學 ({[s.name for s in matches]})，請加註學制（如 {token}碩/{token}博）或使用學號")
        else:
            warnings.append(f"找不到標記 '{token}' 對應的學生")

    return resolved, warnings


def build_audit_report_data(
    audit_data: Dict[str, Any],
    roster: Roster,
    submissions: List[Tuple[str, str]],
    fmt_type: str
) -> Dict[str, Any]:
    """彙整審計數據結構"""
    grade_counts = {}
    for _, g in submissions:
        grade_counts[g] = grade_counts.get(g, 0) + 1

    conflict_cands = set()
    for conf in audit_data.get("pending_conflicts", []):
        for c in conf["candidates"]:
            conflict_cands.add(c.sid)

    true_missing = [s for s in audit_data.get("unrecorded", []) if s.sid not in conflict_cands]

    auto_same = [
        {"sid": cand.sid, "name": cand.name, "program": cand.program, "grade": grade}
        for sid, (grade, cand) in audit_data.get("auto_assigned_same_grade", {}).items()
    ]

    single_alerts = [
        {
            "sid": alert["student"].sid,
            "name": alert["student"].name,
            "program": alert["student"].program,
            "count": alert["count"],
            "grades": alert["grades"],
            "tokens": alert["tokens"]
        }
        for alert in audit_data.get("duplicate_single_alerts", [])
    ]

    conflicts = [
        {
            "suffix": conf["suffix"],
            "grades": conf["grades"],
            "is_over_quota": conf["is_over_quota"],
            "candidates": [
                {"sid": c.sid, "name": c.name, "program": c.program}
                for c in conf["candidates"]
            ]
        }
        for conf in audit_data.get("pending_conflicts", [])
    ]

    missing = [
        {"sid": s.sid, "name": s.name, "program": s.program, "suffix": s.suffix}
        for s in true_missing
    ]

    return {
        "total_submissions": len(submissions),
        "format_type": fmt_type,
        "grade_counts": grade_counts,
        "auto_assigned_count": len(audit_data.get("auto_assigned", {})),
        "auto_assigned_same_grade": auto_same,
        "duplicate_single_alerts": single_alerts,
        "pending_conflicts": conflicts,
        "missing_students": missing,
        "not_found": audit_data.get("not_found", [])
    }


def print_audit_report_text(report: Dict[str, Any]):
    """輸出易讀的人類/代理人審計文字報告"""
    print("\n" + "=" * 60)
    print("  學生成績審計報告 (Grade Audit Report)")
    print("=" * 60)
    print(f"輸入格式: {report['format_type']} | 總解析筆數: {report['total_submissions']} 筆")
    print(f"等第分布: {report['grade_counts']}")

    auto_same = report["auto_assigned_same_grade"]
    print(f"\n【自動安全配對 (同等第免確認)】(共 {len(auto_same)} 人):")
    if auto_same:
        for item in auto_same:
            print(f"  -> [自動配對] {item['sid']} {item['name']} ({item['program']}) -> {item['grade']}")
    else:
        print("  (無)")

    single_alerts = report["duplicate_single_alerts"]
    if single_alerts:
        print("\n" + "!" * 60)
        print(f"【🚨 嚴重警告：單一學生重複提交 / 疑似誤填學號】(共 {len(single_alerts)} 組):")
        for idx, alert in enumerate(single_alerts, 1):
            print(f"  ({idx}) {alert['sid']} {alert['name']} ({alert['program']})")
            print(f"      名冊中僅此 1 位同學，但出現了 {alert['count']} 次！標記: {alert['tokens']} | 成績: {alert['grades']}")

    conflicts = report["pending_conflicts"]
    if conflicts:
        print(f"\n【⚠️ 需確認的重複名單 / 跨等級碰撞】(共 {len(conflicts)} 組):")
        for idx, conf in enumerate(conflicts, 1):
            warning = " ⚠️ [提交次數大於候選人數!]" if conf["is_over_quota"] else ""
            print(f"  ({idx}) 號碼 [{conf['suffix']}]: 出現等第 = {conf['grades']}{warning}")
            for c in conf["candidates"]:
                print(f"      - 候選人: {c['sid']} {c['name']} ({c['program']})")

    not_found = report["not_found"]
    if not_found:
        print(f"\n【❓ 未在名冊中找到的輸入項目】(共 {len(not_found)} 筆):")
        for token, grade in not_found:
            print(f"  - 標記: {token} (等第: {grade})")

    missing = report["missing_students"]
    print(f"\n【缺繳 / 未登記名單】(共 {len(missing)} 人):")
    if missing:
        for s in missing:
            print(f"  - {s['sid']} {s['name']} ({s['program']}, 末兩碼: {s['suffix']})")
    else:
        print("  全班所有同學皆已出現在名單中！")
    print("=" * 60 + "\n")


def run_interactive_audit(audit_data: Dict, roster: Roster) -> Dict[str, str]:
    """執行終端互動流程以解決衝突與警報（真人助教互動模式）"""
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
    parser = argparse.ArgumentParser(
        description="學生成績自動化登記與衝突比對系統 (Grade Auto-Recorder)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例使用方式：
  1. 人工互動模式 (選單操作):
     python run.py

  2. 非互動審計模式 (僅輸出分析與衝突報告):
     python run.py -i raw_grades.txt --audit

  3. 批次消解並一鍵產出檔案:
     python run.py -i raw_grades.txt --resolve "50=A+, 01碩=A, 01博=A+, 04博=A, 04碩=A+, 07碩=A, 07博=A+, 賴彥宏=A" -o grade_20261103 -y

  4. 管線串接模式 (Piping / Stdin):
     cat raw_grades.txt | python run.py --audit --json
        """
    )
    parser.add_argument("-i", "--input", default=None, help="成績輸入來源：可為文字檔案路徑、直接傳入之字串，或 '-' 代表 stdin")
    parser.add_argument("--roster", default=None, help="指定課程名冊 CSV 路徑")
    parser.add_argument("-o", "--output", "--name", dest="name", default=None, help="指定輸出檔案名稱字首（例如 grade_20261103）")
    parser.add_argument("-c", "--column", default="成績", help="指定成績欄位名稱（預設：成績）")
    parser.add_argument("--audit", action="store_true", help="審計模式：僅執行分析並輸出報告，不寫入檔案")
    parser.add_argument("--resolve", default=None, help="消解衝突與補登字串（例如 '50=A+, 01碩=A, 01博=A+, 賴彥宏=A'）")
    parser.add_argument("-y", "--yes", "--non-interactive", dest="non_interactive", action="store_true", help="非互動批次模式：跳過所有終端確認，直接產出檔案")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式輸出審計或執行結果（適合程式與代理人串接）")

    args = parser.parse_args()

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

    if not roster_path.exists():
        print(f"[ERROR] 找不到課程名冊: {roster_path}")
        sys.exit(1)

    roster = Roster(roster_path)

    # 1. 取得 raw_text 輸入內容
    raw_text = ""
    is_interactive = False

    if args.input:
        if args.input == "-":
            raw_text = sys.stdin.read()
        elif os.path.isfile(args.input):
            with open(args.input, "r", encoding="utf-8") as f:
                raw_text = f.read()
        else:
            raw_text = args.input
    elif not sys.stdin.isatty():
        raw_text = sys.stdin.read()
    else:
        # 真人互動選單
        is_interactive = True
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
                sys.exit(1)
        elif choice == "3":
            new_roster_path = input("\n請輸入新課程名冊 CSV 路徑: ").strip()
            if os.path.exists(new_roster_path):
                roster = Roster(Path(new_roster_path))
                print(f"[OK] 已成功載入新名冊: {new_roster_path} (共 {len(roster)} 人)")
                return
            else:
                print("找不到該名冊檔案！")
                sys.exit(1)
        else:
            print("已結束程式。")
            return

    if not raw_text.strip():
        print("[ERROR] 未輸入任何有效資料。")
        sys.exit(1)

    # 2. 解析資料
    submissions, fmt_type = GradeParser.extract_submissions(raw_text)
    if not submissions:
        print("[ERROR] 無法解析任何成績提交項目，請檢查格式。")
        sys.exit(1)

    # 3. 審計分析
    audit = GradeEngine.audit_submissions(submissions, roster)
    report_data = build_audit_report_data(audit, roster, submissions, fmt_type)

    # 4. 若為 --audit 模式，輸出報告後直接退出
    if args.audit:
        if args.json:
            print(json.dumps(report_data, ensure_ascii=False, indent=2))
        else:
            print_audit_report_text(report_data)
        sys.exit(0)

    # 5. 彙整最終登記名單
    final_assigned = dict(audit["auto_assigned"])
    for sid, (grade, cand) in audit.get("auto_assigned_same_grade", {}).items():
        final_assigned[sid] = grade

    # 套用 --resolve 參數
    if args.resolve:
        resolved_items, warnings = parse_resolve_arg(args.resolve, roster)
        if not args.json:
            for warn in warnings:
                print(f"[WARNING] {warn}")
            for sid, grade in resolved_items.items():
                final_assigned[sid] = grade
                st = roster.by_sid.get(sid)
                name_str = f" {st.name}" if st else ""
                print(f"[RESOLVE] 已指定 {sid}{name_str} -> {grade}")
        else:
            for sid, grade in resolved_items.items():
                final_assigned[sid] = grade

    # 檢查是否仍有未消解的衝突
    has_unresolved_alerts = any(
        alert["student"].sid not in final_assigned
        for alert in audit.get("duplicate_single_alerts", [])
    )
    has_unresolved_conflicts = any(
        any(cand.sid not in final_assigned for cand in conf["candidates"])
        for conf in audit.get("pending_conflicts", [])
    )

    if (has_unresolved_alerts or has_unresolved_conflicts) and not args.non_interactive:
        if sys.stdin.isatty():
            # 互動式消解剩餘衝突
            final_assigned = run_interactive_audit(audit, roster)
        elif not args.json:
            print("[WARNING] 偵測到未消解的衝突或警報，但在非互動環境中未提供完整 --resolve，將僅記錄已確認之成績。")

    # 6. 匯出檔案
    out_dir = data_dir if data_dir.exists() else base_dir
    today_str = datetime.now().strftime("%Y%m%d")
    default_name = f"grade_{today_str}"

    if args.name:
        custom_name = args.name.strip()
    elif not is_interactive or args.non_interactive:
        custom_name = default_name
    else:
        custom_name = input(f"\n請輸入儲存檔名 (按 Enter 預設為 '{default_name}'): ").strip() or default_name

    col_name = args.column or "成績"

    csv_p, xlsx_p = GradeExporter.export_full(
        roster=roster,
        grades_map=final_assigned,
        output_dir=out_dir,
        custom_name=custom_name,
        column_name=col_name
    )

    missing_students = [s for s in roster.students if s.sid not in final_assigned]

    if args.json:
        result_json = {
            "status": "success",
            "csv_path": str(csv_p),
            "xlsx_path": str(xlsx_p),
            "total_roster": len(roster.students),
            "recorded_count": len(final_assigned),
            "missing_count": len(missing_students),
            "missing_students": [{"sid": s.sid, "name": s.name} for s in missing_students]
        }
        print(json.dumps(result_json, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 50)
        print(f"[SUCCESS] CSV 寫入成功: {csv_p}")
        print(f"[SUCCESS] 美化 Excel 匯出成功: {xlsx_p}")
        print(f"[INFO] 總學生數: {len(roster.students)} | 已登記: {len(final_assigned)} | 缺繳: {len(missing_students)}")
        if missing_students:
            print("【缺繳同學】:")
            for s in missing_students:
                print(f"  - {s.sid} {s.name} ({s.program})")
        print("=" * 50)


if __name__ == "__main__":
    main()
