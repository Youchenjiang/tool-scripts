#!/usr/bin/env python3
"""
Photo Splitter - 學生合照人物自動裁切與命名工具

功能特點：
1. 自動人臉偵測 (OpenCV YuNet CNN 模型，自動下載；內建 Haar Cascade 備援)。
2. 智慧中線無重疊裁切策略 (Midline Splitting)，避免同排同學互相重疊。
3. 支援雙排與單排自動偵測。
4. 多策略自動姓名與排版推斷 (Multi-strategy Layout & Text Matching)：
   - 上下排標籤解析 (label_top_bottom)
   - 幾何位置匹配 (geometry: 文字與人臉座標水平中心對齊)
   - 投影分欄 OCR (strip_columns)
   - 底部橫幅辨識 (bottom_banner)
   - 色彩姓名標籤分割 (blue_tags)
   - 深度學習 EasyOCR 支援 (選用，未安裝時自動優雅降級為 Tesseract)
5. 名冊模糊匹配校正 (Fuzzy matching with difflib)，支援 Excel/CSV/JSON 名冊。
6. 自動化質檢報告與低信心人工覆核清單產出。
"""

import argparse
import difflib
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from statistics import median
from typing import Optional, Union

import cv2
import numpy as np

# YuNet 人臉偵測模型設定
YUNET_MODEL = Path("face_detection_yunet_2023mar.onnx")
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

# OCR 停用字（避免把排版指示誤認為學生姓名）
STOP_WORDS = {
    "由開至右",  # 常見 OCR 誤判
    "由左至右",
    "左右",
    "上排",
    "下排",
    "上排由左",
    "下排由左",
    "由左到右",
    "至右",
    "組別",
    "組員",
    "學號",
    "姓名",
    "名單",
}

# 預設名冊（向後相容 MIS 歷史範例，若使用者未提供外部名冊則作為備援）
LEGACY_ROSTER_MAP: dict[int, list[str]] = {
    1: ["鄒雅雯", "周怡湘", "蘇文馨", "黃詩涵", "林妤蓁", "朱宇婕"],
    2: ["胡翔安", "王廷瑜", "簡柔恩", "陳梓銜", "謝亭茹"],
    3: ["林承駿", "葉羿君", "黃櫳萱", "李恩齊", "蔣侑宸", "林秭礽"],
    4: ["林秋香", "朱芸萱", "林佩臻", "陳莉豐", "李采姈", "張芮瑀"],
    5: ["彭琦崴", "謝嘉盈", "彭家樺", "郭士揚", "賴劭穎", "李若依"],
    6: ["楊佳炘", "潘維晟", "陳柏甫", "廖承偉", "張珉萁", "謝子尉"],
    7: ["吳心平", "蘇郁茜", "李軒毅", "李芝瑢", "林立翰", "何明哲"],
    8: ["林靖恒", "黃昱鈞", "鍾柏安", "李佳蓁", "蕭筑云", "陳欣妤"],
    9: ["王品淳", "吳佩瑜", "劉和媛", "黃毓芳", "郭潔蓉", "鄭成裕"],
    10: ["陳冠豪", "吳宇翰", "郭明儒", "林婷君", "林冠澔"],
    11: ["黃仁和", "吳霜", "李嶧", "張謦麒", "侯威華"],
    12: ["陳信翰", "陳慎", "詹凱程", "廖柏廉", "謝侑明", "柳炫州"],
}

# 歷史硬編碼排版與順序覆蓋（僅在停用 --auto 或指定舊模式時使用）
LEGACY_IMAGE_ORDER_NAMES: dict[int, list[str]] = {
    1: ["林妤蓁", "鄒雅雯", "周怡湘", "朱宇婕", "蘇文馨", "黃詩涵"],
    2: ["簡柔恩", "陳梓銜", "王廷瑜", "胡翔安"],
    3: ["林承駿", "葉羿君", "黃櫳萱", "李恩齊", "蔣侑宸", "林秭礽"],
    4: ["林秋香", "朱芸萱", "林佩臻", "張芮瑀", "李采姈", "陳莉豐"],
    5: ["彭琦崴", "謝嘉盈", "彭家樺", "李若依", "郭士揚", "賴劭穎"],
    6: ["張珉萁", "謝子尉", "廖承偉", "潘維晟", "楊佳炘", "陳柏甫"],
    7: ["林立翰", "李軒毅", "何明哲", "李芝瑢", "吳心平", "蘇郁茜"],
    8: ["林靖恒", "鍾柏安", "黃昱鈞", "李佳蓁", "陳欣妤", "蕭筑云"],
    9: ["王品淳", "吳佩瑜", "郭潔蓉", "黃毓芳", "鄭成裕", "劉和媛"],
    10: ["陳冠豪", "吳宇翰", "郭明儒", "林婷君", "林冠澔"],
    11: ["黃仁和", "李嶧", "侯威華", "張謦麒", "吳霜"],
    12: ["陳信翰", "陳慎", "謝侑明", "詹凱程", "廖柏廉", "柳炫州"],
}

LEGACY_ROW_LAYOUT: dict[int, list[int]] = {
    1: [4, 2],
    3: [5, 1],
    4: [3, 3],
    8: [3, 3],
    9: [3, 3],
    11: [3, 2],
}

LEGACY_USE_FULL_IMAGE: set[int] = {3, 9}

# 全域 EasyOCR 實例快取
_EASY_READER = None


