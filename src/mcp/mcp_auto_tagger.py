#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣音乐自动标签添加工具 - MCP Chrome DevTools 版

使用方法：
    python mcp_auto_tagger.py --start 0 --end 100

注意：需要在 Claude Code 环境中运行，使用 MCP Chrome DevTools 工具
"""

import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# 导入标签生成器
import sys
sys.path.insert(0, str(Path(__file__).parent))
from auto_gen_music_tags.tag_generator import DoubanMusicTagGenerator


class McpAutoTagger:
    """使用 MCP Chrome DevTools 工具自动添加标签"""

    def __init__(self, cookie_file: str = "cookie.txt"):
        self.cookie_file = cookie_file
        self.tag_generator = DoubanMusicTagGenerator(cookie_file)
        self.current_subject_id = ""

    def load_album_list(self, album_file: str = "album_list_full.json") -> list:
        """加载专辑列表"""
        with open(album_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict) and 'collections' in data:
            return data['collections'].get('collect', [])
        return data if isinstance(data, list) else []

    def navigate_to_album(self, subject_id: str):
        """导航到专辑页面"""
        url = f"https://music.douban.com/subject/{subject_id}/"
        print(f"[MCP] 导航：{url}")
        # 实际调用：mcp__chrome-devtools__navigate_page(url=url, type="url")
        return url

    def take_snapshot(self):
        """获取页面快照"""
        print("[MCP] 获取页面快照...")
        # 实际调用：mcp__chrome-devtools__take_snapshot()
        return {}

    def click(self, uid: str):
        """点击元素"""
        print(f"[MCP] 点击 uid={uid}")
        # 实际调用：mcp__chrome-devtools__click(uid=uid)

    def fill(self, uid: str, value: str):
        """填充输入框"""
        print(f"[MCP] 填充 uid={uid}, value={value}")
        # 实际调用：mcp__chrome-devtools__fill(uid=uid, value=value)

    def find_modify_button(self, snapshot_text: str) -> str:
        """查找修改按钮"""
        for line in snapshot_text.split('\n'):
            if '修改' in line and 'link' in line:
                # 提取 uid
                import re
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        raise Exception("未找到修改按钮")

    def find_tag_input(self, snapshot_text: str) -> str:
        """查找标签输入框"""
        # 在对话框中查找 textbox
        lines = snapshot_text.split('\n')
        for i, line in enumerate(lines):
            if 'textbox' in line and 'uid=2_' in line:
                import re
                match = re.search(r'uid=(2_\d+)', line)
                if match:
                    return match.group(1)
        raise Exception("未找到标签输入框")

    def find_save_button(self, snapshot_text: str) -> str:
        """查找保存按钮"""
        for line in snapshot_text.split('\n'):
            if '保存' in line and 'button' in line:
                import re
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        raise Exception("未找到保存按钮")

    def add_tags(self, subject_id: str, tags: list) -> dict:
        """执行完整的标签添加流程"""
        result = {'success': False, 'message': '', 'subject_id': subject_id}

        print(f"\n[MCP] 开始添加标签 - subject={subject_id}")
        print(f"[MCP] 标签：{' '.join(tags)}")
        print("=" * 60)

        # Step 1: 导航
        self.navigate_to_album(subject_id)
        time.sleep(2)

        # Step 2: 获取快照，找修改按钮
        snapshot = self.take_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2)
        modify_uid = self.find_modify_button(snapshot_text)
        print(f"[MCP] 修改按钮 uid={modify_uid}")

        # Step 3: 点击修改
        self.click(modify_uid)
        time.sleep(1)

        # Step 4: 获取快照，找输入框
        snapshot = self.take_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2)
        input_uid = self.find_tag_input(snapshot_text)
        print(f"[MCP] 输入框 uid={input_uid}")

        # Step 5: 填充标签
        tags_str = ' '.join(tags)
        self.fill(input_uid, tags_str)
        time.sleep(0.5)

        # Step 6: 获取快照，找保存按钮
        snapshot = self.take_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2)
        save_uid = self.find_save_button(snapshot_text)
        print(f"[MCP] 保存按钮 uid={save_uid}")

        # Step 7: 点击保存
        self.click(save_uid)
        time.sleep(1.5)

        result['success'] = True
        result['message'] = '标签添加成功'
        print("[MCP] 完成!")

        return result

    def process_batch(self, start: int, end: int, album_list: list = None):
        """处理一批专辑"""
        if album_list is None:
            album_list = self.load_album_list()

        # 加载进度
        progress_file = f"mcp_progress_{start}_{end}.json"
        processed = []
        failed = []

        if Path(progress_file).exists():
            with open(progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                processed = data.get('processed', [])
                failed = data.get('failed', [])
                print(f"[INFO] 加载进度：已处理 {len(processed)}, 失败 {len(failed)}")

        # 处理范围
        albums_to_process = album_list[start:end+1]

        for i, album in enumerate(albums_to_process):
            absolute_index = start + i
            subject_id = album.get('subject_id', '')
            title = album.get('title', 'Unknown')

            # 跳过已处理的
            if any(p['subject_id'] == subject_id for p in processed):
                print(f"\n[{absolute_index}] [SKIP] 已处理，跳过：{title[:50]}")
                continue

            if not subject_id:
                print(f"\n[{absolute_index}] [SKIP] 无效条目")
                failed.append({
                    'index': absolute_index,
                    'subject_id': '',
                    'title': title,
                    'reason': 'invalid_entry'
                })
                continue

            # 生成标签
            print(f"\n[{absolute_index}/{end}] 处理：{title[:50]}...")

            try:
                tag_result = self.tag_generator.generate_tags(
                    subject_id,
                    album_info=album,
                    verbose=False
                )
                tags = tag_result.get('tags_all', [])[:10]  # 最多 10 个

                if not tags:
                    print(f"[WARN] 未生成标签")
                    failed.append({
                        'index': absolute_index,
                        'subject_id': subject_id,
                        'title': title,
                        'reason': 'no_tags_generated'
                    })
                    continue

                print(f"[INFO] 生成 {len(tags)} 个标签：{' '.join(tags[:5])}...")

                # 添加标签（MCP 浏览器版）
                add_result = self.add_tags(subject_id, tags)

                if add_result['success']:
                    print(f"[OK] 标签添加成功")
                    processed.append({
                        'index': absolute_index,
                        'subject_id': subject_id,
                        'title': title,
                        'tags': tags,
                        'processed_at': datetime.now().isoformat()
                    })
                else:
                    print(f"[FAIL] {add_result['message']}")
                    failed.append({
                        'index': absolute_index,
                        'subject_id': subject_id,
                        'title': title,
                        'reason': add_result['message']
                    })

            except Exception as e:
                print(f"[ERROR] {e}")
                failed.append({
                    'index': absolute_index,
                    'subject_id': subject_id,
                    'title': title,
                    'reason': str(e)
                })

            # 保存进度（每 10 张）
            if len(processed) % 10 == 0 and len(processed) > 0:
                self.save_progress(progress_file, processed, failed)
                print(f"[CHECKPOINT] 进度已保存")

            # 延迟
            if i < len(albums_to_process) - 1:
                print(f"[DELAY] 等待 5 秒...")
                time.sleep(5)

        # 最终保存
        self.save_progress(progress_file, processed, failed)

        # 输出摘要
        print("\n" + "=" * 60)
        print("批次处理完成")
        print("=" * 60)
        print(f"成功：{len(processed)}")
        print(f"失败：{len(failed)}")
        print(f"成功率：{len(processed) / (len(processed) + len(failed)) * 100:.1f}%" if (processed or failed) else "N/A")

        return processed, failed

    def save_progress(self, progress_file: str, processed: list, failed: list):
        """保存进度"""
        data = {
            'updated_at': datetime.now().isoformat(),
            'processed': processed,
            'failed': failed,
            'summary': {
                'total_processed': len(processed),
                'total_failed': len(failed)
            }
        }
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 进度已保存：{progress_file}")


def main():
    parser = argparse.ArgumentParser(description='豆瓣音乐自动标签添加工具')
    parser.add_argument('--start', type=int, default=0, help='起始索引')
    parser.add_argument('--end', type=int, default=100, help='结束索引')
    parser.add_argument('--cookie', type=str, default='cookie.txt', help='Cookie 文件')

    args = parser.parse_args()

    tagger = McpAutoTagger(args.cookie)
    tagger.process_batch(args.start, args.end)


if __name__ == '__main__':
    main()
