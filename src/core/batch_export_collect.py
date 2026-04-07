#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量导出 collect 列表 - 高效版
每次运行导出指定页数，支持断点续跑
"""

import json
import time
from datetime import datetime
from pathlib import Path

PROGRESS_FILE = "export_progress.json"
RESULTS_FILE = "album_list_full.json"
USER_ID = "63343218"
ITEMS_PER_PAGE = 30


def load_progress():
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'collect': {'page': 1, 'start': 0, 'entries': []},
            'do': {'page': 1, 'start': 0, 'entries': []},
            'wish': {'page': 1, 'start': 0, 'entries': []},
            'last_updated': None
        }


def save_progress(progress):
    progress['last_updated'] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

    # 同时保存结果文件
    results = {
        'exported_at': datetime.now().isoformat(),
        'user_id': USER_ID,
        'stats': {
            'collect': len(progress['collect']['entries']),
            'do': len(progress['do']['entries']),
            'wish': len(progress['wish']['entries']),
            'total': (len(progress['collect']['entries']) +
                     len(progress['do']['entries']) +
                     len(progress['wish']['entries']))
        },
        'collections': {
            'collect': progress['collect']['entries'],
            'do': progress['do']['entries'],
            'wish': progress['wish']['entries']
        }
    }
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def print_progress():
    progress = load_progress()
    print(f"\n{'='*60}")
    print("当前导出进度")
    print(f"{'='*60}")
    print(f"Collect (已听): {len(progress['collect']['entries'])} / 6485 条")
    print(f"  - 当前页码：{progress['collect']['page']}, 起始位置：{progress['collect']['start']}")
    print(f"Do (在听):    {len(progress['do']['entries'])} / 152 条")
    print(f"Wish (想听):  {len(progress['wish']['entries'])} / 863 条")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    print_progress()
    print("使用说明:")
    print("1. 在浏览器中打开豆瓣音乐收藏页面")
    print("2. 打开浏览器控制台 (F12)")
    print("3. 运行 quick_export.js 中的 autoExportAll() 函数")
    print("4. 或使用本脚本配合 MCP 工具自动导出")