def get_easy_reader(enabled: bool = True):
    """
    動態取得 EasyOCR Reader 實例。若環境未安裝或使用者停用，安全降級回傳 None。
    """
    global _EASY_READER
    if not enabled:
        return None
    if _EASY_READER is not None:
        return _EASY_READER if _EASY_READER is not False else None

    try:
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
        import easyocr  # type: ignore

        _EASY_READER = easyocr.Reader(["ch_tra", "en"], gpu=False, verbose=False)
        return _EASY_READER
    except Exception:
        _EASY_READER = False
        return None


# ==========================================
# 1. 人臉偵測與中線智慧裁切 (Face Detection & Midline Crop)
# ==========================================


def ensure_yunet_model() -> bool:
    """確認 YuNet 模型檔案存在，若無則自 OpenCV Zoo 下載。"""
    if YUNET_MODEL.exists():
        return True
    try:
        print("[INFO] 下載人臉偵測模型 YuNet ONNX...")
        urllib.request.urlretrieve(YUNET_URL, str(YUNET_MODEL))
        return True
    except Exception as e:
        print(f"[WARN] 無法下載 YuNet 模型 ({e})，將切換為 Haar Cascade 備援。")
        return False


def nms_boxes(
    boxes: list[tuple[int, int, int, int]], iou_thr: float = 0.35
) -> list[tuple[int, int, int, int]]:
    """非極大值抑制 (Non-Maximum Suppression)"""
    if not boxes:
        return []
    arr = np.array(boxes, dtype=np.float32)
    x1 = arr[:, 0]
    y1 = arr[:, 1]
    x2 = arr[:, 0] + arr[:, 2]
    y2 = arr[:, 1] + arr[:, 3]
    area = (x2 - x1) * (y2 - y1)

    order = area.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        iou = inter / (area[i] + area[order[1:]] - inter + 1e-6)
        inds = np.where(iou <= iou_thr)[0]
        order = order[inds + 1]
    return [boxes[i] for i in keep]


def dedupe_by_x(
    boxes: list[tuple[int, int, int, int]]
) -> list[tuple[int, int, int, int]]:
    """針對水平相近的人臉框進行去重"""
    if not boxes:
        return []
    boxes_sorted = sorted(boxes, key=lambda b: b[0] + b[2] * 0.5)
    widths = [b[2] for b in boxes_sorted]
    thr = max(20.0, float(np.median(widths)) * 0.75)

    groups: list[list[tuple[int, int, int, int]]] = [[boxes_sorted[0]]]
    for b in boxes_sorted[1:]:
        prev = groups[-1][-1]
        cx_prev = prev[0] + prev[2] * 0.5
        cx = b[0] + b[2] * 0.5
        if abs(cx - cx_prev) <= thr:
            groups[-1].append(b)
        else:
            groups.append([b])

    deduped = []
    for g in groups:
        deduped.append(max(g, key=lambda b: b[2] * b[3]))
    return deduped


def detect_faces(photo: np.ndarray) -> list[tuple[int, int, int, int]]:
    """人臉偵測主函式：優先使用 YuNet CNN，失敗時自動退回 Haar Cascade。"""
    h_img, w_img = photo.shape[:2]

    if ensure_yunet_model():
        try:
            detector = cv2.FaceDetectorYN.create(
                str(YUNET_MODEL), "", (w_img, h_img), 0.65, 0.3, 5000
            )
            _, det = detector.detect(photo)
            if det is not None and len(det) > 0:
                boxes = []
                for row in det:
                    x, y, w, h, score = row[0], row[1], row[2], row[3], row[-1]
                    if score < 0.7:
                        continue
                    boxes.append((int(x), int(y), int(w), int(h)))
                boxes = [b for b in boxes if b[1] < int(h_img * 0.8)]
                boxes = nms_boxes(boxes, iou_thr=0.35)
                if boxes:
                    return boxes
        except Exception:
            pass

    # 備援：Haar Cascades
    gray = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    frontal = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    profile = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_profileface.xml"
    )

    faces = []
    f1 = frontal.detectMultiScale(
        gray, scaleFactor=1.05, minNeighbors=4, minSize=(36, 36)
    )
    for x, y, w, h in f1:
        faces.append((int(x), int(y), int(w), int(h)))

    p1 = profile.detectMultiScale(
        gray, scaleFactor=1.05, minNeighbors=4, minSize=(36, 36)
    )
    for x, y, w, h in p1:
        faces.append((int(x), int(y), int(w), int(h)))

    gray_flip = cv2.flip(gray, 1)
    p2 = profile.detectMultiScale(
        gray_flip, scaleFactor=1.05, minNeighbors=4, minSize=(36, 36)
    )
    for x, y, w, h in p2:
        faces.append((int(w_img - x - w), int(y), int(w), int(h)))

    faces = [b for b in faces if b[1] < int(h_img * 0.65)]
    faces = nms_boxes(faces, iou_thr=0.35)
    return dedupe_by_x(faces)


def pick_expected_count(
    faces: list[tuple[int, int, int, int]], expected: int
) -> list[tuple[int, int, int, int]]:
    """若偵測到的人臉數超過期望人數，按面積優先篩選並由左至右排序。"""
    if expected <= 0 or len(faces) <= expected:
        return sorted(faces, key=lambda b: b[0] + b[2] * 0.5)
    by_area = sorted(faces, key=lambda b: b[2] * b[3], reverse=True)
    picked = by_area[:expected]
    return sorted(picked, key=lambda b: b[0] + b[2] * 0.5)


