#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣音乐 MCP 自动标签添加器

使用方法:
    python mcp_executor.py              # 从头开始
    python mcp_executor.py --resume     # 从断点恢复
    python mcp_executor.py --start 0 --end 100  # 指定范围

前提：需要在 Claude Code 环境中运行，使用 MCP Chrome DevTools 工具
"""

import json
import time
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Callable

# 导入标签生成器
sys.path.insert(0, str(Path(__file__).parent))
from auto_gen_music_tags.tag_generator import DoubanMusicTagGenerator


# ========== 配置常量 ==========
MAX_TAGS_PER_ALBUM = 10  # 每专辑最多标签数
DELAY_BETWEEN_ALBUMS = 5  # 专辑间延迟（秒）
SAVE_INTERVAL = 5  # 每处理 N 张专辑保存一次进度


class McpExecutor:
    """MCP 自动标签添加执行器"""

    def __init__(
        self,
        cookie_file: str = "cookie.txt",
        album_list_file: str = "album_list_full.json",
        progress_file: str = "mcp_executor_progress.json",
        result_file: str = "mcp_executor_result.json"
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
        self.current_index = 0
        self.success_count = 0
        self.failed_count = 0
        self.results: List[Dict] = []
        self.failed: List[Dict] = []

        # MCP 函数引用（由外部注入）
        self.mcp_navigate: Optional[Callable] = None
        self.mcp_snapshot: Optional[Callable] = None
        self.mcp_click: Optional[Callable] = None
        self.mcp_fill: Optional[Callable] = None

    def _load_album_list(self) -> None:
        """从 album_list_full.json 加载专辑列表"""
        if not Path(self.album_list_file).exists():
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

    def _load_progress(self) -> bool:
        """从 mcp_executor_progress.json 加载进度"""
        if not Path(self.progress_file).exists():
            print(f"[INFO] 进度文件不存在，从头开始")
            return False

        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.current_index = data.get('current_index', 0)
            self.success_count = data.get('success_count', 0)
            self.failed_count = data.get('failed_count', 0)
            self.results = data.get('results', [])
            self.failed = data.get('failed', [])

            print(f"[INFO] 进度已加载：索引={self.current_index}, 成功={self.success_count}, 失败={self.failed_count}")
            return True
        except Exception as e:
            print(f"[ERROR] 加载进度失败：{e}")
            return False

    def _save_progress(self) -> None:
        """保存进度到 mcp_executor_progress.json"""
        data = {
            'started_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'current_index': self.current_index,
            'processed_count': self.success_count + self.failed_count,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'results': self.results,
            'failed': self.failed
        }

        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[INFO] 进度已保存：{self.progress_file}")
        except Exception as e:
            print(f"[ERROR] 保存进度失败：{e}")

    def generate_tags(self, subject_id: str, album_info: Dict = None) -> List[str]:
        """调用 tag_generator 生成标签"""
        try:
            result = self.tag_generator.generate_tags(
                subject_id,
                album_info,
                verbose=False
            )
            tags = result.get('tags_all', [])
            return tags[:MAX_TAGS_PER_ALBUM]
        except Exception as e:
            print(f"[ERROR] 生成标签失败：{e}")
            return []

    def _navigate_to_album(self, subject_id: str) -> None:
        """MCP 导航到专辑页面"""
        url = f"https://music.douban.com/subject/{subject_id}/"
        print(f"[MCP] 导航：{url}")
        if self.mcp_navigate:
            self.mcp_navigate(url=url, type="url")
        time.sleep(2)

    def _take_snapshot(self) -> Dict:
        """MCP 获取页面快照"""
        print("[MCP] 获取页面快照...")
        if self.mcp_snapshot:
            return self.mcp_snapshot()
        return {}

    def _click_element(self, uid: str) -> None:
        """MCP 点击元素"""
        print(f"[MCP] 点击 uid={uid}")
        if self.mcp_click:
            self.mcp_click(uid=uid)

    def _fill_input(self, uid: str, value: str) -> None:
        """MCP 填充输入框"""
        print(f"[MCP] 填充 uid={uid}, value={value}")
        if self.mcp_fill:
            self.mcp_fill(uid=uid, value=value)

    def _find_modify_button(self, snapshot_text: str) -> Optional[str]:
        """在快照中查找修改按钮"""
        for line in snapshot_text.split('\n'):
            if '修改' in line and ('link' in line or 'button' in line):
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        return None

    def _find_tag_input(self, snapshot_text: str) -> Optional[str]:
        """在快照中查找标签输入框"""
        lines = snapshot_text.split('\n')
        for i, line in enumerate(lines):
            if 'textbox' in line:
                # 优先查找对话框中的输入框 (uid=2_)
                if 'uid=2_' in line:
                    match = re.search(r'uid=(2_\d+)', line)
                    if match:
                        return match.group(1)
                # 其次查找任意 textbox
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        return None

    def _find_save_button(self, snapshot_text: str) -> Optional[str]:
        """在快照中查找保存按钮"""
        for line in snapshot_text.split('\n'):
            if '保存' in line and 'button' in line:
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        return None

    def add_tags_via_mcp(self, subject_id: str, tags: List[str]) -> Dict:
        """
        使用 MCP Chrome DevTools 工具添加标签

        Returns:
            dict: {'success': bool, 'message': str, 'tags': list}
        """
        result: Dict = {'success': False, 'message': '', 'tags': []}

        print(f"\n[MCP] 开始添加标签 - subject={subject_id}")
        print(f"[MCP] 新标签：{' '.join(tags)}")
        print("=" * 60)

        try:
            # Step 1: 导航到专辑页面
            self._navigate_to_album(subject_id)

            # Step 2: 获取快照，找修改按钮
            snapshot = self._take_snapshot()
            snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2) if isinstance(snapshot, dict) else str(snapshot)

            modify_uid = self._find_modify_button(snapshot_text)
            if not modify_uid:
                result['message'] = '未找到修改按钮'
                print(f"[ERROR] {result['message']}")
                return result
            print(f"[OK] 修改按钮 uid={modify_uid}")

            # Step 3: 点击修改
            self._click_element(modify_uid)
            time.sleep(1)

            # Step 4: 获取快照，找输入框
            snapshot = self._take_snapshot()
            snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2) if isinstance(snapshot, dict) else str(snapshot)

            input_uid = self._find_tag_input(snapshot_text)
            if not input_uid:
                result['message'] = '未找到标签输入框'
                print(f"[ERROR] {result['message']}")
                return result
            print(f"[OK] 输入框 uid={input_uid}")

            # Step 5: 填充标签（直接使用生成的标签，不合并）
            tags_str = ' '.join(tags)
            print(f"[INFO] 填充标签：{tags_str}")
            self._fill_input(input_uid, tags_str)
            time.sleep(0.5)

            # Step 6: 获取快照，找保存按钮
            snapshot = self._take_snapshot()
            snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2) if isinstance(snapshot, dict) else str(snapshot)

            save_uid = self._find_save_button(snapshot_text)
            if not save_uid:
                result['message'] = '未找到保存按钮'
                print(f"[ERROR] {result['message']}")
                return result
            print(f"[OK] 保存按钮 uid={save_uid}")

            # Step 7: 点击保存
            self._click_element(save_uid)
            time.sleep(1.5)

            # 成功
            result['success'] = True
            result['message'] = '标签添加成功'
            result['tags'] = tags
            print("[OK] 完成!")

            return result

        except Exception as e:
            result['message'] = f'添加标签失败：{e}'
            print(f"[ERROR] {result['message']}")
            return result

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

        # 清理标题中的特殊字符（兼容 Windows 控制台）
        safe_title = title.encode('utf-8', errors='ignore').decode('utf-8')
        safe_title = safe_title.encode('gbk', errors='ignore').decode('gbk')

        print(f"\n[{index}/{len(self.albums)}] Processing: {safe_title}")
        print(f"            subject={subject_id}")

        result: Dict = {
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

        print(f"         生成 {len(tags)} 个标签：{' '.join(tags[:5])}...")

        # Step 2: 添加标签（MCP 浏览器版）
        print("[Step 2] 添加标签...")
        add_result = self.add_tags_via_mcp(subject_id, tags)

        if add_result.get('success', False):
            result['success'] = True
            result['message'] = add_result.get('message', '未知错误')
            result['tags'] = add_result.get('tags', [])
            print(f"         [OK] {result['message']}")
        else:
            result['message'] = add_result.get('message', '未知错误')
            print(f"         [ERROR] {result['message']}")

        return result

    def _save_result(self) -> None:
        """保存最终结果到 mcp_executor_result.json"""
        total = self.success_count + self.failed_count
        result = {
            'completed_at': datetime.now().isoformat(),
            'start_index': 0,
            'end_index': len(self.albums) - 1,
            'processed_count': total,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'success_rate': self.success_count / total if total > 0 else 0,
            'results': self.results,
            'failed': self.failed
        }

        try:
            with open(self.result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"[INFO] 结果已保存：{self.result_file}")
        except Exception as e:
            print(f"[ERROR] 保存结果失败：{e}")

    def _print_summary(self) -> None:
        """打印摘要"""
        total = self.success_count + self.failed_count
        success_rate = self.success_count / total * 100 if total > 0 else 0

        print(f"\n摘要:")
        print(f"  已处理：{total} 张")
        print(f"  成功：{self.success_count} 张")
        print(f"  失败：{self.failed_count} 张")
        print(f"  成功率：{success_rate:.1f}%")

    def run(self, start_index: int = None, end_index: int = None) -> Dict:
        """
        运行批量处理

        Args:
            start_index: 起始索引（默认从进度文件恢复）
            end_index: 结束索引（默认处理到末尾）

        Returns:
            dict: 处理统计结果
        """
        print("\n" + "=" * 60)
        print("豆瓣音乐 MCP 自动标签添加器")
        print("=" * 60)
        print(f"专辑总数：{len(self.albums)}")

        # 加载进度（断点续传）
        self._load_progress()

        # 设置索引范围
        if start_index is None:
            start_index = self.current_index
        if end_index is None:
            end_index = len(self.albums) - 1

        print(f"起始索引：{start_index}")
        print(f"结束索引：{end_index}")
        print(f"待处理：{end_index - start_index + 1} 张专辑")
        print("=" * 60)

        # 主循环
        for i in range(start_index, min(end_index + 1, len(self.albums))):
            album = self.albums[i]
            subject_id = album.get('subject_id', '')

            # 跳过无效条目
            if not subject_id:
                print(f"\n[{i}] [SKIP] 无效条目，跳过")
                self.failed_count += 1
                self.failed.append({
                    'index': i,
                    'subject_id': '',
                    'title': album.get('title', 'Unknown'),
                    'reason': 'invalid_entry'
                })
                continue

            # 处理专辑
            result = self.process_album(album, i)

            # 更新统计
            self.results.append(result)
            if result['success']:
                self.success_count += 1
            else:
                self.failed_count += 1

            self.current_index = i + 1

            # 定期保存进度（每 SAVE_INTERVAL 张）
            if (self.success_count + self.failed_count) % SAVE_INTERVAL == 0:
                print(f"\n[CHECKPOINT] 已处理 {self.success_count + self.failed_count} 张，保存进度...")
                self._save_progress()

            # 延迟（除了最后一张）
            if i < min(end_index, len(self.albums) - 1):
                print(f"[DELAY] 等待 {DELAY_BETWEEN_ALBUMS} 秒...")
                time.sleep(DELAY_BETWEEN_ALBUMS)

        # 最终保存
        print("\n" + "=" * 60)
        print("批次处理完成")
        print("=" * 60)
        self._save_progress()
        self._save_result()

        # 打印摘要
        self._print_summary()

        return {
            'processed': self.success_count + self.failed_count,
            'success': self.success_count,
            'failed': self.failed_count
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='豆瓣音乐 MCP 自动标签添加器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
    python mcp_executor.py              # 从头开始
    python mcp_executor.py --resume     # 从断点恢复
    python mcp_executor.py --start 0 --end 100  # 指定范围
        '''
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
        '--start',
        type=int,
        default=None,
        help='起始索引（默认从进度文件恢复）'
    )
    parser.add_argument(
        '--end',
        type=int,
        default=None,
        help='结束索引（默认处理到末尾）'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='从进度文件恢复（断点续传）'
    )

    args = parser.parse_args()

    # 创建执行器
    executor = McpExecutor(
        cookie_file=args.cookie,
        album_list_file=args.album_list
    )

    # 运行
    executor.run(
        start_index=args.start if not args.resume else None,
        end_index=args.end
    )


if __name__ == '__main__':
    main()
