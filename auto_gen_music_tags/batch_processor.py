#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量处理控制器

遍历收藏列表，为每个专辑生成并添加标签。
支持断点续跑，实时保存进度。
"""

import json
import time
import sys
from typing import Dict, List, Optional
from datetime import datetime

from .collector import DoubanCollector, AlbumEntry
from .progress import ProgressManager, initialize_progress, load_progress
from .tag_generator import DoubanMusicTagGenerator
from .browser_adder import DoubanBrowserTagAdder
from .config import TAGS_PER_ALBUM_LIMIT


class BatchProcessor:
    """批量处理器"""

    def __init__(
        self,
        user_id: str = "63343218",
        cookie_file: str = "cookie.txt",
        progress_file: str = "progress.json",
        album_list_file: str = "album_list.json"
    ):
        self.user_id = user_id
        self.cookie_file = cookie_file
        self.progress_file = progress_file
        self.album_list_file = album_list_file

        # 初始化组件
        self.collector = DoubanCollector(user_id, cookie_file)
        self.tag_generator = DoubanMusicTagGenerator(cookie_file)
        self.browser_adder = DoubanBrowserTagAdder()

        # 进度管理器
        self.progress: Optional[ProgressManager] = None

        # 配置
        self.delay_between_items = 4.0  # 处理间隔（秒）
        self.max_retries = 3  # 最大重试次数

    def export_collections(self, max_pages: int = None, delay: float = 2.0) -> Dict[str, List[AlbumEntry]]:
        """导出收藏列表"""
        print("\n" + "=" * 60)
        print("Step 1: 导出收藏列表")
        print("=" * 60)

        results = self.collector.fetch_all(max_pages, delay)
        self.collector.save_to_file(results, self.album_list_file)

        # 打印统计
        print("\n收藏列表统计:")
        for collection_type, entries in results.items():
            print(f"  {collection_type}: {len(entries)} 个条目")

        return results

    def initialize_progress(self, collections: Dict[str, List[AlbumEntry]]):
        """初始化进度"""
        self.progress = initialize_progress(collections, self.progress_file)
        self.progress.print_progress()

    def load_progress(self) -> bool:
        """加载进度"""
        self.progress = load_progress(self.progress_file)
        if self.progress:
            self.progress.print_progress()
            return True
        return False

    def process_entry(self, collection_type: str, entry: AlbumEntry) -> bool:
        """处理单个条目"""
        subject_id = entry.subject_id
        print(f"\n[{collection_type}] 处理：{entry.title} (subject={subject_id})")
        print(f"         艺术家：{entry.artists}")
        print(f"         已有标签：{entry.tags}")

        # Step 1: 生成标签
        print("\n[Step 1] 生成标签...")
        try:
            result = self.tag_generator.generate_tags(subject_id, verbose=False)
            generated_tags = result['tags_all'][:TAGS_PER_ALBUM_LIMIT]
            print(f"         生成 {len(generated_tags)} 个标签：{' '.join(generated_tags[:5])}...")
        except Exception as e:
            print(f"         [ERROR] 生成失败：{e}")
            return False

        # Step 2: 合并旧标签
        old_tags = entry.tags or []
        all_tags = list(set(old_tags + generated_tags))[:TAGS_PER_ALBUM_LIMIT]
        print(f"\n[Step 2] 合并标签：{len(all_tags)} 个")
        print(f"         最终标签：{' '.join(all_tags)}")

        # Step 3: 添加标签（浏览器模拟版）
        print("\n[Step 3] 添加标签...")
        try:
            add_result = self.browser_adder.add_tags(subject_id, all_tags)
            if add_result['success']:
                print(f"         [OK] 标签添加成功")
                # 更新进度
                self.progress.mark_success(collection_type, subject_id, all_tags)
                return True
            else:
                print(f"         [ERROR] 添加失败：{add_result['message']}")
                return False
        except Exception as e:
            print(f"         [ERROR] 添加失败：{e}")
            return False

    def process_collection(
        self,
        collection_type: str,
        max_items: int = None,
        start_from: int = 0
    ) -> Dict:
        """处理单个类型的收藏"""
        print("\n" + "=" * 60)
        print(f"开始处理 {collection_type}")
        print("=" * 60)

        pending = self.progress.get_pending_entries(collection_type)
        print(f"待处理条目：{len(pending)} 个")

        if not pending:
            print(f"[INFO] {collection_type} 没有待处理条目")
            return {'processed': 0, 'success': 0, 'failed': 0}

        # 限制处理数量
        if max_items:
            pending = pending[:max_items]

        # 跳过已处理的
        pending = pending[start_from:]

        processed = 0
        success = 0
        failed = 0

        for i, entry in enumerate(pending):
            print(f"\n[{i+1}/{len(pending)}] ", end="")

            # 重试逻辑
            for attempt in range(self.max_retries):
                result = self.process_entry(collection_type, entry)
                if result:
                    success += 1
                    break
                elif attempt < self.max_retries - 1:
                    print(f"         [RETRY] {attempt+1}/{self.max_retries}")
                    time.sleep(2)
                else:
                    print(f"         [FAIL] 已达最大重试次数")
                    self.progress.mark_failed(collection_type, entry.subject_id, "max_retries")
                    failed += 1

            processed += 1

            # 延迟（除了最后一个）
            if i < len(pending) - 1:
                print(f"\n         [DELAY] 等待 {self.delay_between_items} 秒...")
                time.sleep(self.delay_between_items)

        return {
            'processed': processed,
            'success': success,
            'failed': failed
        }

    def run(
        self,
        collection_types: List[str] = None,
        max_items_per_type: int = None,
        export_first: bool = True,
        max_pages: int = None
    ):
        """运行批量处理"""
        if collection_types is None:
            collection_types = ['collect', 'do', 'wish']

        print("\n" + "=" * 60)
        print("豆瓣音乐批量标签处理")
        print("=" * 60)
        print(f"用户 ID: {self.user_id}")
        print(f"处理类型：{', '.join(collection_types)}")
        print(f"每专辑标签上限：{TAGS_PER_ALBUM_LIMIT}")
        print(f"处理间隔：{self.delay_between_items}秒")

        # Step 1: 导出收藏列表（如果是首次运行）
        if export_first:
            collections = self.export_collections(max_pages)
            self.initialize_progress(collections)
        else:
            # 加载进度
            if not self.load_progress():
                print("[ERROR] 无法加载进度，请先导出收藏列表")
                print("[INFO] 运行：python -m auto_gen_music_tags.collector")
                return

        # Step 2: 处理每个类型
        for collection_type in collection_types:
            result = self.process_collection(collection_type, max_items_per_type)

            print(f"\n{collection_type} 处理完成:")
            print(f"  已处理：{result['processed']}")
            print(f"  成功：{result['success']}")
            print(f"  失败：{result['failed']}")

        # Step 3: 打印最终摘要
        self.progress.print_progress()
        summary = self.progress.get_summary()

        print("\n" + "=" * 60)
        print("最终摘要")
        print("=" * 60)
        print(f"总条目数：{summary['total']}")
        print(f"已处理：{summary['processed']}")
        print(f"成功：{summary['success']}")
        print(f"失败：{summary['failed']}")
        print(f"进度：{summary['progress_percent']:.1f}%")

        return summary


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='豆瓣音乐批量标签处理')
    parser.add_argument('--user-id', default='63343218', help='豆瓣用户 ID')
    parser.add_argument('--cookie', default='cookie.txt', help='Cookie 文件路径')
    parser.add_argument('--progress', default='progress.json', help='进度文件路径')
    parser.add_argument('--album-list', default='album_list.json', help='专辑列表文件路径')
    parser.add_argument('--types', nargs='+', default=['collect', 'do', 'wish'],
                       help='处理的收藏类型')
    parser.add_argument('--max-items', type=int, default=None,
                       help='每种类型最大处理数量')
    parser.add_argument('--export-first', action='store_true', default=True,
                       help='首先导出收藏列表')
    parser.add_argument('--resume', action='store_true',
                       help='从进度文件恢复（不重新导出）')
    parser.add_argument('--max-pages', type=int, default=None,
                       help='导出时每种类型最大页数')

    args = parser.parse_args()

    processor = BatchProcessor(
        user_id=args.user_id,
        cookie_file=args.cookie,
        progress_file=args.progress,
        album_list_file=args.album_list
    )

    processor.run(
        collection_types=args.types,
        max_items_per_type=args.max_items,
        export_first=not args.resume,
        max_pages=args.max_pages
    )


if __name__ == '__main__':
    main()