def split_rows_by_y(faces: list[tuple[int, int, int, int]]) -> list[list[int]]:
    """依 Y 軸座標將人臉分為單排或上下兩排。"""
    if not faces:
        return []
    if len(faces) <= 2:
        return [list(range(len(faces)))]

    centers = [(i, f[1] + f[3] * 0.5) for i, f in enumerate(faces)]
    centers_sorted = sorted(centers, key=lambda t: t[1])
    ys = [y for _, y in centers_sorted]
    gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
    max_gap_idx = int(np.argmax(gaps))
    max_gap = gaps[max_gap_idx]
    median_h = float(np.median([f[3] for f in faces]))

    if max_gap < max(22.0, median_h * 0.7):
        return [list(range(len(faces)))]

    top_ids = [idx for idx, _ in centers_sorted[: max_gap_idx + 1]]
    bottom_ids = [idx for idx, _ in centers_sorted[max_gap_idx + 1 :]]
    if min(len(top_ids), len(bottom_ids)) < 2:
        if max_gap < max(40.0, median_h * 0.95):
            return [list(range(len(faces)))]
    return [top_ids, bottom_ids]


def compute_crop_boxes(
    photo: np.ndarray, faces: list[tuple[int, int, int, int]]
) -> list[tuple[int, int, int, int]]:
    """
    核心中線裁切演算法：
    計算相鄰人臉之間的水平中點作為裁切分界，保證同排同學照片不重疊，且保留適當身體高度。
    """
    ph, pw = photo.shape[:2]
    if not faces:
        return []

    rows = split_rows_by_y(faces)
    crop_boxes: list[tuple[int, int, int, int]] = [(0, 0, 0, 0)] * len(faces)

    row_meta = []
    for row_ids in rows:
        row_faces = [faces[i] for i in row_ids]
        top = min(f[1] for f in row_faces)
        bottom = max(f[1] + f[3] for f in row_faces)
        row_meta.append((row_ids, top, bottom))

    row_meta = sorted(row_meta, key=lambda t: t[1])
    y_cuts = []
    for i in range(len(row_meta) - 1):
        upper_bottom = row_meta[i][2]
        lower_top = row_meta[i + 1][1]
        y_cuts.append(int((upper_bottom + lower_top) * 0.5))

    for row_i, (row_ids, _, _) in enumerate(row_meta):
        order = sorted(row_ids, key=lambda idx: faces[idx][0] + faces[idx][2] * 0.5)
        cxs = [faces[idx][0] + faces[idx][2] * 0.5 for idx in order]

        left_bounds = [0] * len(order)
        right_bounds = [pw] * len(order)
        for j in range(len(order)):
            if j > 0:
                left_bounds[j] = int((cxs[j - 1] + cxs[j]) * 0.5)
            if j < len(order) - 1:
                right_bounds[j] = int((cxs[j] + cxs[j + 1]) * 0.5)

        for j, idx in enumerate(order):
            x, y, w, h = faces[idx]
            cx = x + 0.5 * w
            half_w = 1.15 * w
            left_lim = 0 if j == 0 else left_bounds[j] + 4
            right_lim = pw if j == len(order) - 1 else right_bounds[j] - 4

            half_w = min(half_w, cx - left_lim, right_lim - cx)
            if half_w < 0.6 * w:
                half_w = 0.6 * w
            x1 = max(0, int(cx - half_w))
            x2 = min(pw, int(cx + half_w))
            y1 = max(0, int(y - 0.8 * h))
            y2 = min(ph, int(y + 8.2 * h))

            if len(row_meta) > 1:
                if row_i == 0:
                    y2 = min(y2, y_cuts[0] + int(0.25 * h))
                else:
                    y1 = max(y1, y_cuts[row_i - 1] - int(0.2 * h))

            if x2 <= x1:
                cx = int(x + w * 0.5)
                half = max(18, int(0.8 * w))
                x1 = max(0, cx - half)
                x2 = min(pw, cx + half)
            if y2 <= y1:
                cy = int(y + h * 0.5)
                half = max(18, int(1.8 * h))
                y1 = max(0, cy - half)
                y2 = min(ph, cy + half)

            crop_boxes[idx] = (x1, y1, x2, y2)

    return crop_boxes


def detect_photo_text_split(img: np.ndarray) -> int:
    """自動偵測合照與底部白底姓名標籤區的切割線高度。"""
    h = img.shape[0]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    row_mean = gray.mean(axis=1)
    start = int(h * 0.45)
    white = row_mean > 235

    run_start = None
    run_len = 0
    for y in range(start, h):
        if white[y]:
            if run_start is None:
                run_start = y
                run_len = 1
            else:
                run_len += 1
            if run_len >= 20:
                return max(run_start - 2, int(h * 0.55))
        else:
            run_start = None
            run_len = 0

    return int(h * 0.72)


# ==========================================
# 2. OCR 文字辨識與分詞 (OCR Engines & Parsing)
# ==========================================


def run_tesseract_text(img: np.ndarray, psm: str = "6") -> str:
    """執行 Tesseract OCR 取得純文字。"""
    if img is None or img.size == 0:
        return ""
    tmp = Path(f"_tmp_ocr_{os.getpid()}_{id(img)}.png")
    cv2.imwrite(str(tmp), img)
    cmd = ["tesseract", str(tmp), "stdout", "-l", "chi_tra", "--psm", psm]
    try:
        out = subprocess.check_output(
            cmd, text=True, encoding="utf-8", errors="ignore"
        )
    except Exception:
        out = ""
    finally:
        tmp.unlink(missing_ok=True)
    return out


