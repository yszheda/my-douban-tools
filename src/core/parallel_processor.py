#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣音乐并行标签处理器

支持多批次并行执行，每批次独立处理指定索引范围的专辑。
支持断点续传，每 10 张专辑保存一次进度。

使用示例：
    python -m auto_gen_music_tags.parallel_processor --batch a --start 0 --end 2130
    python -m auto_gen_music_tags.parallel_processor --batch b --start 2131 --end 4260
    python -m auto_gen_music_tags.parallel_processor --batch c --start 4261 --end 6391

或者直接运行：
    cd auto_gen_music_tags && python parallel_processor.py --batch a --start 0 --end 2130
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入标签生成器（直接导入，不使用相对导入）
from auto_gen_music_tags.tag_generator import DoubanMusicTagGenerator
from auto_gen_music_tags.browser_adder import DoubanBrowserTagAdder


# ========== 配置常量 ==========
MAX_TAGS_PER_ALBUM = 10  # 每专辑最多标签数
DELAY_BETWEEN_ALBUMS = 5  # 专辑间延迟（秒）
SAVE_INTERVAL = 10  # 每处理 N 张专辑保存一次进度


class ParallelTagProcessor:
    """
    并行标签处理器

    支持按批次和索引范围处理专辑，独立保存进度和结果。
    """

    def __init__(
        self,
        batch_id: str,
        start_index: int,
        end_index: int,
        cookie_file: str = "cookie.txt",
        album_list_file: str = "album_list_full.json",
        dry_run: bool = False
    ):
        """
        初始化处理器

        Args:
            batch_id: 批次标识（a, b, c）
            start_index: 起始索引（包含）
            end_index: 结束索引（包含）
            cookie_file: Cookie 文件路径
            album_list_file: 专辑列表文件路径
        """
        self.batch_id = batch_id
        self.start_index = start_index
        self.end_index = end_index
        self.cookie_file = cookie_file
        self.album_list_file = album_list_file
        self.dry_run = dry_run

        # 文件路径配置
        self.progress_file = f"progress_{batch_id}.json"
        self.result_file = f"result_{batch_id}.json"
        self.tags_file = f"tags_batch_{batch_id}.json"

        # 初始化组件
        self.tag_generator = DoubanMusicTagGenerator(cookie_file)
        self.browser_adder = DoubanBrowserTagAdder()

        # 加载专辑列表
        self.albums: List[Dict] = []
        self._load_album_list()

        # 进度管理
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.current_index = start_index
        self.results: List[Dict] = []
        self.all_tags: List[Dict] = []

    def _load_album_list(self):
        """加载专辑列表"""
        if not os.path.exists(self.album_list_file):
            print(f"[ERROR] 专辑列表文件不存在：{self.album_list_file}")
            return

        try:
            with open(self.album_list_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 处理嵌套结构：{collections: {collect: [...]}}
            if isinstance(data, dict) and 'collections' in data:
                self.albums = data['collections'].get('collect', [])
            elif isinstance(data, list):
                self.albums = data
            else:
                self.albums = []

            print(f"[INFO] 加载专辑列表：{len(self.albums)} 条记录")
        except Exception as e:
            print(f"[ERROR] 加载专辑列表失败：{e}")

    def load_progress(self) -> bool:
        """
        加载进度

        Returns:
            bool: 是否成功加载
        """
        if not os.path.exists(self.progress_file):
            print(f"[INFO] 进度文件不存在，从头开始：{self.progress_file}")
            return False

        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.current_index = data.get('current_index', self.start_index)
            self.processed_count = data.get('processed_count', 0)
            self.success_count = data.get('success_count', 0)
            self.failed_count = data.get('failed_count', 0)
            self.results = data.get('results', [])
            self.all_tags = data.get('all_tags', [])

            print(f"[INFO] 进度已加载：{self.progress_file}")
            print(f"[INFO] 当前索引：{self.current_index}, 已成功：{self.success_count}, 已失败：{self.failed_count}")
            return True

        except Exception as e:
            print(f"[ERROR] 加载进度失败：{e}")
            return False

    def save_progress(self):
        """保存进度到文件"""
        data = {
            'batch_id': self.batch_id,
            'start_index': self.start_index,
            'end_index': self.end_index,
            'current_index': self.current_index,
            'processed_count': self.processed_count,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'last_updated': datetime.now().isoformat(),
            'results': self.results,
            'all_tags': self.all_tags
        }

        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[INFO] 进度已保存：{self.progress_file}")
        except Exception as e:
            print(f"[ERROR] 保存进度失败：{e}")

    def generate_tags_for_album(self, subject_id: str, album_info: Dict = None) -> Dict:
        """
        为专辑生成标签

        Args:
            subject_id: 豆瓣 subject ID
            album_info: 可选的专辑信息

        Returns:
            dict: 标签生成结果
        """
        try:
            result = self.tag_generator.generate_tags(subject_id, album_info, verbose=False)
            return result
        except Exception as e:
            print(f"[ERROR] 生成标签失败：{e}")
            return {
                'subject_id': subject_id,
                'tags_all': [],
                'error': str(e)
            }

    def process_album(self, album: Dict, index: int) -> Dict:
        """
        处理单张专辑

        Args:
            album: 专辑信息字典
            index: 当前索引

        Returns:
            dict: 处理结果
        """
        subject_id = album.get('subject_id', '')
        title = album.get('title', 'Unknown')

        # 清理标题中的特殊字符以避免编码问题
        safe_title = title.encode('utf-8', errors='ignore').decode('utf-8')
        # 进一步清理 GBK 无法表示的字符
        safe_title = safe_title.encode('gbk', errors='ignore').decode('gbk')

        print(f"\n[{index}/{self.end_index}] Processing: {safe_title}")
        print(f"            subject={subject_id}")

        result = {
            'index': index,
            'subject_id': subject_id,
            'title': title,
            'success': False,
            'message': '',
            'tags': []
        }

        # Step 1: 生成标签
        print("[Step 1] 生成标签...")
        try:
            tag_result = self.generate_tags_for_album(subject_id, album)
            generated_tags = tag_result.get('tags_all', [])[:MAX_TAGS_PER_ALBUM]
            print(f"         生成 {len(generated_tags)} 个标签")
        except Exception as e:
            result['message'] = f'生成标签失败：{e}'
            print(f"         [ERROR] {result['message']}")
            return result

        # Step 2: 合并旧标签
        old_tags = album.get('tags', [])
        if old_tags:
            all_tags = list(set(old_tags + generated_tags))[:MAX_TAGS_PER_ALBUM]
            print(f"         合并旧标签后：{len(all_tags)} 个")
        else:
            all_tags = generated_tags

        print(f"         最终标签：{' '.join(all_tags[:5])}...")

        # Step 3: 添加标签（浏览器模拟版）
        if self.dry_run:
            print("[Step 2] 跳过添加标签（dry-run 模式）")
            result['success'] = True
            result['message'] = 'dry-run 模式，已生成标签'
            result['tags'] = all_tags
        else:
            print("[Step 2] 添加标签...")
            try:
                add_result = self.browser_adder.add_tags(subject_id, all_tags)
                if add_result.get('success', False):
                    result['success'] = True
                    result['message'] = '标签添加成功'
                    result['tags'] = all_tags
                    print(f"         [OK] {result['message']}")
                else:
                    result['message'] = add_result.get('message', '未知错误')
                    print(f"         [ERROR] {result['message']}")
            except Exception as e:
                result['message'] = f'添加标签失败：{e}'
                print(f"         [ERROR] {result['message']}")

        return result

    def save_result(self):
        """保存结果到文件"""
        # 保存完整结果
        output_result = {
            'batch_id': self.batch_id,
            'start_index': self.start_index,
            'end_index': self.end_index,
            'processed_count': self.processed_count,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'completed_at': datetime.now().isoformat(),
            'results': self.results
        }

        try:
            with open(self.result_file, 'w', encoding='utf-8') as f:
                json.dump(output_result, f, ensure_ascii=False, indent=2)
            print(f"[INFO] 结果已保存：{self.result_file}")
        except Exception as e:
            print(f"[ERROR] 保存结果失败：{e}")

        # 保存标签汇总
        output_tags = {
            'batch_id': self.batch_id,
            'total_albums': len(self.all_tags),
            'tags': self.all_tags
        }

        try:
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump(output_tags, f, ensure_ascii=False, indent=2)
            print(f"[INFO] 标签已保存：{self.tags_file}")
        except Exception as e:
            print(f"[ERROR] 保存标签失败：{e}")

    def run(self):
        """
        运行处理器

        主循环：遍历指定范围内的专辑，逐个处理并保存进度。
        """
        print("\n" + "=" * 60)
        print("豆瓣音乐并行标签处理器")
        print("=" * 60)
        print(f"批次：{self.batch_id}")
        print(f"索引范围：{self.start_index} - {self.end_index}")
        print(f"专辑总数：{len(self.albums)}")
        print(f"处理范围：{self.end_index - self.start_index + 1} 张专辑")
        print(f"每专辑标签上限：{MAX_TAGS_PER_ALBUM}")
        print(f"专辑间延迟：{DELAY_BETWEEN_ALBUMS}秒")
        print(f"保存间隔：每{SAVE_INTERVAL}张专辑")
        print("=" * 60)

        # 加载进度（断点续传）
        self.load_progress()

        # 主循环
        for i in range(self.start_index, min(self.end_index + 1, len(self.albums))):
            # 跳过已处理的
            if i < self.current_index:
                continue

            album = self.albums[i]
            subject_id = album.get('subject_id', '')

            if not subject_id:
                print(f"\n[{i}] [SKIP] 无效条目，跳过")
                self.failed_count += 1
                self.processed_count += 1
                continue

            # 处理专辑
            result = self.process_album(album, i)

            # 更新统计
            self.results.append(result)
            if result['success']:
                self.success_count += 1
                # 保存标签数据
                self.all_tags.append({
                    'subject_id': subject_id,
                    'title': result['title'],
                    'tags': result['tags']
                })
            else:
                self.failed_count += 1

            self.processed_count += 1
            self.current_index = i + 1

            # 定期保存进度（每 SAVE_INTERVAL 张）
            if self.processed_count % SAVE_INTERVAL == 0:
                print(f"\n[CHECKPOINT] 已处理 {self.processed_count} 张，保存进度...")
                self.save_progress()

            # 延迟（除了最后一张）
            if i < min(self.end_index, len(self.albums) - 1):
                print(f"[DELAY] 等待 {DELAY_BETWEEN_ALBUMS} 秒...")
                time.sleep(DELAY_BETWEEN_ALBUMS)

        # 最终保存
        print("\n" + "=" * 60)
        print("批次处理完成")
        print("=" * 60)
        self.save_progress()
        self.save_result()

        # 打印摘要
        print(f"\n批次 {self.batch_id} 摘要:")
        print(f"  处理范围：{self.start_index} - {self.end_index}")
        print(f"  已处理：{self.processed_count} 张")
        print(f"  成功：{self.success_count} 张")
        print(f"  失败：{self.failed_count} 张")
        print(f"  成功率：{self.success_count / self.processed_count * 100:.1f}%" if self.processed_count > 0 else "  成功率：N/A")

        return {
            'batch_id': self.batch_id,
            'processed': self.processed_count,
            'success': self.success_count,
            'failed': self.failed_count
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='豆瓣音乐并行标签处理器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
    python parallel_processor.py --batch a --start 0 --end 2130
    python parallel_processor.py --batch b --start 2131 --end 4260
    python parallel_processor.py --batch c --start 4261 --end 6391
        """
    )

    parser.add_argument(
        '--batch',
        type=str,
        required=True,
        help='批次标识 (a, b, c)'
    )
    parser.add_argument(
        '--start',
        type=int,
        required=True,
        help='起始索引（包含）'
    )
    parser.add_argument(
        '--end',
        type=int,
        required=True,
        help='结束索引（包含）'
    )
    parser.add_argument(
        '--cookie',
        type=str,
        default='cookie.txt',
        help='Cookie 文件路径 (默认：cookie.txt)'
    )
    parser.add_argument(
        '--album-list',
        type=str,
        default='album_list_full.json',
        help='专辑列表文件路径 (默认：album_list_full.json)'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='从进度文件恢复（断点续传）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅生成标签，不实际添加（用于测试）'
    )

    args = parser.parse_args()

    # 创建处理器
    processor = ParallelTagProcessor(
        batch_id=args.batch,
        start_index=args.start,
        end_index=args.end,
        cookie_file=args.cookie,
        album_list_file=args.album_list,
        dry_run=args.dry_run
    )

    # 运行
    processor.run()


if __name__ == '__main__':
    main()
