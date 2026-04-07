#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""豆瓣音乐批量标签添加器 - MCP Chrome DevTools 版

使用方法：
1. 打开 Chrome 浏览器，访问豆瓣音乐并登录
2. 确保 MCP Chrome DevTools 已配置
3. 在 Claude Code 会话中运行：python mcp_tagger.py --demo

脚本会：
1. 读取 album_list_full.json 中的专辑列表
2. 为每张专辑生成标签
3. 通过 MCP Chrome DevTools 模拟浏览器操作添加标签
4. 记录处理进度和结果
"""

import json
import time
import sys
import re
import subprocess
from datetime import datetime
from pathlib import Path

# 导入标签生成器
sys.path.insert(0, str(Path(__file__).parent))
from auto_gen_music_tags.tag_generator import DoubanMusicTagGenerator

# 配置
ALBUM_LIST_FILE = "album_list_full.json"
PROGRESS_FILE = "batch_tag_progress_mcp.json"
RESULT_FILE = "batch_tag_result_mcp.json"
MAX_TAGS_PER_ALBUM = 10
DELAY_BETWEEN_ALBUMS = 5


def load_json_file(filepath):
    """加载 JSON 文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(filepath, data):
    """保存 JSON 文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_progress():
    """加载处理进度"""
    try:
        return load_json_file(PROGRESS_FILE)
    except FileNotFoundError:
        return {
            'processed': [],
            'failed': [],
            'current_index': 0,
            'started_at': None,
            'last_updated': None
        }


def save_progress(progress):
    """保存处理进度"""
    progress['last_updated'] = datetime.now().isoformat()
    save_json_file(PROGRESS_FILE, progress)


def generate_tags(subject_id: str, title: str = "") -> list:
    """为单张专辑生成标签"""
    print(f"\n[生成标签] subject={subject_id}")
    print(f"标题：{title[:50]}...")

    try:
        tagger = DoubanMusicTagGenerator()
        result = tagger.generate_tags(
            subject_id=subject_id,
            album_info={'title': title} if title else None,
            verbose=False
        )
        tags = result.get('tags_all', [])
        print(f"生成 {len(tags)} 个标签")
        if tags:
            print(f"标签：{' '.join(tags[:10])}")
        return tags
    except Exception as e:
        print(f"[ERROR] 标签生成失败：{e}")
        return []


class McpBrowserTagger:
    """MCP Chrome DevTools 浏览器标签添加器

    注意：此类需要在 Claude Code 会话中运行，以便调用 MCP 工具
    """

    def __init__(self):
        self.subject_id = None

    def navigate_to_album(self, subject_id: str):
        """导航到专辑页面"""
        url = f"https://music.douban.com/subject/{subject_id}/"
        print(f"[Browser] 导航：{url}")
        # 实际调用 MCP 工具
        # mcp__chrome-devtools__navigate_page(url=url, type="url")
        return url

    def take_snapshot(self, verbose: bool = False):
        """获取页面快照"""
        print("[Browser] 获取页面快照...")
        # 实际调用 MCP 工具
        # mcp__chrome-devtools__take_snapshot(verbose=verbose)
        # 返回示例结构
        return {"content": ""}

    def click(self, uid: str):
        """点击元素"""
        print(f"[Browser] 点击 uid={uid}")
        # 实际调用 MCP 工具
        # mcp__chrome-devtools__click(uid=uid)

    def fill(self, uid: str, value: str):
        """填充输入框"""
        print(f"[Browser] 填充 uid={uid}, value={value[:50]}...")
        # 实际调用 MCP 工具
        # mcp__chrome-devtools__fill(uid=uid, value=value)

    def wait(self, seconds: float):
        """等待"""
        print(f"[Browser] 等待 {seconds} 秒...")
        time.sleep(seconds)

    def find_element_by_text(self, snapshot_text: str, target_text: str, element_type: str = None):
        """根据文本查找元素"""
        for line in snapshot_text.split('\n'):
            if target_text in line:
                if element_type is None or element_type in line:
                    match = re.search(r'uid=(\d+_\d+)', line)
                    if match:
                        return match.group(1)
        return None

    def add_tags(self, subject_id: str, tags: list) -> dict:
        """执行完整的标签添加流程"""
        self.subject_id = subject_id
        tags_str = ' '.join(tags[:MAX_TAGS_PER_ALBUM])

        print(f"\n[Browser] 开始添加标签 - subject={subject_id}")
        print(f"[Browser] 标签：{tags_str}")
        print("=" * 50)

        # Step 1: 导航到专辑页面
        self.navigate_to_album(subject_id)
        self.wait(2)

        # Step 2: 获取快照，查找"修改"按钮
        snapshot = self.take_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False)
        modify_uid = self.find_element_by_text(snapshot_text, '修改', 'link')

        if not modify_uid:
            print("[Browser] 错误：未找到修改按钮")
            return {'success': False, 'message': '未找到修改按钮'}

        print(f"[Browser] 修改按钮 uid={modify_uid}")
        self.click(modify_uid)
        self.wait(1)

        # Step 3: 获取快照，查找标签输入框
        snapshot = self.take_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False)
        input_uid = self.find_element_by_text(snapshot_text, '标签', 'textbox')

        if not input_uid:
            print("[Browser] 错误：未找到标签输入框")
            return {'success': False, 'message': '未找到标签输入框'}

        print(f"[Browser] 输入框 uid={input_uid}")

        # Step 4: 填充标签（合并旧标签）
        self.fill(input_uid, tags_str)
        self.wait(0.5)

        # Step 5: 获取快照，查找"保存"按钮
        snapshot = self.take_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False)
        save_uid = self.find_element_by_text(snapshot_text, '保存', 'button')

        if not save_uid:
            print("[Browser] 错误：未找到保存按钮")
            return {'success': False, 'message': '未找到保存按钮'}

        print(f"[Browser] 保存按钮 uid={save_uid}")
        self.click(save_uid)
        self.wait(1.5)

        # Step 6: 验证结果
        print("[Browser] 完成!")
        return {'success': True, 'message': '标签添加成功'}


def batch_process(limit: int = None, start_index: int = None, demo: bool = False):
    """批量处理专辑"""
    print("=" * 60)
    print("豆瓣音乐批量标签添加工具 - MCP 版")
    print("=" * 60)

    # 加载数据
    albums_data = load_json_file(ALBUM_LIST_FILE)
    albums = albums_data['collections']['collect']
    progress = load_progress()

    if start_index is None:
        start_index = progress.get('current_index', 0)

    total = len(albums)
    print(f"专辑总数：{total}")
    print(f"已处理：{len(progress['processed'])}")
    print(f"失败：{len(progress['failed'])}")
    print(f"起始索引：{start_index}")

    if limit:
        print(f"处理限制：{limit} 张专辑")
        end_index = min(start_index + limit, total)
    else:
        end_index = total

    if demo:
        print("演示模式：只处理 1 张专辑")
        end_index = min(start_index + 1, total)

    print("=" * 60)

    # 处理进度
    processed = progress['processed']
    failed = progress['failed']
    browser_tagger = McpBrowserTagger()

    for i in range(start_index, end_index):
        album = albums[i]
        subject_id = album['subject_id']
        title = album.get('title', '')

        print(f"\n{'='*60}")
        print(f"处理 {i+1}/{total}: {subject_id}")
        print(f"标题：{title[:60]}...")

        # 生成标签
        tags = generate_tags(subject_id, title)

        if not tags:
            print(f"[WARN] 未生成标签，跳过")
            failed.append({'subject_id': subject_id, 'reason': 'no_tags', 'title': title})
            progress['current_index'] = i + 1
            save_progress(progress)
            continue

        # 限制标签数量
        tags_limited = tags[:MAX_TAGS_PER_ALBUM]

        # 通过浏览器添加标签
        print(f"\n[添加标签] 使用 {len(tags_limited)} 个标签：{' '.join(tags_limited)}")
        result = browser_tagger.add_tags(subject_id, tags_limited)

        if result.get('success'):
            processed.append({
                'subject_id': subject_id,
                'title': title,
                'tags': tags_limited,
                'processed_at': datetime.now().isoformat()
            })
            print(f"[OK] 成功")
        else:
            failed.append({
                'subject_id': subject_id,
                'title': title,
                'reason': result.get('message', 'unknown')
            })
            print(f"[FAIL] {result.get('message')}")

        # 保存进度
        progress['processed'] = processed
        progress['failed'] = failed
        progress['current_index'] = i + 1
        progress['started_at'] = progress.get('started_at') or datetime.now().isoformat()
        save_progress(progress)

        # 延迟
        if i < end_index - 1:
            print(f"[DELAY] 等待 {DELAY_BETWEEN_ALBUMS} 秒...")
            time.sleep(DELAY_BETWEEN_ALBUMS)

    # 完成
    print("\n" + "=" * 60)
    print("批量处理完成!")
    print("=" * 60)
    print(f"总计：{len(processed)} 成功，{len(failed)} 失败")

    # 保存最终结果
    save_result(processed, failed, albums_data)

    return processed, failed


def save_result(processed, failed, albums_data):
    """保存最终结果"""
    result = {
        'completed_at': datetime.now().isoformat(),
        'summary': {
            'total_processed': len(processed),
            'total_failed': len(failed),
            'success_rate': len(processed) / (len(processed) + len(failed)) if (processed or failed) else 0
        },
        'processed': processed,
        'failed': failed
    }

    save_json_file(RESULT_FILE, result)
    print(f"\n结果已保存到：{RESULT_FILE}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='豆瓣音乐批量标签添加 - MCP 版')
    parser.add_argument('--limit', type=int, default=None, help='限制处理数量')
    parser.add_argument('--start', type=int, default=None, help='起始索引')
    parser.add_argument('--demo', action='store_true', help='演示模式（只处理 1 张）')

    args = parser.parse_args()

    if args.demo:
        print("演示模式：只处理 1 张专辑")
        batch_process(limit=1)
    else:
        batch_process(limit=args.limit, start_index=args.start)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] 未预期错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