def run_tesseract_tsv(img: np.ndarray, psm: str = "6") -> list[dict]:
    """執行 Tesseract OCR 取得包含邊界方框 (TSV) 的結構化資料。"""
    if img is None or img.size == 0:
        return []
    tmp = Path(f"_tmp_tsv_{os.getpid()}_{id(img)}.png")
    cv2.imwrite(str(tmp), img)
    cmd = ["tesseract", str(tmp), "stdout", "-l", "chi_tra", "--psm", psm, "tsv"]
    try:
        out = subprocess.check_output(
            cmd, text=True, encoding="utf-8", errors="ignore"
        )
    except Exception:
        out = ""
    finally:
        tmp.unlink(missing_ok=True)

    rows = []
    lines = out.splitlines()
    for ln in lines[1:]:
        cols = ln.split("\t")
        if len(cols) < 12:
            continue
        text = cols[11].strip()
        if not text:
            continue
        try:
            x, y, w, h = int(cols[6]), int(cols[7]), int(cols[8]), int(cols[9])
        except ValueError:
            continue
        rows.append({"x": x, "y": y, "w": w, "h": h, "text": text})
    return rows


def easyocr_names_with_pos(
    img: np.ndarray, reader=None, min_conf: float = 0.12
) -> list[tuple[str, float, float]]:
    """使用 EasyOCR 取得候選姓名及其水平中心座標 (name, xc, conf)。"""
    if reader is None or reader is False or img is None or img.size == 0:
        return []
    try:
        res = reader.readtext(img, detail=1, paragraph=False)
    except Exception:
        return []

    out: list[tuple[str, float, float]] = []
    for box, text, conf in res:
        if conf < min_conf:
            continue
        names = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
        if not names:
            continue
        xc = sum(p[0] for p in box) / 4.0
        for n in names:
            if n in STOP_WORDS:
                continue
            out.append((n, float(xc), float(conf)))
    out.sort(key=lambda t: t[1])
    return out


def extract_names_from_tsv_rows(
    rows: list[dict],
) -> list[tuple[str, float, float]]:
    """將 Tesseract TSV 碎片化字框依 Y 軸聚合分行，再依 X 軸相鄰合併並萃取姓名。"""
    if not rows:
        return []

    rows = sorted(rows, key=lambda r: (r["y"] + r["h"] * 0.5, r["x"]))
    line_groups: list[list[dict]] = []
    for r in rows:
        cy = r["y"] + r["h"] * 0.5
        placed = False
        for g in line_groups:
            gcy = sum(it["y"] + it["h"] * 0.5 for it in g) / len(g)
            gh = median([it["h"] for it in g])
            if abs(cy - gcy) <= max(12.0, gh * 0.75):
                g.append(r)
                placed = True
                break
        if not placed:
            line_groups.append([r])

    extracted: list[tuple[str, float, float]] = []
    for g in line_groups:
        g = sorted(g, key=lambda r: r["x"])
        merged: list[list[dict]] = [[g[0]]]
        for r in g[1:]:
            prev = merged[-1][-1]
            gap = r["x"] - (prev["x"] + prev["w"])
            ref_w = max(10, int((prev["w"] + r["w"]) * 0.5))
            if gap <= ref_w * 1.1:
                merged[-1].append(r)
            else:
                merged.append([r])

        for m in merged:
            text = "".join(
                "".join(re.findall(r"[\u4e00-\u9fff0-9]", it["text"]))
                for it in m
            )
            if not text:
                continue
            names = [
                n
                for n in re.findall(r"[\u4e00-\u9fff]{2,4}", text)
                if n not in STOP_WORDS
            ]
            if not names:
                continue
            x1 = min(it["x"] for it in m)
            x2 = max(it["x"] + it["w"] for it in m)
            yc = sum(it["y"] + it["h"] * 0.5 for it in m) / len(m)
            xc = (x1 + x2) * 0.5
            for nm in names:
                extracted.append((nm, xc, yc))
    return extracted


def parse_top_bottom_names(ocr_text: str) -> tuple[list[str], list[str]]:
    """解析標示有「上排由左至右」、「下排由左至右」之文字區塊。"""
    top_names: list[str] = []
    bottom_names: list[str] = []
    for line in ocr_text.splitlines():
        compact = re.sub(r"\s+", "", line)
        if "上" in compact and "排" in compact:
            if ":" in compact:
                compact = compact.split(":", 1)[1]
            elif "：" in compact:
                compact = compact.split("：", 1)[1]
            top_names = [
                n
                for n in re.findall(r"[\u4e00-\u9fff]{2,4}", compact)
                if n not in STOP_WORDS
            ]
        elif "下" in compact and "排" in compact:
            if ":" in compact:
                compact = compact.split(":", 1)[1]
            elif "：" in compact:
                compact = compact.split("：", 1)[1]
            bottom_names = [
                n
                for n in re.findall(r"[\u4e00-\u9fff]{2,4}", compact)
                if n not in STOP_WORDS
            ]
    return top_names, bottom_names


def parse_names_generic(ocr_text: str) -> list[str]:
    """通用純文字姓名過濾"""
    names: list[str] = []
    for line in ocr_text.splitlines():
        compact = re.sub(r"\s+", "", line)
        if not compact:
            continue
        for n in re.findall(r"[\u4e00-\u9fff]{2,4}", compact):
            if n in STOP_WORDS or n in names:
                continue
            names.append(n)
    return names


# ==========================================
# 3. 多策略佈局判定 (Multi-Strategy Layout Extraction)
# ==========================================


