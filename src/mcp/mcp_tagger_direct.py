#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣音乐自动标签添加器 - MCP 工具集成版

此脚本通过 JSON 协议与 MCP Chrome DevTools 通信
需要在 Claude Code 环境中运行

使用方法:
    python mcp_tagger_direct.py --start 0 --end 10
"""

import json
import time
import argparse
import sys
import re
from pathlib import Path
from datetime import datetime

# 导入标签生成器
sys.path.insert(0, str(Path(__file__).parent))
from auto_gen_music_tags.tag_generator import DoubanMusicTagGenerator


class McpProtocolError(Exception):
    """MCP 协议错误"""
    pass


class McpChromeClient:
    """
    MCP Chrome DevTools 客户端

    通过标准输入/输出与 MCP 服务器通信
    """

    def __init__(self):
        self.current_snapshot = {}

    def navigate(self, url: str) -> dict:
        """导航到 URL"""
        return {
            'method': 'mcp__chrome-devtools__navigate_page',
            'params': {'type': 'url', 'url': url, 'timeout': 30000}
        }

    def take_snapshot(self) -> dict:
        """获取页面快照"""
        return {
            'method': 'mcp__chrome-devtools__take_snapshot',
            'params': {'verbose': False}
        }

    def click(self, uid: str) -> dict:
        """点击元素"""
        return {
            'method': 'mcp__chrome-devtools__click',
            'params': {'uid': uid}
        }

    def fill(self, uid: str, value: str) -> dict:
        """填充输入框"""
        return {
            'method': 'mcp__chrome-devtools__fill',
            'params': {'uid': uid, 'value': value}
        }


class AutoTaggerMCP:
    """豆瓣音乐自动标签添加器 - MCP 版"""

    def __init__(self, cookie_file: str = "cookie.txt"):
        self.cookie_file = cookie_file
        self.tag_generator = DoubanMusicTagGenerator(cookie_file)
        self.client = McpChromeClient()

    def load_album_list(self, album_file: str = "album_list_full.json") -> list:
        """加载专辑列表"""
        with open(album_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict) and 'collections' in data:
            return data['collections'].get('collect', [])
        return data if isinstance(data, list) else []

    def extract_uid(self, text: str) -> str:
        """从快照行中提取 uid"""
        match = re.search(r'uid=(\d+_\d+)', text)
        return match.group(1) if match else None

    def find_modify_button(self, snapshot_text: str) -> str:
        """查找修改按钮"""
        for line in snapshot_text.split('\n'):
            if '修改' in line and 'link' in line:
                uid = self.extract_uid(line)
                if uid:
                    return uid
        raise Exception("未找到修改按钮")

    def find_tag_input(self, snapshot_text: str) -> str:
        """查找标签输入框"""
        lines = snapshot_text.split('\n')
        for i, line in enumerate(lines):
            if 'textbox' in line:
                # 检查是否在对话框中 (uid=2_)
                if 'uid=2_' in line:
                    uid = self.extract_uid(line)
                    if uid:
                        return uid
        # 如果没有找到 2_ 开头，找任意 textbox
        for line in lines:
            if 'textbox' in line:
                uid = self.extract_uid(line)
                if uid:
                    return uid
        raise Exception("未找到标签输入框")

    def find_save_button(self, snapshot_text: str) -> str:
        """查找保存按钮"""
        for line in snapshot_text.split('\n'):
            if '保存' in line and 'button' in line:
                uid = self.extract_uid(line)
                if uid:
                    return uid
        raise Exception("未找到保存按钮")

    def process_album(self, subject_id: str, title: str, index: int,
                      mcp_navigator, mcp_snapshot, mcp_click, mcp_fill) -> dict:
        """
        处理单张专辑

        Args:
            subject_id: 专辑 subject_id
            title: 专辑标题
            index: 索引
            mcp_navigator: MCP navigate_page 函数
            mcp_snapshot: MCP take_snapshot 函数
            mcp_click: MCP click 函数
            mcp_fill: MCP fill 函数

        Returns:
            dict: 处理结果
        """
        result = {
            'index': index,
            'subject_id': subject_id,
            'title': title,
            'success': False,
            'message': '',
            'tags': []
        }

        print(f"\n[{index}] 处理：{title[:60]}...")

        # Step 1: 生成标签
        print("  [Step 1] 生成标签...")
        try:
            tag_result = self.tag_generator.generate_tags(
                subject_id,
                album_info={'subject_id': subject_id, 'title': title},
                verbose=False
            )
            tags = tag_result.get('tags_all', [])[:10]

            if not tags:
                result['message'] = '未生成标签'
                print(f"  [FAIL] {result['message']}")
                return result

            print(f"  [OK] 生成 {len(tags)} 个标签：{' '.join(tags[:5])}...")

        except Exception as e:
            result['message'] = f'生成标签失败：{e}'
            print(f"  [ERROR] {result['message']}")
            return result

        # Step 2: 导航到专辑页面
        print("  [Step 2] 导航到专辑页面...")
        url = f"https://music.douban.com/subject/{subject_id}/"
        mcp_navigator(url=url, type="url")
        time.sleep(2)

        # Step 3: 获取快照，找修改按钮
        print("  [Step 3] 查找修改按钮...")
        snapshot = mcp_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2)

        try:
            modify_uid = self.find_modify_button(snapshot_text)
            print(f"  [OK] 修改按钮 uid={modify_uid}")
        except Exception as e:
            result['message'] = f'未找到修改按钮：{e}'
            print(f"  [ERROR] {result['message']}")
            return result

        # Step 4: 点击修改
        print("  [Step 4] 点击修改按钮...")
        mcp_click(uid=modify_uid)
        time.sleep(1)

        # Step 5: 获取快照，找输入框
        print("  [Step 5] 查找标签输入框...")
        snapshot = mcp_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2)

        try:
            input_uid = self.find_tag_input(snapshot_text)
            print(f"  [OK] 输入框 uid={input_uid}")
        except Exception as e:
            result['message'] = f'未找到标签输入框：{e}'
            print(f"  [ERROR] {result['message']}")
            return result

        # Step 6: 填充标签
        print("  [Step 6] 填充标签...")
        tags_str = ' '.join(tags)
        mcp_fill(uid=input_uid, value=tags_str)
        time.sleep(0.5)

        # Step 7: 获取快照，找保存按钮
        print("  [Step 7] 查找保存按钮...")
        snapshot = mcp_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2)

        try:
            save_uid = self.find_save_button(snapshot_text)
            print(f"  [OK] 保存按钮 uid={save_uid}")
        except Exception as e:
            result['message'] = f'未找到保存按钮：{e}'
            print(f"  [ERROR] {result['message']}")
            return result

        # Step 8: 点击保存
        print("  [Step 8] 点击保存按钮...")
        mcp_click(uid=save_uid)
        time.sleep(1.5)

        # 成功
        result['success'] = True
        result['message'] = '标签添加成功'
        result['tags'] = tags
        print(f"  [OK] 完成!")

        return result

    def run_batch(self, start: int, end: int, album_list: list = None,
                  mcp_navigate=None, mcp_snapshot=None, mcp_click=None, mcp_fill=None):
        """
        处理一批专辑

        Args:
            start: 起始索引
            end: 结束索引
            album_list: 专辑列表
            mcp_navigate: MCP navigate_page 函数
            mcp_snapshot: MCP take_snapshot 函数
            mcp_click: MCP click 函数
            mcp_fill: MCP fill 函数
        """
        if album_list is None:
            album_list = self.load_album_list()

        # 进度文件
        progress_file = f"mcp_progress_{start}_{end}.json"
        processed = []
        failed = []

        # 加载进度
        if Path(progress_file).exists():
            with open(progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                processed = data.get('processed', [])
                failed = data.get('failed', [])
                print(f"[INFO] 加载进度：已处理 {len(processed)}, 失败 {len(failed)}")

        print("\n" + "=" * 60)
        print("豆瓣音乐自动标签添加器 - MCP 版")
        print("=" * 60)
        print(f"批次范围：{start} - {end}")
        print(f"专辑总数：{len(album_list)}")
        print(f"待处理：{end - start + 1} 张")
        print("=" * 60)

        # 处理专辑
        for i in range(start, min(end + 1, len(album_list))):
            album = album_list[i]
            subject_id = album.get('subject_id', '')
            title = album.get('title', 'Unknown')

            # 跳过已处理
            if any(p['subject_id'] == subject_id for p in processed):
                print(f"\n[{i}] [SKIP] 已处理：{title[:50]}")
                continue

            if not subject_id:
                print(f"\n[{i}] [SKIP] 无效条目")
                failed.append({
                    'index': i,
                    'subject_id': '',
                    'title': title,
                    'reason': 'invalid_entry'
                })
                continue

            # 处理专辑
            result = self.process_album(
                subject_id, title, i,
                mcp_navigate, mcp_snapshot, mcp_click, mcp_fill
            )

            if result['success']:
                processed.append({
                    'index': i,
                    'subject_id': subject_id,
                    'title': title,
                    'tags': result['tags'],
                    'processed_at': datetime.now().isoformat()
                })
            else:
                failed.append({
                    'index': i,
                    'subject_id': subject_id,
                    'title': title,
                    'reason': result['message']
                })

            # 保存进度（每 10 张）
            if len(processed) % 10 == 0 and len(processed) > 0:
                self.save_progress(progress_file, processed, failed)
                print(f"\n[CHECKPOINT] 进度已保存")

            # 延迟（除最后一张）
            if i < min(end, len(album_list) - 1):
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
        total = len(processed) + len(failed)
        if total > 0:
            print(f"成功率：{len(processed) / total * 100:.1f}%")

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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='豆瓣音乐自动标签添加器')
    parser.add_argument('--start', type=int, default=0, help='起始索引')
    parser.add_argument('--end', type=int, default=10, help='结束索引')
    parser.add_argument('--cookie', type=str, default='cookie.txt', help='Cookie 文件')

    args = parser.parse_args()

    tagger = AutoTaggerMCP(args.cookie)

    print("注意：此脚本需要在 Claude Code 环境中运行")
    print("MCP 工具将通过参数注入方式调用")
    print("\n请使用以下方式运行:")
    print("  在 Claude Code 中导入此脚本并调用 run_batch() 方法")

    # 示例调用（需要 MCP 工具注入）
    # tagger.run_batch(args.start, args.end,
    #                  mcp_navigate=mcp__chrome-devtools__navigate_page,
    #                  mcp_snapshot=mcp__chrome-devtools__take_snapshot,
    #                  mcp_click=mcp__chrome-devtools__click,
    #                  mcp_fill=mcp__chrome-devtools__fill)
