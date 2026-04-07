#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣收藏列表批量导出脚本 - MCP 工具版

此脚本通过 MCP 工具在后台自动执行导出操作。
支持断点续跑，每页保存进度。

运行方式（在 MCP 环境中）:
    python mcp_export.py
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Tuple


class MCPExporter:
    """使用 MCP 工具导出豆瓣收藏"""

    def __init__(self, user_id: str = "63343218"):
        self.user_id = user_id
        self.progress_file = "export_progress.json"
        self.results_file = "album_list_full.json"
        self.items_per_page = 30
        self.mcp_tools = None

    def bind_mcp_tools(self, mcp_tools: dict):
        """绑定 MCP 工具"""
        self.mcp_tools = mcp_tools

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

    def navigate_to_page(self, url: str):
        """导航到页面"""
        self.mcp_tools['navigate_page'](url=url, type='url', timeout=30000)
        time.sleep(2.0)

    def extract_page_data(self) -> Tuple[List[Dict], bool, int]:
        """提取当前页面数据"""
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

        result = self.mcp_tools['evaluate_script'](function=js)
        data = result if isinstance(result, dict) else {}

        return data.get('entries', []), data.get('hasNext', False), data.get('count', 0)

    def export_collection(self, collection_type: str, max_pages: int = None) -> List[Dict]:
        """导出单个收藏类型"""
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
            url = f"https://music.douban.com/people/{self.user_id}/{collection_type}?start={start}&mode=list"
            print(f"\n[Page {page}] {url}")

            # 导航
            self.navigate_to_page(url)

            # 提取数据
            entries_data, has_next, count = self.extract_page_data()

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
            results['stats']['total'] = sum(results['stats'].values())
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

    def export_all(self, max_pages_per_type: int = None):
        """导出所有收藏类型"""
        if not self.mcp_tools:
            print("错误：请先绑定 MCP 工具")
            print("使用 exporter.bind_mcp_tools(mcp_tools)")
            return None

        print(f"\n{'='*70}")
        print("豆瓣音乐收藏列表导出工具")
        print(f"{'='*70}")
        print(f"用户：{self.user_id}")
        print(f"开始：{datetime.now().isoformat()}")

        progress = self.load_progress()

        for ctype in ['collect', 'do', 'wish']:
            entries = self.export_collection(ctype, max_pages_per_type)
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


# 全局导出器实例
exporter = MCPExporter()


def run_export(mcp_tools, user_id: str = "63343218", max_pages: int = None):
    """运行导出"""
    exporter.bind_mcp_tools(mcp_tools)
    exporter.user_id = user_id
    return exporter.export_all(max_pages)


if __name__ == '__main__':
    print("请在 MCP 环境中运行:")
    print("  from mcp_export import run_export")
    print("  run_export(mcp_tools)")
