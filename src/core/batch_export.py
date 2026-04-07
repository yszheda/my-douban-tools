#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣收藏列表批量导出脚本

使用 MCP 浏览器工具批量导出收藏列表。
支持断点续跑，每页保存进度。

运行方式：
    python batch_export.py --type collect --user-id 63343218
"""

import json
import time
import argparse
from datetime import datetime
from pathlib import Path


class DoubanExporter:
    """豆瓣收藏导出器"""

    def __init__(self, user_id: str = "63343218"):
        self.user_id = user_id
        self.progress_file = "export_progress.json"
        self.results_file = "album_list_full.json"

    def load_progress(self) -> dict:
        """加载进度"""
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'current_type': 'collect',
                'current_page': 1,
                'current_start': 0,
                'entries': {'collect': [], 'do': [], 'wish': []},
                'started_at': datetime.now().isoformat()
            }

    def save_progress(self, progress: dict):
        """保存进度"""
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    def load_results(self) -> dict:
        """加载结果"""
        try:
            with open(self.results_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'exported_at': datetime.now().isoformat(),
                'user_id': self.user_id,
                'stats': {'collect': 0, 'do': 0, 'wish': 0, 'total': 0},
                'collections': {'collect': [], 'do': [], 'wish': []}
            }

    def save_results(self, results: dict):
        """保存结果"""
        results['stats']['total'] = sum(results['stats'].values())
        with open(self.results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    def get_next_page_url(self, collection_type: str, start: int) -> str:
        """获取下一页 URL"""
        return f"https://music.douban.com/people/{self.user_id}/{collection_type}?start={start}&mode=list"

    def export_page(self, mcp_tools, url: str) -> tuple:
        """导出单页数据"""
        # 导航
        mcp_tools['navigate_page'](url=url, type='url', timeout=30000)
        time.sleep(2.0)

        # 执行 JS
        js = """
        () => {
            const links = Array.from(document.querySelectorAll('a[href*="/subject/"]'))
                .filter(a => !a.href.includes('/people/'))
                .map(a => {
                    const match = a.href.match(/\\/subject\\/(\\d+)\\//);
                    return {
                        subject_id: match ? match[1] : null,
                        title: a.title || a.textContent.trim()
                    };
                })
                .filter(x => x.subject_id);

            const seen = new Set();
            const unique = links.filter(x => {
                if (seen.has(x.subject_id)) return false;
                seen.add(x.subject_id);
                return true;
            });

            const hasNext = Array.from(document.querySelectorAll('a')).some(a => a.textContent.includes('后页'));

            return { entries: unique, hasNext, count: unique.length };
        }
        """

        result = mcp_tools['evaluate_script'](function=js)
        data = result if isinstance(result, dict) else {}

        return data.get('entries', []), data.get('hasNext', False), data.get('count', 0)

    def export_collection(self, mcp_tools, collection_type: str, max_pages: int = None) -> list:
        """导出单个收藏类型"""
        progress = self.load_progress()
        entries = progress['entries'].get(collection_type, [])

        start = 0
        page = 1
        items_per_page = 30

        print(f"\n开始导出 {collection_type}...")

        while True:
            url = self.get_next_page_url(collection_type, start)
            print(f"[Page {page}] {url}")

            page_entries, has_next, count = self.export_page(mcp_tools, url)

            if count == 0:
                print("  无条目，停止")
                break

            # 去重合并
            existing_ids = {e['subject_id'] for e in entries}
            new_entries = [e for e in page_entries if e['subject_id'] not in existing_ids]
            entries.extend(new_entries)

            print(f"  本页：{count} 条，新增：{len(new_entries)} 条，累计：{len(entries)} 条")

            # 保存进度
            progress['entries'][collection_type] = entries
            progress['current_page'] = page + 1
            progress['current_start'] = start + items_per_page
            self.save_progress(progress)

            if not has_next:
                print("  已达最后一页")
                break

            if max_pages and page >= max_pages:
                print(f"  已达最大页数 {max_pages}")
                break

            start += items_per_page
            page += 1
            time.sleep(1.5)

        print(f"{collection_type} 完成：{len(entries)} 条")
        return entries

    def export_all(self, mcp_tools, max_pages_per_type: int = None):
        """导出所有收藏类型"""
        print(f"\n{'='*60}")
        print("豆瓣音乐收藏列表导出工具")
        print(f"{'='*60}")
        print(f"用户：{self.user_id}")
        print(f"开始：{datetime.now().isoformat()}")

        progress = self.load_progress()

        for ctype in ['collect', 'do', 'wish']:
            entries = self.export_collection(mcp_tools, ctype, max_pages_per_type)
            progress['entries'][ctype] = entries

        # 保存最终结果
        results = {
            'exported_at': datetime.now().isoformat(),
            'user_id': self.user_id,
            'stats': {k: len(v) for k, v in progress['entries'].items()},
            'collections': progress['entries']
        }
        self.save_results(results)

        print(f"\n{'='*60}")
        print("导出完成!")
        print(f"已听 (collect): {len(progress['entries']['collect'])}")
        print(f"在听 (do): {len(progress['entries']['do'])}")
        print(f"想听 (wish): {len(progress['entries']['wish'])}")
        print(f"总计：{sum(len(v) for v in progress['entries'].values())}")
        print(f"保存到：{self.results_file}")
        print(f"{'='*60}")

        return results


def main():
    parser = argparse.ArgumentParser(description='豆瓣音乐收藏列表导出工具')
    parser.add_argument('--user-id', default='63343218', help='豆瓣用户 ID')
    parser.add_argument('--max-pages', type=int, default=None, help='每种类型最大页数')
    parser.add_argument('--type', choices=['collect', 'do', 'wish', 'all'], default='all', help='导出类型')

    args = parser.parse_args()

    exporter = DoubanExporter(user_id=args.user_id)

    # 注意：这个脚本需要在 MCP 环境中运行
    print("此脚本需要在 MCP 环境中运行")
    print("请提供 mcp_tools 字典以执行导出")


if __name__ == '__main__':
    main()
