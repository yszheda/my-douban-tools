#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣收藏列表导出脚本 - 使用 MCP 工具自动执行

此脚本通过 MCP 工具在后台自动执行导出操作。
支持断点续跑，每页保存进度。

运行方式：
    python auto_export.py
"""

import json
import time
from datetime import datetime


def save_progress(data: dict, filename: str = "export_progress.json"):
    """保存进度"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_progress(filename: str = "export_progress.json") -> dict:
    """加载进度"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'type': 'collect',
            'page': 1,
            'start': 0,
            'entries': {'collect': [], 'do': [], 'wish': []},
            'started_at': datetime.now().isoformat()
        }


def export_page_data(entries: list, has_next: bool, page: int, collection_type: str,
                     progress_file: str = "export_progress.json",
                     results_file: str = "album_list_full.json"):
    """保存单页数据到进度文件"""
    progress = load_progress(progress_file)

    # 更新当前类型的条目
    existing_ids = {e['subject_id'] for e in progress['entries'].get(collection_type, [])}
    new_entries = [e for e in entries if e['subject_id'] not in existing_ids]
    progress['entries'][collection_type].extend(new_entries)

    # 更新进度
    progress['current_type'] = collection_type
    progress['current_page'] = page
    progress['last_updated'] = datetime.now().isoformat()

    save_progress(progress, progress_file)

    # 保存临时结果
    results = {
        'exported_at': datetime.now().isoformat(),
        'user_id': '63343218',
        'stats': {k: len(v) for k, v in progress['entries'].items()},
        'collections': progress['entries']
    }

    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"  保存进度：{collection_type} 第 {page} 页，新增 {len(new_entries)} 条，累计 {len(progress['entries'][collection_type])} 条")

    return len(new_entries)


def main():
    """主函数"""
    print("=" * 60)
    print("豆瓣收藏列表导出脚本")
    print("=" * 60)

    progress = load_progress()
    print(f"当前进度:")
    print(f"  类型：{progress.get('current_type', 'collect')}")
    print(f"  页码：{progress.get('current_page', 1)}")
    print(f"  已收集：collect={len(progress['entries'].get('collect', []))}, "
          f"do={len(progress['entries'].get('do', []))}, "
          f"wish={len(progress['entries'].get('wish', []))}")

    print("\n此脚本需要在 MCP 环境中运行")
    print("使用 MCP 工具逐页导航并提取数据")


if __name__ == '__main__':
    main()
