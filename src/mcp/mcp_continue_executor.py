#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣音乐 MCP 继续执行器 - 从索引 10 开始继续批量添加标签

在 Claude Code 环境中运行，使用 MCP Chrome DevTools 工具
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from auto_gen_music_tags.tag_generator import DoubanMusicTagGenerator

# 配置
MAX_TAGS = 10
DELAY = 5
SAVE_INTERVAL = 5
START_INDEX = 10


class McpContinueExecutor:
    """MCP 继续执行器"""

    def __init__(self):
        self.tag_generator = DoubanMusicTagGenerator("cookie.txt")
        self.albums: List[Dict] = []
        self.results: List[Dict] = []
        self.failed: List[Dict] = []
        self.current_index = START_INDEX
        self.success_count = 0
        self.failed_count = 0

        # 加载现有进度
        self._load_progress()
        # 加载专辑列表
        self._load_album_list()

    def _load_progress(self):
        """加载现有进度"""
        progress_file = Path("mcp_executor_progress.json")
        if progress_file.exists():
            with open(progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.results = data.get('results', [])
            self.failed = data.get('failed', [])
            self.success_count = data.get('success_count', 0)
            self.failed_count = data.get('failed_count', 0)
            self.current_index = data.get('current_index', START_INDEX)
            print(f"[INFO] 加载进度：已处理 {len(self.results)} 条，当前索引={self.current_index}")

    def _load_album_list(self):
        """加载专辑列表"""
        album_file = Path("album_list_full.json")
        with open(album_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict) and 'collections' in data:
            self.albums = data['collections'].get('collect', [])
        else:
            self.albums = data if isinstance(data, list) else []
        print(f"[INFO] 专辑总数：{len(self.albums)}")

    def _save_progress(self):
        """保存进度"""
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
        with open("mcp_executor_progress.json", 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 进度已保存")

    def generate_tags(self, subject_id: str, album_info: Dict = None) -> List[str]:
        """生成标签"""
        try:
            result = self.tag_generator.generate_tags(subject_id, album_info, verbose=False)
            tags = result.get('tags_all', [])
            return tags[:MAX_TAGS]
        except Exception as e:
            print(f"[ERROR] 生成标签失败：{e}")
            return []

    def navigate_to_album(self, subject_id: str):
        """导航到专辑页面"""
        url = f"https://music.douban.com/subject/{subject_id}/"
        from mcp__chrome_devtools__navigate_page import navigate_page
        navigate_page(url=url, type="url")
        time.sleep(2)

    def take_snapshot(self) -> Dict:
        """获取页面快照"""
        from mcp__chrome_devtools__take_snapshot import take_snapshot
        return take_snapshot()

    def click_element(self, uid: str):
        """点击元素"""
        from mcp__chrome_devtools__click import click
        click(uid=uid)

    def fill_input(self, uid: str, value: str):
        """填充输入框"""
        from mcp__chrome_devtools__fill import fill
        fill(uid=uid, value=value)

    def find_modify_button(self, snapshot_text: str) -> Optional[str]:
        """查找修改按钮"""
        import re
        for line in snapshot_text.split('\n'):
            if '修改' in line and ('link' in line or 'button' in line):
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        return None

    def find_tag_input(self, snapshot_text: str) -> Optional[str]:
        """查找标签输入框"""
        import re
        lines = snapshot_text.split('\n')
        for i, line in enumerate(lines):
            if 'textbox' in line:
                if 'uid=2_' in line:
                    match = re.search(r'uid=(2_\d+)', line)
                    if match:
                        return match.group(1)
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        return None

    def find_save_button(self, snapshot_text: str) -> Optional[str]:
        """查找保存按钮"""
        import re
        for line in snapshot_text.split('\n'):
            if '保存' in line and 'button' in line:
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        return None

    def add_tags_via_mcp(self, subject_id: str, tags: List[str]) -> Dict:
        """使用 MCP 添加标签"""
        result = {'success': False, 'message': '', 'tags': []}
        print(f"[MCP] 添加标签 - subject={subject_id}")
        print(f"[MCP] 标签：{' '.join(tags)}")

        try:
            # Step 1: 导航
            self.navigate_to_album(subject_id)

            # Step 2: 找修改按钮
            snapshot = self.take_snapshot()
            snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2)
            modify_uid = self.find_modify_button(snapshot_text)
            if not modify_uid:
                result['message'] = '未找到修改按钮'
                return result

            # Step 3: 点击修改
            self.click_element(modify_uid)
            time.sleep(1)

            # Step 4: 找输入框
            snapshot = self.take_snapshot()
            snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2)
            input_uid = self.find_tag_input(snapshot_text)
            if not input_uid:
                result['message'] = '未找到标签输入框'
                return result

            # Step 5: 填充标签
            tags_str = ' '.join(tags)
            self.fill_input(input_uid, tags_str)
            time.sleep(0.5)

            # Step 6: 找保存按钮
            snapshot = self.take_snapshot()
            snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2)
            save_uid = self.find_save_button(snapshot_text)
            if not save_uid:
                result['message'] = '未找到保存按钮'
                return result

            # Step 7: 点击保存
            self.click_element(save_uid)
            time.sleep(1.5)

            result['success'] = True
            result['message'] = '标签添加成功'
            result['tags'] = tags
            return result

        except Exception as e:
            result['message'] = f'添加标签失败：{e}'
            return result

    def process_album(self, album: Dict, index: int) -> Dict:
        """处理单张专辑"""
        subject_id = album.get('subject_id', '')
        title = album.get('title', 'Unknown')
        safe_title = title.encode('utf-8', errors='ignore').decode('utf-8')
        safe_title = safe_title.encode('gbk', errors='ignore').decode('gbk')

        print(f"\n[{index}/{len(self.albums)}] {safe_title}")
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
            return result
        print(f"         生成 {len(tags)} 个标签")

        # Step 2: 添加标签
        print("[Step 2] 添加标签...")
        add_result = self.add_tags_via_mcp(subject_id, tags)
        result['success'] = add_result.get('success', False)
        result['message'] = add_result.get('message', '')
        result['tags'] = add_result.get('tags', [])

        if result['success']:
            print(f"         [OK] {result['message']}")
        else:
            print(f"         [ERROR] {result['message']}")

        return result

    def run(self):
        """运行批量处理"""
        print("\n" + "=" * 60)
        print("豆瓣音乐 MCP 继续执行器")
        print("=" * 60)
        print(f"起始索引：{self.current_index}")
        print(f"专辑总数：{len(self.albums)}")
        print(f"待处理：{len(self.albums) - self.current_index} 张")
        print("=" * 60)

        for i in range(self.current_index, len(self.albums)):
            album = self.albums[i]
            subject_id = album.get('subject_id', '')

            if not subject_id:
                print(f"\n[{i}] [SKIP] 无效条目")
                self.failed_count += 1
                self.failed.append({
                    'index': i,
                    'subject_id': '',
                    'title': album.get('title', 'Unknown'),
                    'reason': 'invalid_entry'
                })
                self.current_index = i + 1
                continue

            result = self.process_album(album, i)
            self.results.append(result)

            if result['success']:
                self.success_count += 1
            else:
                self.failed_count += 1

            self.current_index = i + 1

            # 定期保存
            if (self.success_count + self.failed_count) % SAVE_INTERVAL == 0:
                self._save_progress()

            # 延迟
            if i < len(self.albums) - 1:
                print(f"[DELAY] 等待 {DELAY} 秒...")
                time.sleep(DELAY)

        # 最终保存
        self._save_progress()

        total = self.success_count + self.failed_count
        rate = self.success_count / total * 100 if total > 0 else 0
        print(f"\n完成：已处理 {total} 张，成功 {self.success_count} 张，失败 {self.failed_count} 张，成功率 {rate:.1f}%")


if __name__ == '__main__':
    executor = McpContinueExecutor()
    executor.run()
