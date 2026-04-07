#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣收藏列表导出器 - 浏览器自动化版

使用 Chrome DevTools MCP 绕过豆瓣反爬保护。
支持多页遍历，导出到 JSON 文件。

使用方法:
    python export_collections_browser.py
"""

import json
import time
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class AlbumEntry:
    """专辑条目数据类"""
    subject_id: str
    title: str = ""
    status: str = "pending"
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


class DoubanBrowserCollector:
    """豆瓣收藏列表抓取器 - 浏览器自动化版"""

    def __init__(self, user_id: str = "63343218"):
        self.user_id = user_id
        self.collection_types = ['collect', 'do', 'wish']
        self.items_per_page = 30

    def navigate_to_page(self, collection_type: str, start: int) -> str:
        """导航到收藏页面"""
        url = f"https://music.douban.com/people/{self.user_id}/{collection_type}?start={start}&mode=list"
        return url

    def parse_snapshot(self, snapshot_text: str) -> Tuple[List[AlbumEntry], bool]:
        """解析快照，提取专辑信息和是否有下一页"""
        entries = []
        has_next = False

        lines = snapshot_text.split('\n')

        # 检查是否有"后页"链接
        for line in lines:
            if '后页' in line and 'link' in line:
                has_next = True
                break

        # 提取专辑链接 (uid=XX link "标题" url="https://music.douban.com/subject/XXX/")
        seen_ids = set()
        for line in lines:
            # 匹配专辑链接：uid=XX link "标题" url="https://music.douban.com/subject/XXX/"
            match = re.search(r'uid=(\S+) link "(.+?)" url="https://music\.douban\.com/subject/(\d+)/"', line)
            if match:
                subject_id = match.group(3)
                title = match.group(2)

                # 去重
                if subject_id in seen_ids:
                    continue
                seen_ids.add(subject_id)

                # 只保留标题，清理多余空格
                title = re.sub(r'\s+', ' ', title).strip()

                entry = AlbumEntry(
                    subject_id=subject_id,
                    title=title
                )
                entries.append(entry)

        return entries, has_next

    def fetch_collection(self, mcp_tools, collection_type: str, max_pages: int = None, delay: float = 1.0) -> List[AlbumEntry]:
        """
        使用浏览器自动化抓取收藏列表

        Args:
            mcp_tools: MCP 工具字典
            collection_type: 'collect', 'do', 或 'wish'
            max_pages: 最大页数，None 表示抓取全部
            delay: 页面间延迟（秒）

        Returns:
            AlbumEntry 列表
        """
        all_entries = []
        start = 0
        page = 1

        print(f"\n[INFO] 开始抓取 {collection_type} 列表...")

        while True:
            url = self.navigate_to_page(collection_type, start)
            print(f"[INFO] 第 {page} 页：{url}")

            # 导航到页面
            mcp_tools['navigate_page'](url=url, type='url', timeout=30000)
            time.sleep(delay)

            # 获取快照
            snapshot_result = mcp_tools['take_snapshot']()
            snapshot_text = snapshot_result.get('content', str(snapshot_result))

            # 解析快照
            entries, has_next = self.parse_snapshot(snapshot_text)

            if not entries:
                print(f"[INFO] 没有更多条目")
                break

            all_entries.extend(entries)
            print(f"       抓取到 {len(entries)} 个条目，累计 {len(all_entries)} 个")

            # 如果没有下一页，停止
            if not has_next:
                print(f"[INFO] 已达列表末尾")
                break

            # 检查是否达到最大页数
            if max_pages and page >= max_pages:
                print(f"[INFO] 已达最大页数 {max_pages}")
                break

            # 延迟后继续下一页
            start += self.items_per_page
            page += 1

        print(f"[INFO] {collection_type} 抓取完成：共 {len(all_entries)} 个条目")
        return all_entries

    def fetch_all(self, mcp_tools, max_pages_per_type: int = None, delay: float = 1.0) -> Dict[str, List[AlbumEntry]]:
        """抓取所有类型的收藏列表"""
        results = {}

        for collection_type in self.collection_types:
            entries = self.fetch_collection(mcp_tools, collection_type, max_pages_per_type, delay)
            results[collection_type] = entries

        return results

    def save_to_file(self, results: Dict[str, List[AlbumEntry]], output_file: str = "album_list_browser.json"):
        """保存结果到 JSON 文件"""
        output = {
            'exported_at': datetime.now().isoformat(),
            'user_id': self.user_id,
            'stats': {
                k: len(v) for k, v in results.items()
            },
            'collections': {}
        }

        for collection_type, entries in results.items():
            output['collections'][collection_type] = [asdict(entry) for entry in entries]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n[INFO] 结果已保存到：{output_file}")
        return output_file


def run_export():
    """运行导出"""
    import argparse

    parser = argparse.ArgumentParser(description='豆瓣音乐收藏列表导出器（浏览器版）')
    parser.add_argument('--user-id', default='63343218', help='豆瓣用户 ID')
    parser.add_argument('--max-pages', type=int, default=None, help='每种类型最大页数')
    parser.add_argument('--delay', type=float, default=1.0, help='页面间延迟（秒）')
    parser.add_argument('--output', default='album_list_browser.json', help='输出文件路径')
    parser.add_argument('--types', nargs='+', default=['collect', 'do', 'wish'],
                       help='处理的收藏类型')

    args = parser.parse_args()

    collector = DoubanBrowserCollector(user_id=args.user_id)

    print("=" * 60)
    print("豆瓣音乐收藏列表导出（浏览器自动化版）")
    print("=" * 60)
    print(f"用户 ID: {args.user_id}")
    print(f"处理类型：{', '.join(args.types)}")

    # 注意：这个脚本需要在支持 MCP 的环境中运行
    # 在实际使用时，需要通过 MCP 客户端调用浏览器工具
    print("\n[WARN] 此脚本需要在 MCP 环境中运行")
    print("[INFO] 请在支持 Chrome DevTools MCP 的环境中执行")

    return collector


if __name__ == '__main__':
    run_export()
