#!/usr/bin/env python3
"""
CLI 啟動入口
執行方式：
    python run.py
    python run.py --config config.yaml --weeks 18
"""

import argparse
import os
import sys
import yaml

from recorder import TACourseRecorder


def main():
    parser = argparse.ArgumentParser(description="AI輔助教學TA補助計畫課程紀錄表 - 自動化生成器")
    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="設定檔路徑 (預設: config.yaml)",
    )
    parser.add_argument(
        "-s",
        "--start-week",
        type=int,
        default=5,
        help="起始週次 (方案 A 預設: 5，即 10/09 當週)",
    )
    parser.add_argument(
        "-e",
        "--end-week",
        type=int,
        default=None,
        help="結束週次 (預設: 自動依 config.yaml 已有週次決定，最高至第 16 週)",
    )

    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = (
        args.config
        if os.path.isabs(args.config)
        else os.path.join(script_dir, args.config)
    )

    if not os.path.exists(config_file):
        print(f"[Error] 找不到設定檔 {config_file}")
        sys.exit(1)

    with open(config_file, "r", encoding="utf-8") as f:
        config_dict = yaml.safe_load(f)

    # 起始週次預設為 5 (即 10/09 當週)
    start_week = args.start_week or 5

    # 結束週次：若使用者未傳入 -e，則自動取 config.yaml 中已記錄的最大週次，上限為 16
    recorded_weeks = [int(w) for w in config_dict.get("weeks", {}).keys()]
    max_recorded = max(recorded_weeks) if recorded_weeks else start_week
    total_semester_weeks = config_dict.get("course", {}).get("total_semester_weeks", 16)

    if args.end_week is not None:
        end_week = min(args.end_week, total_semester_weeks)
    else:
        end_week = min(max_recorded, total_semester_weeks)

    recorder = TACourseRecorder(config_dict, base_dir=script_dir)
    recorder.generate_all(start_week=start_week, end_week=end_week)


if __name__ == "__main__":
    main()
