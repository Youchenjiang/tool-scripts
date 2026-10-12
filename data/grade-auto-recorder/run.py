#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Grade Auto-Recorder - 一鍵啟動入口
"""

import sys

# 確保在 Windows 控制台正確輸出 UTF-8 中文字
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

from grade_recorder.cli import main

if __name__ == "__main__":
    main()