def names_from_geometry(
    img: np.ndarray, faces: list[tuple[int, int, int, int]], expected: int
) -> tuple[list[str], list[int]]:
    """依人臉幾何排版與文字方塊座標對齊。"""
    rows = run_tesseract_tsv(img, psm="6")
    name_points = extract_names_from_tsv_rows(rows)
    if not name_points or not faces:
        return [], []

    face_rows = split_rows_by_y(faces)
    face_min_y = min(y for _, y, _, _ in faces)
    face_max_y = max(y + h for _, y, _, h in faces)

    top_candidates = [
        (n, x, y) for (n, x, y) in name_points if y < face_min_y - 8
    ]
    bottom_candidates = [
        (n, x, y) for (n, x, y) in name_points if y > face_max_y + 8
    ]
    around_candidates = [
        (n, x, y)
        for (n, x, y) in name_points
        if (n, x, y) not in top_candidates + bottom_candidates
    ]

    def _pick_by_x(items: list[tuple[str, float, float]], k: int) -> list[str]:
        if not items or k <= 0:
            return []
        items = sorted(items, key=lambda t: t[1])
        names = []
        for n, _, _ in items:
            if n not in names:
                names.append(n)
            if len(names) >= k:
                break
        return names

    if len(face_rows) == 2:
        cnt_top = len(face_rows[0])
        cnt_bottom = len(face_rows[1])
        top_names = _pick_by_x(top_candidates, cnt_top)
        bottom_names = _pick_by_x(bottom_candidates, cnt_bottom)
        if len(top_names) + len(bottom_names) >= max(2, expected // 2):
            return (top_names + bottom_names)[:expected], [
                len(top_names),
                len(bottom_names),
            ]

    if len(bottom_candidates) >= max(2, expected // 2):
        return _pick_by_x(bottom_candidates, expected), []
    if len(top_candidates) >= max(2, expected // 2):
        return _pick_by_x(top_candidates, expected), []

    all_names = _pick_by_x(
        top_candidates + bottom_candidates + around_candidates, expected
    )
    return all_names, []


def _ocr_column_name(crop: np.ndarray, reader=None) -> str:
    """針對單一欄位條帶進行高對比二值化與 OCR 辨識。"""
    if crop is None or crop.size == 0:
        return ""
    if crop.shape[0] < 14 or crop.shape[1] < 30:
        return ""
    c = cv2.resize(crop, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    g = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)
    cands: list[str] = []
    for inv in (False, True):
        src = (255 - g) if inv else g
        for mode in ("7", "6"):
            _, bw = cv2.threshold(
                src, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            text = run_tesseract_text(bw, psm=mode)
            names = [
                n
                for n in re.findall(r"[\u4e00-\u9fff]{2,4}", text)
                if n not in STOP_WORDS
            ]
            if names:
                cands.extend(names[:2])

    if not cands and reader:
        items = easyocr_names_with_pos(crop, reader=reader)
        if items:
            return items[0][0]

    return cands[0] if cands else ""


def names_from_strip_columns(
    img: np.ndarray,
    faces: list[tuple[int, int, int, int]],
    expected: int,
    reader=None,
) -> tuple[list[str], list[int]]:
    """將底部（或上下排）圖片投影分割為多個欄位獨立 OCR。"""
    if not faces or expected <= 0:
        return [], []
    h, w = img.shape[:2]
    face_rows = split_rows_by_y(faces)
    face_rows = [
        sorted(r, key=lambda i: faces[i][0] + faces[i][2] * 0.5)
        for r in face_rows
    ]
    face_rows = sorted(
        face_rows, key=lambda r: sum(faces[i][1] for i in r) / max(1, len(r))
    )

    if len(face_rows) == 2 and min(len(face_rows[0]), len(face_rows[1])) >= 2:
        top_n = len(face_rows[0])
        bottom_n = len(face_rows[1])
        top_strip = img[0 : int(h * 0.24), :]
        bottom_strip = img[int(h * 0.72) : h, :]
        names: list[str] = []
        for i in range(top_n):
            x1 = int(i * w / top_n)
            x2 = int((i + 1) * w / top_n)
            names.append(_ocr_column_name(top_strip[:, x1:x2], reader=reader))
        for i in range(bottom_n):
            x1 = int(i * w / bottom_n)
            x2 = int((i + 1) * w / bottom_n)
            names.append(
                _ocr_column_name(bottom_strip[:, x1:x2], reader=reader)
            )
        return names, [top_n, bottom_n]

    order = sorted(
        range(len(faces)), key=lambda i: faces[i][0] + faces[i][2] * 0.5
    )
    cxs = [faces[i][0] + faces[i][2] * 0.5 for i in order]
    bounds = [0]
    for i in range(len(cxs) - 1):
        bounds.append(int((cxs[i] + cxs[i + 1]) * 0.5))
    bounds.append(w)

    text_band = img[int(h * 0.84) : h, :]
    names = []
    for i in range(min(expected, len(bounds) - 1)):
        x1 = max(0, bounds[i])
        x2 = min(w, bounds[i + 1])
        names.append(_ocr_column_name(text_band[:, x1:x2], reader=reader))
    return names, []


def names_from_blue_tags(
    img: np.ndarray,
    expected: int,
    reader=None,
) -> tuple[list[str], list[int]]:
    """透過 HSV 顏色遮罩分割藍底姓名標籤條。"""
    if expected <= 0:
        return [], []
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (95, 80, 60), (135, 255, 255))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in cnts:
        x, y, bw, bh = cv2.boundingRect(c)
        if bw * bh >= 1200 and bw >= 40 and bh >= 20:
            boxes.append((x, y, bw, bh))

    if len(boxes) < max(2, expected // 2):
        return [], []

    boxes = sorted(boxes, key=lambda b: b[0] + b[2] * 0.5)
    names = []
    for x, y, bw, bh in boxes[:expected]:
        crop = img[y : y + bh, x : x + bw]
        names.append(_ocr_column_name(crop, reader=reader))
    return names, []


# ==========================================
# 4. 名冊比對與候選評分 (Fuzzy Matching & Strategy Selection)
# ==========================================


def best_match_name(name: str, candidates: list[str]) -> tuple[str, float]:
    """模糊比對：在候選名單中尋找與 OCR 結果最接近的學生姓名。"""
    if not candidates:
        return name, 0.0
    scored: list[tuple[float, str]] = []
    for c in candidates:
        ratio = difflib.SequenceMatcher(None, name, c).ratio()
        if name and c and name[0] == c[0]:
            ratio += 0.15
        if len(name) == len(c):
            ratio += 0.05
        scored.append((ratio, c))
    scored.sort(reverse=True)
    return scored[0][1], scored[0][0]


def map_ocr_names_to_roster(
    raw_names: list[str],
    roster_names: list[str],
    expected: int,
) -> tuple[list[str], int, float]:
    """將 OCR 候選字群映射到名冊，計算成功匹配數與平均信心度。"""
    if not roster_names:
        clipped = raw_names[:expected]
        while len(clipped) < expected:
            clipped.append(f"unknown_{len(clipped)+1:02d}")
        return clipped, len([n for n in clipped if not n.startswith("unknown_")]), 0.5

    result: list[str] = []
    unused = roster_names.copy()
    matched = 0
    score_sum = 0.0

    for n in raw_names:
        if not n:
            continue
        m, s = best_match_name(n, unused)
        if s >= 0.45:
            result.append(m)
            unused.remove(m)
            matched += 1
            score_sum += s
        else:
            result.append(n)

    # 不足預期人數時以剩餘名單補足
    for n in unused:
        if len(result) >= expected:
            break
        result.append(n)

    final_names = result[:expected]
    while len(final_names) < expected:
        final_names.append(f"unknown_{len(final_names)+1:02d}")

    avg_score = (score_sum / matched) if matched > 0 else 0.0
    return final_names, matched, avg_score


def choose_best_strategy(
    expected: int,
    roster: list[str],
    face_row_sizes: list[int],
    candidate_strategies: list[tuple[str, list[str], list[int]]],
) -> tuple[list[str], list[int], str, int, float]:
    """從多種排版與辨識策略候選中，評估並選出最優策略。"""
    best = (roster[:expected] if roster else [], [], "fallback", -1, -1.0)
    for tag, raw_names, row_layout in candidate_strategies:
        if not raw_names:
            continue
        mapped, matched, avg = map_ocr_names_to_roster(raw_names, roster, expected)
        rows = []
        if row_layout and sum(row_layout) == len(mapped):
            rows = row_layout
        if (matched, avg) > (best[3], best[4]):
            best = (mapped, rows, tag, matched, avg)

    names, rows, tag, matched, avg = best
    if roster and matched < max(1, expected // 3) and avg < 0.60:
        return roster[:expected], [], "roster_fallback", matched, avg
    return names, rows, tag, matched, avg


# ==========================================
# 5. 人臉與姓名對齊分配 (Face & Name Pairing)
# ==========================================


def sanitize_filename(name: str) -> str:
    """清理檔名中的非法字元"""
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    name = name.strip("_ ")
    return name or "unknown"


def assign_names_with_row_layout(
    faces: list[tuple[int, int, int, int]],
    names: list[str],
    row_counts: list[int],
) -> list[tuple[str, tuple[int, int, int, int]]]:
    """依指定的每排行數將人臉由上至下、由左至右與姓名配對。"""
    if not faces:
        return []
    if not row_counts or sum(row_counts) <= 0:
        faces_sorted = sorted(faces, key=lambda b: b[0] + b[2] * 0.5)
        return [(names[i] if i < len(names) else f"unknown_{i+1:02d}", f) for i, f in enumerate(faces_sorted)]

    expected = min(sum(row_counts), len(names))
    faces = pick_expected_count(faces, expected)
    faces_by_y = sorted(faces, key=lambda b: b[1] + b[3] * 0.5)

    pairs: list[tuple[str, tuple[int, int, int, int]]] = []
    cursor = 0
    name_i = 0
    for cnt in row_counts:
        if name_i >= expected or cursor >= len(faces_by_y):
            break
        row_faces = faces_by_y[cursor : cursor + cnt]
        row_faces = sorted(row_faces, key=lambda b: b[0] + b[2] * 0.5)
        for f in row_faces:
            if name_i >= expected:
                break
            pairs.append((names[name_i], f))
            name_i += 1
        cursor += cnt
    return pairs


# ==========================================
# 6. 名冊檔案載入器 (External Roster Loaders)
# ==========================================


def load_external_roster(roster_path: Path) -> dict[Union[int, str], list[str]]:
    """支援載入 JSON 或 Excel/CSV 名冊檔案。"""
    if not roster_path.exists():
        print(f"[WARN] 找不到名冊檔案: {roster_path}")
        return {}

    ext = roster_path.suffix.lower()
    if ext == ".json":
        try:
            with open(roster_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 轉換 key 為 int（若為組別編號）
            res = {}
            for k, v in data.items():
                try:
                    res[int(k)] = v
                except ValueError:
                    res[k] = v
            return res
        except Exception as e:
            print(f"[WARN] 讀取 JSON 名冊失敗: {e}")
            return {}

    if ext in (".xlsx", ".xls", ".csv"):
        try:
            from rename_by_roster import load_roster_table

            mapping = load_roster_table(roster_path)
            # 平鋪姓名清單
            return {"default": list(mapping.keys())}
        except Exception as e:
            print(f"[WARN] 讀取表格名冊失敗: {e}")
            return {}

    return {}


# ==========================================
# 7. 單圖處理流水線 (Image Processing Pipeline)
# ==========================================


def process_one_image(
    img_path: Path,
    out_dir: Path,
    debug_dir: Path,
    roster_map: dict[Union[int, str], list[str]],
    auto_mode: bool = True,
    reader=None,
) -> dict:
    """處理單張合照，自動完成偵測、裁切、重命名與除錯圖產出。"""
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"[WARN] 無法讀取圖片: {img_path.name}")
        return {}

    gid = int(img_path.stem) if img_path.stem.isdigit() else None
    h_img, w_img = img.shape[:2]

    # 1. 取得該組別名冊
    roster = []
    if gid is not None and gid in roster_map:
        roster = roster_map[gid]
    elif "default" in roster_map:
        roster = roster_map["default"]
    elif gid is not None and gid in LEGACY_ROSTER_MAP:
        roster = LEGACY_ROSTER_MAP[gid]

    # 2. 人臉偵測
    use_full_img = (gid in LEGACY_USE_FULL_IMAGE) if (not auto_mode and gid is not None) else False
    split_y = detect_photo_text_split(img)

    if use_full_img:
        photo = img
        text_area = img[0:0, :]
    else:
        photo = img[:split_y, :]
        text_area = img[split_y:, :]

    faces = detect_faces(photo)
    expected = len(faces)
    face_rows = split_rows_by_y(faces)
    face_row_sizes = [len(r) for r in face_rows]

    # 3. 命名策略決定
    strategy_tag = "auto"
    matched_count = 0
    avg_score = 0.0

    # 歷史強制指定模式 (若關閉 auto_mode 且有舊版順序定義)
    if not auto_mode and gid is not None and gid in LEGACY_IMAGE_ORDER_NAMES:
        order_names = LEGACY_IMAGE_ORDER_NAMES[gid]
        row_layout = LEGACY_ROW_LAYOUT.get(gid, [])
        expected = min(len(faces), len(order_names))
        pairs = assign_names_with_row_layout(faces, order_names[:expected], row_layout)
        strategy_tag = "legacy_override"
        matched_count = expected
        avg_score = 1.0
    else:
        # 自動化多策略推斷
        candidates: list[tuple[str, list[str], list[int]]] = []

        # 策略 A: 上排/下排標記 OCR
        ocr_text_area = run_tesseract_text(text_area, psm="6") if text_area.size > 0 else ""
        top_l, bottom_l = parse_top_bottom_names(ocr_text_area)
        if top_l and bottom_l:
            candidates.append(("label_top_bottom", top_l + bottom_l, [len(top_l), len(bottom_l)]))

        # 策略 B: 幾何座標空間匹配
        geo_names, geo_rows = names_from_geometry(img, faces, expected)
        if geo_names:
            candidates.append(("geometry", geo_names, geo_rows))

        # 策略 C: 投影分欄
        strip_names, strip_rows = names_from_strip_columns(img, faces, expected, reader=reader)
        if strip_names:
            candidates.append(("strip_columns", strip_names, strip_rows))

        # 策略 D: 色彩標籤 (藍底)
        blue_names, blue_rows = names_from_blue_tags(img, expected, reader=reader)
        if blue_names:
            candidates.append(("blue_tags", blue_names, blue_rows))

        # 策略 E: 底部純文字
        if text_area.size > 0:
            text_names = parse_names_generic(ocr_text_area)
            if text_names:
                candidates.append(("text_area", text_names, []))

        # 策略 F: EasyOCR 底部加強 (若有啟用)
        if reader:
            easy_bottom_items = easyocr_names_with_pos(img[int(h_img * 0.70) : h_img, :], reader=reader)
            if easy_bottom_items:
                candidates.append(("easyocr_bottom", [it[0] for it in easy_bottom_items], []))

        # 評估最佳策略
        final_names, row_layout, strategy_tag, matched_count, avg_score = choose_best_strategy(
            expected=expected,
            roster=roster,
            face_row_sizes=face_row_sizes,
            candidate_strategies=candidates,
        )

        if row_layout and sum(row_layout) == len(final_names):
            pairs = assign_names_with_row_layout(faces, final_names, row_layout)
        else:
            pairs = assign_names_with_row_layout(faces, final_names, face_row_sizes)

    # 4. 裁切與輸出
    pair_faces = [f for _, f in pairs]
    crop_boxes = compute_crop_boxes(photo, pair_faces)

    stem_dir = out_dir / img_path.stem
    stem_dir.mkdir(parents=True, exist_ok=True)
    for old in stem_dir.glob("*.png"):
        old.unlink(missing_ok=True)

    dbg = photo.copy()
    for i, (name, face) in enumerate(pairs, start=1):
        x, y, w, h = face
        cv2.rectangle(dbg, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(
            dbg,
            f"{i}:{name}",
            (x, max(20, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
        )
        x1, y1, x2, y2 = crop_boxes[i - 1]
        cv2.rectangle(dbg, (x1, y1), (x2, y2), (255, 180, 0), 2)
        crop = photo[y1:y2, x1:x2]
        filename = f"{i:02d}_{sanitize_filename(name)}.png"
        cv2.imwrite(str(stem_dir / filename), crop)

    debug_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(debug_dir / f"{img_path.stem}_debug.png"), dbg)
    print(f"[OK] {img_path.name} -> {len(pairs)} 人 (策略: {strategy_tag}, 信心度: {avg_score:.2f})")

    return {
        "file": img_path.name,
        "group": img_path.stem,
        "expected": expected,
        "matched": matched_count,
        "avg_score": round(avg_score, 3),
        "strategy": strategy_tag,
        "names": [nm for nm, _ in pairs],
    }


# ==========================================
# 8. 質檢與審查報告 (Reports)
# ==========================================


def generate_reports(
    run_meta: list[dict], report_path: Optional[Path], low_conf_path: Optional[Path]
) -> None:
    """產出執行總結報告與需要人工覆核的低信心清單。"""
    if report_path:
        lines = ["# 學生照片分割執行報告", "", "| 圖片檔名 | 偵測人數 | 名冊匹配數 | 平均信心度 | 採用策略 | 辨識名單 |", "| :--- | :---: | :---: | :---: | :--- | :--- |"]
        for m in run_meta:
            if not m:
                continue
            names_str = ", ".join(m.get("names", []))
            lines.append(
                f"| {m['file']} | {m['expected']} | {m['matched']} | {m['avg_score']} | `{m['strategy']}` | {names_str} |"
            )
        report_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"[INFO] 執行報告已產出: {report_path.resolve()}")

    if low_conf_path:
        flagged = []
        for m in run_meta:
            if not m:
                continue
            exp = max(1, m.get("expected", 1))
            matched = m.get("matched", 0)
            avg = m.get("avg_score", 0.0)
            strat = m.get("strategy", "")
            if strat == "fallback" or strat == "roster_fallback" or matched < max(1, exp // 2) or avg < 0.65:
                flagged.append(m)

        lines = ["# 低信心覆核清單 (建議人工檢查以下照片)", ""]
        if not flagged:
            lines.append("🎉 所有合照辨識品質良好，無低信心項目。")
        else:
            for m in flagged:
                lines.append(
                    f"- **{m['file']}** (組別 {m['group']}): 策略 `{m['strategy']}`, 匹配 {m['matched']}/{m['expected']}, 平均信心度 {m['avg_score']}"
                )
        low_conf_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"[INFO] 低信心覆核清單已產出: {low_conf_path.resolve()}")


# ==========================================
# 9. 命令列入口 (CLI Entrypoint)
# ==========================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="學生合照人物自動裁切與命名工具 (支援 YuNet、多策略排版與名冊校正)"
    )
    parser.add_argument("--input-dir", "-i", default=".", help="輸入合照目錄 (預設: 當前目錄)")
    parser.add_argument("--output-dir", "-o", default="split_students_output", help="裁切照片輸出資料夾")
    parser.add_argument("--debug-dir", "-d", default="split_students_debug", help="偵測框線除錯圖資料夾")
    parser.add_argument("--roster", "-r", help="名冊檔案路徑 (.xlsx, .xls, .csv, .json)")
    parser.add_argument("--no-auto", action="store_true", help="停用自動排版多策略推斷，使用預設規則")
    parser.add_argument("--use-easyocr", action="store_true", help="若已安裝 easyocr，強制啟用以加強文字識別")
    parser.add_argument("--report", help="產出 Markdown 執行報告檔案路徑")
    parser.add_argument("--low-confidence-report", help="產出低信心覆核報告檔案路徑")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    debug_dir = Path(args.debug_dir)

    roster_map = {}
    if args.roster:
        roster_map = load_external_roster(Path(args.roster))

    reader = None
    if args.use_easyocr:
        reader = get_easy_reader(enabled=True)
        if reader is None:
            print("[INFO] 系統未安裝 easyocr，將自動降級使用 Tesseract OCR。")

    imgs = []
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.JPG", "*.PNG", "*.JPEG", "*.webp"):
        imgs.extend(input_dir.glob(ext))
    uniq = {p.resolve(): p for p in imgs if p.is_file()}
    imgs = sorted(
        [
            p
            for p in uniq.values()
            if not p.name.lower().startswith(("_tmp_", "tmp_ocr", "debug_"))
        ],
        key=lambda p: int(p.stem) if p.stem.isdigit() else str(p.stem),
    )

    if not imgs:
        print(f"[INFO] 在 {input_dir.resolve()} 找不到合照圖片檔。")
        return

    print(f"找到 {len(imgs)} 張圖片，開始進行智慧人臉分割與姓名排版判定...\n")
    run_meta = []
    for p in imgs:
        meta = process_one_image(
            img_path=p,
            out_dir=out_dir,
            debug_dir=debug_dir,
            roster_map=roster_map,
            auto_mode=not args.no_auto,
            reader=reader,
        )
        if meta:
            run_meta.append(meta)

    report_path = Path(args.report) if args.report else None
    low_conf_path = Path(args.low_confidence_report) if args.low_confidence_report else None
    generate_reports(run_meta, report_path, low_conf_path)

    print(f"\n處理完成！個人照片存放於: {out_dir.resolve()}")
    print(f"除錯標註圖存放於: {debug_dir.resolve()}")


if __name__ == "__main__":
    main()
