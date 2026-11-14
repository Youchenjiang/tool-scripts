#!/usr/bin/env python3
"""
Roster Renamer - 學生照片學號批次重命名工具

功能：
讀取名冊檔案 (Excel .xlsx / .xls 或 CSV .csv)，將裁切好的學生姓名照片
(例如 01_林妤蓁.png 或 林妤蓁.png) 自動對應學號，輸出重命名後的照片 (例如 114001 林妤蓁.png)。

特色：
- 優先使用 pandas，若無安裝則自動使用內建 zipfile/xml 與 csv 輕量解析，零外部套件依賴亦可運行。
- 支援智慧欄位偵測 (自動識別「學號」與「姓名」欄位)。
"""

import argparse
import csv
import os
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


def _col_letter_to_index(c_ref: str) -> int:
    """將 Excel 儲存格座標 (如 C4) 轉換為以 0 為基底的欄位索引 (如 2)。"""
    m = re.match(r"^([A-Za-z]+)", c_ref)
    if not m:
        return 0
    letters = m.group(1).upper()
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def _read_xlsx_builtin(path: Path) -> list[list[str]]:
    """內建輕量 .xlsx 解析器（無需 pandas 或 openpyxl）。"""
    with zipfile.ZipFile(path) as z:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in tree.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                # 處理富文本或一般文字
                parts = []
                for t in si.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"):
                    if t.text:
                        parts.append(t.text)
                shared.append("".join(parts))

        sheet_names = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet")]
        if not sheet_names:
            return []
        sheet_tree = ET.fromstring(z.read(sheet_names[0]))

        matrix: list[list[str]] = []
        for row in sheet_tree.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
            row_dict: dict[int, str] = {}
            for c in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                ref = c.attrib.get("r", "")
                c_idx = _col_letter_to_index(ref)
                v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                t = c.attrib.get("t")
                val = ""
                if v is not None and v.text:
                    if t == "s" and shared and int(v.text) < len(shared):
                        val = shared[int(v.text)]
                    else:
                        val = v.text
                row_dict[c_idx] = val

            max_c = max(row_dict.keys()) if row_dict else 0
            row_list = [row_dict.get(i, "") for i in range(max_c + 1)]
            matrix.append(row_list)
        return matrix


