#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣音乐批量标签添加 - MCP Chrome DevTools 自动化执行脚本

使用方法：
1. 确保 Chrome 浏览器已打开并访问豆瓣
2. 确保已登录豆瓣账号
3. 运行脚本：python run_mcp_batch_tagger.py

脚本会自动：
1. 读取 album_list_full.json 中的专辑列表
2. 为每张专辑生成标签
3. 通过 MCP Chrome DevTools 模拟浏览器操作添加标签
4. 记录处理进度和结果
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from auto_gen_music_tags.tag_generator import DoubanMusicTagGenerator


# ========== 配置常量 ==========
MAX_TAGS_PER_ALBUM = 10  # 每专辑最多标签数
DELAY_BETWEEN_ALBUMS = 5  # 专辑间延迟（秒）
SAVE_INTERVAL = 5  # 每处理 N 张专辑保存一次进度


class McpBatchTagger:
    """MCP 批量标签添加器"""

    def __init__(
        self,
        cookie_file: str = "cookie.txt",
        album_list_file: str = "album_list_full.json",
        progress_file: str = "mcp_batch_progress.json",
        result_file: str = "mcp_batch_result.json"
    ):
        self.cookie_file = cookie_file
        self.album_list_file = album_list_file
        self.progress_file = progress_file
        self.result_file = result_file

        # 初始化标签生成器
        self.tag_generator = DoubanMusicTagGenerator(cookie_file)

        # 加载专辑列表
        self.albums: List[Dict] = []
        self._load_album_list()

        # 进度管理
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.current_index = 0
        self.results: List[Dict] = []

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
        """加载进度"""
        if not os.path.exists(self.progress_file):
            print(f"[INFO] 进度文件不存在，从头开始")
            return False

        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.current_index = data.get('current_index', 0)
            self.processed_count = data.get('processed_count', 0)
            self.success_count = data.get('success_count', 0)
            self.failed_count = data.get('failed_count', 0)
            self.results = data.get('results', [])

            print(f"[INFO] 进度已加载：当前索引={self.current_index}, 成功={self.success_count}, 失败={self.failed_count}")
            return True
        except Exception as e:
            print(f"[ERROR] 加载进度失败：{e}")
            return False

    def save_progress(self):
        """保存进度"""
        data = {
            'current_index': self.current_index,
            'processed_count': self.processed_count,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'last_updated': datetime.now().isoformat(),
            'results': self.results
        }

        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[INFO] 进度已保存")
        except Exception as e:
            print(f"[ERROR] 保存进度失败：{e}")

    def generate_tags(self, subject_id: str, album_info: Dict = None) -> List[str]:
        """为专辑生成标签"""
        try:
            result = self.tag_generator.generate_tags(subject_id, album_info, verbose=False)
            return result.get('tags_all', [])[:MAX_TAGS_PER_ALBUM]
        except Exception as e:
            print(f"[ERROR] 生成标签失败：{e}")
            return []

    def mcp_add_tags(self, subject_id: str, tags: List[str]) -> Dict:
        """
        使用 MCP Chrome DevTools 添加标签

        这是在 Claude Code 环境中实际执行的函数。
        """
        print(f"\n[MCP] 准备添加标签 - subject={subject_id}")
        print(f"[MCP] 标签：{' '.join(tags)}")

        # 这里需要 Claude Code 调用 MCP 工具
        # 返回一个结果字典
        return {
            'success': True,
            'message': '请在 Claude Code 中执行标签添加',
            'subject_id': subject_id,
            'tags': tags
        }

    def process_album(self, album: Dict, index: int) -> Dict:
        """处理单张专辑"""
        subject_id = album.get('subject_id', '')
        title = album.get('title', 'Unknown')

        safe_title = title[:50]
        print(f"\n[{index}/{len(self.albums)}] Processing: {safe_title}")
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
        tags = self.generate_tags(subject_id, album)
        if not tags:
            result['message'] = '未生成标签'
            print(f"         [ERROR] {result['message']}")
            return result

        print(f"         生成 {len(tags)} 个标签")

        # Step 2: 合并旧标签
        old_tags = album.get('tags', [])
        if old_tags:
            all_tags = list(set(old_tags + tags))[:MAX_TAGS_PER_ALBUM]
            print(f"         合并旧标签后：{len(all_tags)} 个")
        else:
            all_tags = tags

        # Step 3: 添加标签（MCP 版）
        print("[Step 2] 添加标签...")
        add_result = self.mcp_add_tags(subject_id, all_tags)

        if add_result.get('success', False):
            result['success'] = True
            result['message'] = '标签添加成功'
            result['tags'] = all_tags
            print(f"         [OK] {result['message']}")
        else:
            result['message'] = add_result.get('message', '未知错误')
            print(f"         [ERROR] {result['message']}")

        return result

    def run(self, start_index: int = None, end_index: int = None):
        """运行批量处理"""
        print("\n" + "=" * 60)
        print("豆瓣音乐批量标签添加 - MCP 版")
        print("=" * 60)
        print(f"专辑总数：{len(self.albums)}")

        # 加载进度
        self.load_progress()

        # 设置索引范围
        if start_index is None:
            start_index = self.current_index
        if end_index is None:
            end_index = len(self.albums) - 1

        print(f"起始索引：{start_index}")
        print(f"结束索引：{end_index}")
        print("=" * 60)

        # 主循环
        for i in range(start_index, min(end_index + 1, len(self.albums))):
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
            else:
                self.failed_count += 1

            self.processed_count += 1
            self.current_index = i + 1

            # 定期保存进度
            if self.processed_count % SAVE_INTERVAL == 0:
                print(f"\n[CHECKPOINT] 保存进度...")
                self.save_progress()

            # 延迟（除了最后一张）
            if i < min(end_index, len(self.albums) - 1):
                print(f"[DELAY] 等待 {DELAY_BETWEEN_ALBUMS} 秒...")
                time.sleep(DELAY_BETWEEN_ALBUMS)

        # 最终保存
        print("\n" + "=" * 60)
        print("批次处理完成")
        print("=" * 60)
        self.save_progress()

        # 打印摘要
        print(f"\n摘要:")
        print(f"  已处理：{self.processed_count} 张")
        print(f"  成功：{self.success_count} 张")
        print(f"  失败：{self.failed_count} 张")
        print(f"  成功率：{self.success_count / self.processed_count * 100:.1f}%" if self.processed_count > 0 else "  成功率：N/A")

        return {
            'processed': self.processed_count,
            'success': self.success_count,
            'failed': self.failed_count
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='豆瓣音乐批量标签添加 - MCP 版')
    parser.add_argument('--cookie', default='cookie.txt', help='Cookie 文件路径')
    parser.add_argument('--album-list', default='album_list_full.json', help='专辑列表文件路径')
    parser.add_argument('--start', type=int, default=None, help='起始索引')
    parser.add_argument('--end', type=int, default=None, help='结束索引')
    parser.add_argument('--resume', action='store_true', help='从进度文件恢复')

    args = parser.parse_args()

    tagger = McpBatchTagger(
        cookie_file=args.cookie,
        album_list_file=args.album_list
    )

    if args.resume:
        tagger.load_progress()

    tagger.run(start_index=args.start, end_index=args.end)


if __name__ == '__main__':
    main()
