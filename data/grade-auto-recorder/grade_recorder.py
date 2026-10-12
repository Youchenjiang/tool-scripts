#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
學生成績自動化登記與衝突比對系統 (Grade Auto-Recorder v2)

核心特色：
1. 獨立作業存檔：每次作業自動以日期命名分檔（如 grade_20260915.xlsx），避免歷史紀錄被覆蓋。
2. 支援多門課程替換：可自訂基準名冊（預設 roster.csv，亦可指定其他課程名冊）。
3. 碩博智慧辨識：
   - 輸入支援快捷後綴（如 "1博 A+"、"1碩 A"），直接精準配對免確認！
   - 衝突確認選單自動標示 "(碩班)"、"(博班)"。
4. Excel 自動美化匯出：每次存檔自動同步導出格式美觀的 XLSX 檔案。
"""

import os
import sys
import csv
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# 確保在 Windows 控制台正確輸出 UTF-8 中文字
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_ROSTER_CSV = DATA_DIR / "roster.csv" if DATA_DIR.exists() else BASE_DIR / "roster.csv"


class GradeRecorder:
    def __init__(self, roster_path=DEFAULT_ROSTER_CSV):
        self.roster_path = Path(roster_path)
        # 若無 roster.csv 則依序尋找備用路徑
        if not self.roster_path.exists():
            for fallback in [
                DATA_DIR / "roster.csv",
                BASE_DIR / "roster.csv",
                DATA_DIR / "grades.csv",
                BASE_DIR / "grades.csv",
                BASE_DIR / "data.example" / "roster.example.csv"
            ]:
                if fallback.exists():
                    self.roster_path = fallback
                    break

        self.students = []
        self.by_sid = {}
        self.by_suffix = defaultdict(list)
        self.load_students()

    def get_program_type(self, sid: str) -> str:
        """依學號特徵辨識學制（博班 / 碩班）"""
        if len(sid) >= 6:
            code = sid[3:6]
            if "83" in code or code.startswith("8"):
                return "博班"
            elif "23" in code or code.startswith("2"):
                return "碩班"
        return ""

    def load_students(self):
        """載入基準名冊並建立多重索引"""
        if not self.roster_path.exists():
            raise FileNotFoundError(f"找不到學生名冊檔案: {self.roster_path}")

        self.students = []
        self.by_sid.clear()
        self.by_suffix.clear()

        with open(self.roster_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sid = row.get("帳號", "").strip()
                name = row.get("姓名", "").strip()
                if not sid:
                    continue
                suffix = sid[-2:]
                program = self.get_program_type(sid)
                student_info = {
                    "帳號": sid,
                    "姓名": name,
                    "學制": program,
                    "raw": row
                }
                self.students.append(student_info)
                self.by_sid[sid] = student_info
                self.by_suffix[suffix].append(student_info)

    def match_item(self, token: str):
        """
        將輸入 token 匹配到學生：
        支援：
        - 完整學號 (115423001)
        - 帶學制快捷標記 (1博、01碩、4博、7碩)
        - 後兩碼 (01, 1, 59)
        - 姓名或簡稱 (王大明、聲樂)
        """
        token = token.strip()
        if not token:
            return [], "empty"

        # 1. 完整學號 (9碼)
        if token in self.by_sid:
            return [self.by_sid[token]], "exact_id"

        # 2. 帶學制標記 (例如 "1博", "01碩", "04博", "4碩")
        m_prog = re.match(r"^(\d{1,3})(博|碩)$", token)
        if m_prog:
            num, prog_flag = m_prog.group(1), m_prog.group(2)
            suffix = num[-2:].zfill(2)
            prog_name = "博班" if prog_flag == "博" else "碩班"
            candidates = self.by_suffix.get(suffix, [])
            matched = [c for c in candidates if c["學制"] == prog_name]
            if matched:
                return matched, f"suffix_{prog_name}"

        # 3. 純數字且長度 <= 3 (末兩碼/末三碼)
        if token.isdigit():
            suffix = token[-2:].zfill(2)
            if suffix in self.by_suffix:
                return self.by_suffix[suffix], "suffix"
            return [], "not_found"

        # 4. 姓名精確比對
        exact_names = [s for s in self.students if s["姓名"] == token]
        if exact_names:
            return exact_names, "exact_name"

        # 5. 姓名包含/簡稱比對 (如 "大明" in "王大明")
        partial_names = [s for s in self.students if token in s["姓名"]]
        if partial_names:
            return partial_names, "partial_name"

        return [], "not_found"

    def parse_multi_column_table(self, text: str):
        """解析 Excel 多欄複製貼上格式 (A-, A, A+)"""
        lines = [line.rstrip("\r\n") for line in text.strip().splitlines() if line.strip()]
        if not lines:
            return None

        headers = [h.strip() for h in re.split(r"\t+", lines[0]) if h.strip()]
        is_header = len(headers) > 1 and not all(h.isdigit() for h in headers)
        if not is_header:
            return None

        col_data = defaultdict(list)
        for line in lines[1:]:
            cells = line.split("\t")
            for idx, cell in enumerate(cells):
                cell_val = cell.strip()
                if idx < len(headers) and cell_val:
                    col_data[headers[idx]].append(cell_val)
        return dict(col_data)

    def parse_key_value_lines(self, text: str):
        """解析單行鍵值對格式 (59 85、1博 A+)"""
        items = []
        for line in text.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = re.split(r"[\s,:\t]+", line)
            if len(parts) >= 2:
                items.append((parts[0], parts[1]))
        return items

    def process_data(self, input_text: str, interactive=True):
        col_data = self.parse_multi_column_table(input_text)
        assigned_results = {}
        suffix_occurrences = defaultdict(list)
        not_found_list = []

        # 收集所有原始提交項目 [(token, grade_label)]
        raw_items = []
        if col_data is not None:
            print("\n[INFO] 偵測到多欄表格格式，包含等級/欄位:", list(col_data.keys()))
            for grade_label, tokens in col_data.items():
                for token in tokens:
                    raw_items.append((token, grade_label))
        else:
            kv_items = self.parse_key_value_lines(input_text)
            if not kv_items:
                print("[ERROR] 無法識別輸入格式！")
                return None
            print(f"\n[INFO] 偵測到鍵值對格式，共 {len(kv_items)} 筆資料。")
            raw_items = kv_items

        # 分組與配對
        single_student_occurrences = defaultdict(list)  # sid -> list of (grade, token, student_info)
        suffix_occurrences = defaultdict(list)          # suffix -> list of (grade, token, candidates)
        not_found_list = []

        for token, grade_label in raw_items:
            matches, mtype = self.match_item(token)
            if not matches:
                not_found_list.append((token, grade_label))
            elif len(matches) == 1:
                s = matches[0]
                single_student_occurrences[s["帳號"]].append((grade_label, token, s))
            else:
                suffix = token[-2:].zfill(2) if token.isdigit() else token
                suffix_occurrences[suffix].append((grade_label, token, matches))

        print("\n" + "=" * 50)
        print("【比對結果分析】")

        if not_found_list:
            print(f"\n[警告] 以下項目未在名冊中找到:")
            for token, grade in not_found_list:
                print(f"  - 輸入標記: {token} (成績: {grade})")

        # 1. 檢查單一學生是否被重複提交 (一人相符卻交了多人/多次)
        duplicate_single_alerts = []
        for sid, entries in single_student_occurrences.items():
            s_info = entries[0][2]
            grades = [e[0] for e in entries]
            if len(entries) == 1:
                assigned_results[sid] = grades[0]
            else:
                duplicate_single_alerts.append({
                    "student": s_info,
                    "grades": grades,
                    "tokens": [e[1] for e in entries]
                })

        print(f"已自動匹配唯一且無衝突學生: {len(assigned_results)} 位")

        # 若發現單一學生重複提交，立即提出嚴重警報！
        if duplicate_single_alerts:
            print("\n" + "!" * 50)
            print(f"【🚨 嚴重警告：單一學生重複提交 / 疑似誤填學號】(共 {len(duplicate_single_alerts)} 組)")
            for idx, alert in enumerate(duplicate_single_alerts, 1):
                st = alert["student"]
                grades = alert["grades"]
                tokens = alert["tokens"]
                print(f"\n({idx}) 學生: {st['帳號']} {st['姓名']} ({st['學制']})")
                print(f"    名冊中僅此 1 位同學，但本次輸入中出現了 {len(grades)} 次！")
                print(f"    輸入標記: {tokens} | 對應成績: {grades}")
                print(f"    ⚠️ 原因分析: 可能是該生被重複打分，或有其他同學誤填了該學號！")

                if interactive:
                    print(f"    >> 請選擇如何處理此學生成績：")
                    for g_idx, g in enumerate(grades, 1):
                        print(f"       輸入 {g_idx}: 採用成績 [{g}] (輸入為: {tokens[g_idx-1]})")
                    print(f"       輸入 0: 暫不登記 (保留空白，留待查對)")

                    while True:
                        choice = input("    請選擇 (0/1/2...): ").strip()
                        if choice == "0":
                            print(f"    [SKIP] 跳過 {st['姓名']} 之成績，暫不寫入。")
                            break
                        elif choice.isdigit() and 1 <= int(choice) <= len(grades):
                            chosen_grade = grades[int(choice) - 1]
                            assigned_results[st["帳號"]] = chosen_grade
                            print(f"    [OK] 已設定 {st['姓名']} -> {chosen_grade}")
                            break
                        else:
                            print("    無效選項，請重新輸入！")

        # 2. 處理多候選人衝突
        pending_conflicts = []
        for suffix, entries in suffix_occurrences.items():
            candidates = entries[0][2]
            grades = [e[0] for e in entries]

            # 情況 A：同等級且次數剛好吻合候選人數 -> 自動全部分配
            if len(grades) == len(candidates) and len(set(grades)) == 1:
                target_grade = grades[0]
                print(f"\n[自動分配] 號碼 [{suffix}] 共有 {len(candidates)} 位候選人，且均登記為 [{target_grade}]：")
                for cand in candidates:
                    sid = cand["帳號"]
                    assigned_results[sid] = target_grade
                    print(f"  -> {sid} {cand['姓名']} ({cand['學制']}) 登記為: {target_grade}")
            else:
                # 情況 B：次數大於候選人數，或跨等級
                pending_conflicts.append({
                    "suffix": suffix,
                    "grades": grades,
                    "candidates": candidates
                })

        if pending_conflicts:
            print(f"\n【需確認的重複名單】(共 {len(pending_conflicts)} 組):")
            for idx, conf in enumerate(pending_conflicts, 1):
                suffix = conf["suffix"]
                grades = conf["grades"]
                cands = conf["candidates"]

                is_over_quota = len(grades) > len(cands)
                quota_warning = f" ⚠️【警告：提交次數 ({len(grades)}) 大於候選人數 ({len(cands)})！】" if is_over_quota else ""

                print(f"\n({idx}) 號碼 [{suffix}]: 本次出現的成績標記為 {grades}{quota_warning}")
                print("    候選同學:")
                for c_idx, cand in enumerate(cands, 1):
                    print(f"      [{c_idx}] {cand['帳號']} {cand['姓名']} ({cand['學制']})")

                if interactive:
                    for grade in grades:
                        print(f"\n  >> 請問獲得 [{grade}] 的是哪一位同學？")
                        valid_choices = {str(i + 1): cands[i] for i in range(len(cands))}
                        valid_choices["0"] = None
                        for k, c in valid_choices.items():
                            if c:
                                print(f"     輸入 {k}: {c['姓名']} ({c['帳號']} - {c['學制']})")
                            else:
                                print(f"     輸入 0: 暫不指定 / 跳過")

                        while True:
                            choice = input("  請選擇 (0/1/2...): ").strip()
                            if choice in valid_choices:
                                chosen = valid_choices[choice]
                                if chosen:
                                    assigned_results[chosen["帳號"]] = grade
                                    print(f"  [OK] 已設定 {chosen['帳號']} {chosen['姓名']} ({chosen['學制']}) -> {grade}")
                                else:
                                    print("  [SKIP] 跳過此筆登記。")
                                break
                            else:
                                print("  無效選項，請重新輸入！")

        # 統計未登記名單
        unrecorded = [s for s in self.students if s["帳號"] not in assigned_results]
        print("\n" + "=" * 50)
        print("【缺繳 / 未登記名單】")
        if unrecorded:
            print(f"共有 {len(unrecorded)} 位同學本次未登記到成績：")
            for s in unrecorded:
                print(f"  - {s['帳號']} {s['姓名']} ({s['學制']}, 末兩碼: {s['帳號'][-2:]})")
        else:
            print(f"全班 {len(self.students)} 位同學均已全數登記！")

        return assigned_results

    def save_results(self, assigned_results: dict, custom_name=None, column_name="成績"):
        """
        儲存成績：
        預設檔名：grade_YYYYMMDD.csv 與 grade_YYYYMMDD.xlsx
        """
        today_str = datetime.now().strftime("%Y%m%d")
        file_prefix = custom_name.strip() if custom_name else f"grade_{today_str}"

        target_dir = DATA_DIR if DATA_DIR.exists() else BASE_DIR
        target_dir.mkdir(exist_ok=True)

        csv_filename = f"{file_prefix}.csv"
        csv_path = target_dir / csv_filename

        rows = []
        for s in self.students:
            sid = s["帳號"]
            score = assigned_results.get(sid, "")
            rows.append({
                "帳號": sid,
                "姓名": s["姓名"],
                column_name: score,
                "備註": ""
            })

        fieldnames = ["帳號", "姓名", column_name, "備註"]
        with open(csv_path, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"\n[SUCCESS] 成績已成功寫入 CSV: {csv_path}")

        # 同步導出 Excel
        try:
            from export_excel import convert_csv_to_excel
            xlsx_path = target_dir / f"{file_prefix}.xlsx"
            convert_csv_to_excel(csv_path=csv_path, xlsx_path=xlsx_path)
        except Exception as e:
            print(f"[WARN] 自動導出 Excel 失敗: {e}")

        return csv_path


def demo_or_cli():
    import argparse
    parser = argparse.ArgumentParser(description="學生成績自動化登記與衝突比對系統")
    parser.add_argument("--roster", default=str(DEFAULT_ROSTER_CSV), help="指定課程學生名冊 CSV 路徑")
    parser.add_argument("--name", default=None, help="指定輸出檔案名稱字首（例如 HW1，預設為 grade_YYYYMMDD）")
    args, unknown = parser.parse_known_args()

    recorder = GradeRecorder(roster_path=args.roster)
    print("=" * 60)
    print("  學生成績自動化登記與衝突比對系統 v2")
    print(f"  目前基準名冊: {Path(recorder.roster_path).name} (共 {len(recorder.students)} 位學生)")
    print("=" * 60)

    print("\n請選擇操作方式：")
    print("1. 貼上文字資料（支援多欄表格或鍵值對，支援 1博/1碩 快捷輸入）")
    print("2. 載入文字檔案 (.txt)")
    print("3. 更換/切換其他課程名單")
    print("4. 退出")
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
        text = "\n".join(lines)
        if text.strip():
            results = recorder.process_data(text, interactive=True)
            if results:
                custom_name = input(f"\n請輸入儲存檔名 (直接按 Enter 預設為 'grade_{datetime.now().strftime('%Y%m%d')}'): ").strip()
                col_name = input("請輸入成績欄位名稱 (直接按 Enter 預設為 '成績'): ").strip() or "成績"
                recorder.save_results(results, custom_name=custom_name or None, column_name=col_name)
    elif choice == "2":
        fpath = input("\n請輸入文字檔案路徑: ").strip()
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            results = recorder.process_data(content, interactive=True)
            if results:
                custom_name = input(f"\n請輸入儲存檔名 (直接按 Enter 預設為 'grade_{datetime.now().strftime('%Y%m%d')}'): ").strip()
                col_name = input("請輸入成績欄位名稱 (直接按 Enter 預設為 '成績'): ").strip() or "成績"
                recorder.save_results(results, custom_name=custom_name or None, column_name=col_name)
        else:
            print("找不到該檔案！")
    elif choice == "3":
        new_roster = input("\n請輸入新課程名冊 CSV 檔案路徑 (例如 roster_軟體工程.csv): ").strip()
        if os.path.exists(new_roster):
            recorder = GradeRecorder(roster_path=new_roster)
            print(f"[OK] 已成功載入新課程名冊: {new_roster}，共 {len(recorder.students)} 位學生！")
        else:
            print("找不到該名冊檔案！")
    else:
        print("已結束程式。")


if __name__ == "__main__":
    demo_or_cli()
