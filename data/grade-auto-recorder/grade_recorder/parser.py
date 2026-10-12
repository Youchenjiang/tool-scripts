#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
學生成績管理系統 - 輸入解析模組 (Parser)
支援 Excel 複製的多欄表格格式、單行鍵值對以及各種空白/Tab 分隔字串。
"""

import re
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


class GradeParser:
    """成績輸入解析器"""

    @staticmethod
    def parse_multi_column_table(text: str) -> Optional[Dict[str, List[str]]]:
        """
        解析 Excel 複製的多欄貼上格式，例如：
        A+      A       A-
        32      52      24
        60      65
        """
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

    @staticmethod
    def parse_key_value_lines(text: str) -> List[Tuple[str, str]]:
        """
        解析單行鍵值對格式，例如：
        59 A-
        1博 A+
        115423001 95
        """
        items = []
        for line in text.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = re.split(r"[\s,:\t]+", line)
            if len(parts) >= 2:
                items.append((parts[0], parts[1]))
        return items

    @classmethod
    def extract_submissions(cls, raw_text: str) -> Tuple[List[Tuple[str, str]], str]:
        """
        統一解析輸入文字為 [(token, grade_label)] 清單，並回傳格式類型
        """
        table_result = cls.parse_multi_column_table(raw_text)
        if table_result is not None:
            entries = []
            for grade_label, tokens in table_result.items():
                for token in tokens:
                    entries.append((token, grade_label))
            return entries, "multi_column"

        kv_result = cls.parse_key_value_lines(raw_text)
        if kv_result:
            return kv_result, "key_value"

        return [], "unknown"
