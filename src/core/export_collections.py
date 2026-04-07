#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣收藏列表导出脚本 - 使用 MCP 工具后台执行

此脚本通过 MCP 工具在后台自动执行导出操作。
支持断点续跑，每页保存进度。

运行方式（在 MCP 环境中）:
    python -m auto_gen_music_tags.export_collections --user-id 63343218
"""

import json
import time
import argparse
from datetime import datetime
from pathlib import Path


class DoubanCollectionExporter:
    """豆瓣收藏导出器"""

    def __init__(self, user_id: str = "63343218"):
        self.user_id = user_id
        self.progress_file = "export_progress.json"
        self.results_file = "album_list_full.json"
        self.items_per_page = 30

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

    def save_results(self, results: dict):
        """保存结果"""
        with open(self.results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    def get_collection_url(self, collection_type: str, start: int) -> str:
        """生成收藏页面 URL"""
        return f"https://music.douban.com/people/{self.user_id}/{collection_type}?start={start}&mode=list"

    def export_with_mcp(self, mcp_tools, collection_type: str, max_pages: int = None) -> list:
        """使用 MCP 工具导出收藏列表"""
        progress = self.load_progress()

        # 如果是新类型，从头开始
        if progress.get('current_type') != collection_type:
            progress['current_type'] = collection_type
            progress['current_page'] = 1
            progress['current_start'] = 0

        entries = progress['entries'].get(collection_type, [])
        start = progress['current_start']
        page = progress['current_page']

        print(f"\n{'='*60}")
        print(f"导出 {collection_type} 列表")
        print(f"{'='*60}")
        print(f"起始页码：{page}, 起始位置：{start}")
        print(f"已有条目：{len(entries)}")

        while True:
            url = self.get_collection_url(collection_type, start)
            print(f"\n[Page {page}] {url}")

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

            entries_data = data.get('entries', [])
            has_next = data.get('hasNext', False)
            count = data.get('count', 0)

            if count == 0:
                print("  无条目，停止")
                break

            # 去重合并
            existing_ids = {e['subject_id'] for e in entries}
            new_entries = [e for e in entries_data if e['subject_id'] not in existing_ids]
            entries.extend(new_entries)

            print(f"  本页：{count} 条，新增：{len(new_entries)} 条，累计：{len(entries)} 条")

            # 保存进度
            progress['entries'][collection_type] = entries
            progress['current_type'] = collection_type
            progress['current_page'] = page + 1
            progress['current_start'] = start + self.items_per_page
            progress['last_updated'] = datetime.now().isoformat()
            self.save_progress(progress)

            # 保存临时结果
            results = {
                'exported_at': datetime.now().isoformat(),
                'user_id': self.user_id,
                'stats': {k: len(v) for k, v in progress['entries'].items()},
                'collections': progress['entries']
            }
            self.save_results(results)

            if not has_next:
                print("  已达最后一页")
                break

            if max_pages and page >= max_pages:
                print(f"  已达最大页数 {max_pages}")
                break

            start += self.items_per_page
            page += 1
            time.sleep(1.5)

        print(f"\n{collection_type} 完成：{len(entries)} 条")
        return entries

    def export_all(self, mcp_tools, max_pages_per_type: int = None):
        """导出所有收藏类型"""
        print(f"\n{'='*70}")
        print("豆瓣音乐收藏列表导出工具")
        print(f"{'='*70}")
        print(f"用户：{self.user_id}")
        print(f"开始：{datetime.now().isoformat()}")

        progress = self.load_progress()

        for ctype in ['collect', 'do', 'wish']:
            entries = self.export_with_mcp(mcp_tools, ctype, max_pages_per_type)
            progress['entries'][ctype] = entries

        # 保存最终结果
        results = {
            'exported_at': datetime.now().isoformat(),
            'user_id': self.user_id,
            'stats': {k: len(v) for k, v in progress['entries'].items()},
            'collections': progress['entries']
        }
        results['stats']['total'] = sum(results['stats'].values())
        self.save_results(results)

        print(f"\n{'='*70}")
        print("导出完成!")
        print(f"已听 (collect): {len(progress['entries']['collect'])}")
        print(f"在听 (do): {len(progress['entries']['do'])}")
        print(f"想听 (wish): {len(progress['entries']['wish'])}")
        print(f"总计：{results['stats']['total']}")
        print(f"保存到：{self.results_file}")
        print(f"{'='*70}")

        return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='豆瓣音乐收藏列表导出工具')
    parser.add_argument('--user-id', default='63343218', help='豆瓣用户 ID')
    parser.add_argument('--max-pages', type=int, default=None, help='每种类型最大页数')
    parser.add_argument('--type', choices=['collect', 'do', 'wish', 'all'], default='all', help='导出类型')

    args = parser.parse_args()

    exporter = DoubanCollectionExporter(user_id=args.user_id)

    print("此脚本需要在 MCP 环境中运行")
    print("使用 MCP 工具逐页导航并提取数据")
    print(f"运行：exporter.export_all(mcp_tools, max_pages_per_type={args.max_pages})")


if __name__ == '__main__':
    main()
