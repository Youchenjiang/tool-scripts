#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Grade Auto-Recorder - 學生成績自動化登記與衝突消解系統
"""

from .models import Student, Roster
from .parser import GradeParser
from .engine import GradeEngine
from .exporter import GradeExporter
from .cli import main

__version__ = "2.0.0"
__all__ = ["Student", "Roster", "GradeParser", "GradeEngine", "GradeExporter", "main"]