def _read_table_rows(roster_path: Path) -> list[list[str]]:
    """讀取表格為二維字串陣列 (優先 pandas，自動降級至內建 csv/xlsx)。"""
    ext = roster_path.suffix.lower()

    # 1. 嘗試使用 pandas
    try:
        import pandas as pd  # type: ignore

        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(roster_path, header=None)
            return [[str(x) if str(x) != "nan" else "" for x in row] for row in df.values.tolist()]
        elif ext == ".csv":
            try:
                df = pd.read_csv(roster_path, header=None, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(roster_path, header=None, encoding="big5")
            return [[str(x) if str(x) != "nan" else "" for x in row] for row in df.values.tolist()]
    except ImportError:
        pass

    # 2. 內建降級解析
    if ext == ".xlsx":
        return _read_xlsx_builtin(roster_path)
    elif ext == ".csv":
        rows: list[list[str]] = []
        try:
            with open(roster_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                rows.extend(reader)
        except Exception:
            with open(roster_path, "r", encoding="big5", errors="ignore") as f:
                reader = csv.reader(f)
                rows.extend(reader)
        return rows
    else:
        raise ValueError(f"不支援的名冊格式: {ext} (支援 .xlsx, .csv)")


def load_roster_table(
    roster_path: Path,
    id_col: Optional[str] = None,
    name_col: Optional[str] = None,
) -> dict[str, str]:
    """
    讀取名冊檔案並建立 {姓名: 學號} 字典。
    自動智慧探測含有「學號」與「姓名」特徵的欄位。
    """
    if not roster_path.exists():
        raise FileNotFoundError(f"找不到名冊檔案: {roster_path}")

    rows = _read_table_rows(roster_path)
    if not rows:
        return {}

    # 優先權定義：精確匹配 > 子字串匹配
    exact_id_keywords = ["學號", "student_id", "studentid", "學籍號", "sid"]
    exact_name_keywords = ["姓名", "student_name", "studentname", "學生姓名"]

    header_row_idx = None
    found_id_col = None
    found_name_col = None

    # 1. 掃描表頭
    max_scan = min(30, len(rows))
    for r in range(max_scan):
        row_vals = [str(v).strip().lower() for v in rows[r]]
        c_id = None
        c_name = None
        id_score = -1
        name_score = -1

        for col_idx, val in enumerate(row_vals):
            if not val:
                continue
            # 判斷學號欄
            if id_col is not None:
                if str(id_col).lower() == val or str(id_col) == str(col_idx):
                    c_id = col_idx
                    id_score = 999
            else:
                if val in exact_id_keywords and id_score < 100:
                    c_id = col_idx
                    id_score = 100
                elif "學號" in val and "組" not in val and id_score < 50:
                    c_id = col_idx
                    id_score = 50
                elif any(kw in val for kw in ["student_id", "studentid", "學籍號"]) and id_score < 30:
                    c_id = col_idx
                    id_score = 30

            # 判斷姓名欄
            if name_col is not None:
                if str(name_col).lower() == val or str(name_col) == str(col_idx):
                    c_name = col_idx
                    name_score = 999
            else:
                if val in exact_name_keywords and name_score < 100:
                    c_name = col_idx
                    name_score = 100
                elif "姓名" in val and "名單" not in val and name_score < 50:
                    c_name = col_idx
                    name_score = 50
                elif any(kw in val for kw in ["student_name", "studentname"]) and name_score < 30:
                    c_name = col_idx
                    name_score = 30

        if c_id is not None and c_name is not None and c_id != c_name:
            header_row_idx = r
            found_id_col = c_id
            found_name_col = c_name
            break

    # 2. 若未找到標題列，以數值特徵探測
    if header_row_idx is None:
        for r in range(max_scan):
            for col_idx in range(len(rows[r])):
                val = str(rows[r][col_idx]).strip()
                if (re.match(r"^\d{5,12}$", val) or re.match(r"^\d+\.\d+e\+\d+$", val.lower())) and found_id_col is None:
                    found_id_col = col_idx
                    header_row_idx = max(0, r - 1)
                elif re.match(r"^[\u4e00-\u9fff]{2,5}$", val) and found_name_col is None:
                    found_name_col = col_idx

            if found_id_col is not None and found_name_col is not None:
                break

    if found_id_col is None or found_name_col is None:
        raise ValueError("無法自動辨識學號與姓名欄位，請使用 --id-col 與 --name-col 明確指定。")

    start_row = (header_row_idx + 1) if header_row_idx is not None else 0
    mapping: dict[str, str] = {}

    for r in range(start_row, len(rows)):
        row = rows[r]
        if found_id_col >= len(row) or found_name_col >= len(row):
            continue
        raw_id = str(row[found_id_col]).strip()
        raw_name = str(row[found_name_col]).strip()

        if not raw_name or raw_name.lower() in ("nan", "none", ""):
            continue
        if not raw_id or raw_id.lower() in ("nan", "none", ""):
            continue

        # 數值正規化 (處理浮點數或科學記號 1.13423033E8 -> 113423033)
        try:
            id_val = str(int(float(raw_id)))
        except ValueError:
            id_val = re.sub(r"\.0$", "", raw_id)

        clean_name = re.sub(r"[\s\u3000]+", "", raw_name)
        if clean_name and id_val:
            mapping[clean_name] = id_val

    return mapping


def extract_student_name_from_path(file_path: Path) -> str:
    """從檔名中萃取出學生姓名 (如 '01_林妤蓁.png' -> '林妤蓁')。"""
    stem = file_path.stem
    parts = stem.split("_")
    for part in reversed(parts):
        cleaned = re.sub(r"[0-9()\-_\s\u3000]", "", part)
        if re.search(r"[\u4e00-\u9fff]{2,5}", cleaned):
            return cleaned

    cleaned = re.sub(r"[0-9()\-_\s\u3000]", "", stem)
    return cleaned or stem


def rename_students(
    input_dir: Path,
    roster_path: Path,
    output_dir: Path,
    id_col: Optional[str] = None,
    name_col: Optional[str] = None,
    naming_format: str = "{id} {name}{ext}",
    mode: str = "copy",
    keep_subdirs: bool = False,
    unmatched_prefix: str = "未知學號 ",
    dry_run: bool = False,
) -> dict[str, int]:
    """掃描圖片檔案並按名冊重命名。"""
    if not input_dir.exists():
        raise FileNotFoundError(f"找不到輸入資料夾: {input_dir}")

    mapping = load_roster_table(roster_path, id_col=id_col, name_col=name_col)
    print(f"[INFO] 成功載入名冊，共 {len(mapping)} 筆學生學號對應資料。")

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
    all_files: list[Path] = []
    for root, _, files in os.walk(input_dir):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in image_exts:
                all_files.append(p)

    all_files.sort()
    if not all_files:
        print(f"[WARN] 在 {input_dir} 找不到支援的圖片檔。")
        return {"total": 0, "matched": 0, "unmatched": 0}

    stats = {"total": len(all_files), "matched": 0, "unmatched": 0}

    for src_path in all_files:
        name = extract_student_name_from_path(src_path)
        ext = src_path.suffix

        if name in mapping:
            sid = mapping[name]
            stats["matched"] += 1
            filename = naming_format.format(id=sid, name=name, ext=ext)
        else:
            stats["unmatched"] += 1
            filename = f"{unmatched_prefix}{name}{ext}"
            print(f"[WARN] 未在名冊中找到學生「{name}」(檔名: {src_path.name})，命名為: {filename}")

        if keep_subdirs:
            rel_parent = src_path.parent.relative_to(input_dir)
            target_folder = output_dir / rel_parent
        else:
            target_folder = output_dir

        dest_path = target_folder / filename

        counter = 2
        while dest_path.exists():
            stem = Path(filename).stem
            dest_path = target_folder / f"{stem}_{counter}{ext}"
            counter += 1

        action_name = "DRY-RUN " + ("MOVE" if mode == "move" else "COPY")
        if dry_run:
            print(f"[{action_name}] {src_path.name} -> {dest_path.name}")
        else:
            target_folder.mkdir(parents=True, exist_ok=True)
            if mode == "move":
                shutil.move(src_path, dest_path)
            else:
                shutil.copy2(src_path, dest_path)

    print("\n======== 處理統計 ========")
    print(f"總圖檔數: {stats['total']}")
    print(f"成功對應學號: {stats['matched']}")
    print(f"名冊未對應: {stats['unmatched']}")
    print(f"輸出資料夾: {output_dir.resolve()}")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="學生照片學號批次重命名工具 (依名冊 Excel/CSV 自動匹配學號)"
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        default="split_students_output",
        help="輸入圖片資料夾 (預設: split_students_output)",
    )
    parser.add_argument(
        "--roster",
        "-r",
        required=True,
        help="名冊檔案路徑 (.xlsx, .csv)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="renamed_students_output",
        help="輸出資料夾 (預設: renamed_students_output)",
    )
    parser.add_argument(
        "--id-col",
        help="學號欄位名稱或索引 (若未指定會自動智慧探測)",
    )
    parser.add_argument(
        "--name-col",
        help="姓名欄位名稱或索引 (若未指定會自動智慧探測)",
    )
    parser.add_argument(
        "--format",
        default="{id} {name}{ext}",
        help="命名格式樣式 (預設: '{id} {name}{ext}')",
    )
    parser.add_argument(
        "--mode",
        choices=["copy", "move"],
        default="copy",
        help="處理模式: copy (複製) 或 move (移動)，預設為 copy",
    )
    parser.add_argument(
        "--keep-subdirs",
        action="store_true",
        help="是否保留原本的子資料夾階層 (預設平鋪至輸出目錄)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="僅預覽重命名結果，不實際複製或移動檔案",
    )

    args = parser.parse_args()

    rename_students(
        input_dir=Path(args.input_dir),
        roster_path=Path(args.roster),
        output_dir=Path(args.output_dir),
        id_col=args.id_col,
        name_col=args.name_col,
        naming_format=args.format,
        mode=args.mode,
        keep_subdirs=args.keep_subdirs,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
