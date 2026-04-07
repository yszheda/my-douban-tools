#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣音乐 MCP 自动标签添加器 - 直接执行版本

在 Claude Code 环境中运行，通过 MCP 工具注入
"""

import json
import time
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable

sys.path.insert(0, str(Path(__file__).parent))
from auto_gen_music_tags.tag_generator import DoubanMusicTagGenerator

# 配置常量
MAX_TAGS_PER_ALBUM = 10
DELAY_BETWEEN_ALBUMS = 5
SAVE_INTERVAL = 5

# 全局 MCP 工具（由外部注入）
mcp_navigate: Optional[Callable] = None
mcp_snapshot: Optional[Callable] = None
mcp_click: Optional[Callable] = None
mcp_fill: Optional[Callable] = None

# 专辑列表和进度
albums: List[Dict] = []
progress: Dict = {
    'current_index': 0,
    'success_count': 0,
    'failed_count': 0,
    'results': [],
    'failed': []
}


def load_data():
    """加载专辑列表和进度"""
    global albums, progress

    # 加载专辑列表
    with open('album_list_full.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict) and 'collections' in data:
        albums = data['collections'].get('collect', [])
    else:
        albums = data if isinstance(data, list) else []

    # 加载进度
    try:
        with open('mcp_executor_progress.json', 'r', encoding='utf-8') as f:
            progress = json.load(f)
        print(f"[INFO] 从进度文件恢复：索引={progress.get('current_index', 0)}")
    except:
        print("[INFO] 无进度文件，从头开始")
        progress = {
            'current_index': 0,
            'success_count': 0,
            'failed_count': 0,
            'results': [],
            'failed': []
        }


def save_progress():
    """保存进度"""
    with open('mcp_executor_progress.json', 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)
    print(f"[INFO] 进度已保存：索引={progress['current_index']}")


def generate_tags(subject_id: str, album_info: Dict = None) -> List[str]:
    """生成标签"""
    tagger = DoubanMusicTagGenerator(cookie_file='cookie.txt')
    result = tagger.generate_tags(subject_id, album_info, verbose=False)
    tags = result.get('tags_all', [])
    return tags[:MAX_TAGS_PER_ALBUM]


def navigate_to_album(subject_id: str):
    """导航到专辑页面"""
    url = f"https://music.douban.com/subject/{subject_id}/"
    print(f"[MCP] 导航：{url}")
    if mcp_navigate:
        mcp_navigate(url=url, type="url")
    time.sleep(2)


def take_snapshot() -> Dict:
    """获取页面快照"""
    if mcp_snapshot:
        return mcp_snapshot()
    return {}


def click_element(uid: str):
    """点击元素"""
    print(f"[MCP] 点击 uid={uid}")
    if mcp_click:
        mcp_click(uid=uid)


def fill_input(uid: str, value: str):
    """填充输入框"""
    print(f"[MCP] 填充 uid={uid}, value={value}")
    if mcp_fill:
        mcp_fill(uid=uid, value=value)


def find_modify_button(snapshot_text: str) -> Optional[str]:
    """查找修改按钮"""
    for line in snapshot_text.split('\n'):
        if '修改' in line and ('link' in line or 'button' in line):
            match = re.search(r'uid=(\d+_\d+)', line)
            if match:
                return match.group(1)
    return None


def find_tag_input(snapshot_text: str) -> Optional[str]:
    """查找标签输入框"""
    for line in snapshot_text.split('\n'):
        if 'textbox' in line:
            if 'uid=2_' in line:
                match = re.search(r'uid=(2_\d+)', line)
                if match:
                    return match.group(1)
            match = re.search(r'uid=(\d+_\d+)', line)
            if match:
                return match.group(1)
    return None


def find_save_button(snapshot_text: str) -> Optional[str]:
    """查找保存按钮"""
    for line in snapshot_text.split('\n'):
        if '保存' in line and 'button' in line:
            match = re.search(r'uid=(\d+_\d+)', line)
            if match:
                return match.group(1)
    return None


def add_tags(subject_id: str, tags: List[str]) -> Dict:
    """添加标签"""
    result = {'success': False, 'message': '', 'tags': []}

    print(f"\n[MCP] 开始添加标签 - subject={subject_id}")
    print(f"[MCP] 标签：{' '.join(tags)}")
    print("=" * 60)

    try:
        # Step 1: 导航
        navigate_to_album(subject_id)

        # Step 2: 找修改按钮
        snapshot = take_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2) if isinstance(snapshot, dict) else str(snapshot)

        modify_uid = find_modify_button(snapshot_text)
        if not modify_uid:
            result['message'] = '未找到修改按钮'
            print(f"[ERROR] {result['message']}")
            return result
        print(f"[OK] 修改按钮 uid={modify_uid}")

        # Step 3: 点击修改
        click_element(modify_uid)
        time.sleep(1)

        # Step 4: 找输入框
        snapshot = take_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2) if isinstance(snapshot, dict) else str(snapshot)

        input_uid = find_tag_input(snapshot_text)
        if not input_uid:
            result['message'] = '未找到标签输入框'
            print(f"[ERROR] {result['message']}")
            return result
        print(f"[OK] 输入框 uid={input_uid}")

        # Step 5: 填充标签
        tags_str = ' '.join(tags)
        print(f"[INFO] 填充标签：{tags_str}")
        fill_input(input_uid, tags_str)
        time.sleep(0.5)

        # Step 6: 找保存按钮
        snapshot = take_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2) if isinstance(snapshot, dict) else str(snapshot)

        save_uid = find_save_button(snapshot_text)
        if not save_uid:
            result['message'] = '未找到保存按钮'
            print(f"[ERROR] {result['message']}")
            return result
        print(f"[OK] 保存按钮 uid={save_uid}")

        # Step 7: 点击保存
        click_element(save_uid)
        time.sleep(1.5)

        result['success'] = True
        result['message'] = '标签添加成功'
        result['tags'] = tags
        print("[OK] 完成!")

        return result

    except Exception as e:
        result['message'] = f'添加标签失败：{e}'
        print(f"[ERROR] {result['message']}")
        return result


def process_album(album: Dict, index: int, total: int) -> Dict:
    """处理单张专辑"""
    subject_id = album.get('subject_id', '')
    title = album.get('title', 'Unknown')

    # 清理标题
    safe_title = title.encode('utf-8', errors='ignore').decode('utf-8')
    safe_title = safe_title.encode('gbk', errors='ignore').decode('gbk')

    print(f"\n[{index+1}/{total}] Processing: {safe_title}")
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
    tags = generate_tags(subject_id, album)

    if not tags:
        result['message'] = '未生成标签'
        print(f"         [ERROR] {result['message']}")
        return result

    print(f"         生成 {len(tags)} 个标签：{' '.join(tags[:5])}...")

    # Step 2: 添加标签
    print("[Step 2] 添加标签...")
    add_result = add_tags(subject_id, tags)

    if add_result.get('success', False):
        result['success'] = True
        result['message'] = add_result.get('message', '未知错误')
        result['tags'] = add_result.get('tags', [])
        print(f"         [OK] {result['message']}")
    else:
        result['message'] = add_result.get('message', '未知错误')
        print(f"         [ERROR] {result['message']}")

    return result


def inject_mcp_tools(navigate_fn, snapshot_fn, click_fn, fill_fn):
    """注入 MCP 工具函数"""
    global mcp_navigate, mcp_snapshot, mcp_click, mcp_fill
    mcp_navigate = navigate_fn
    mcp_snapshot = snapshot_fn
    mcp_click = click_fn
    mcp_fill = fill_fn
    print("[INFO] MCP 工具已注入")


def run_batch(start_index: int = None, end_index: int = None):
    """主执行函数"""
    global progress

    load_data()

    total = len(albums)
    print(f"\n{'='*60}")
    print("豆瓣音乐 MCP 自动标签添加器")
    print(f"{'='*60}")
    print(f"专辑总数：{total}")

    if start_index is None:
        start_index = progress.get('current_index', 0)
    if end_index is None:
        end_index = total - 1

    print(f"起始索引：{start_index}")
    print(f"结束索引：{end_index}")
    print(f"待处理：{end_index - start_index + 1} 张专辑")
    print(f"{'='*60}\n")

    results = progress.get('results', [])
    failed = progress.get('failed', [])
    success_count = progress.get('success_count', 0)
    failed_count = progress.get('failed_count', 0)

    for i in range(start_index, min(end_index + 1, total)):
        album = albums[i]
        subject_id = album.get('subject_id', '')

        if not subject_id:
            print(f"\n[{i+1}/{total}] [SKIP] 无效条目，跳过")
            failed_count += 1
            failed.append({
                'index': i,
                'subject_id': '',
                'title': album.get('title', 'Unknown'),
                'reason': 'invalid_entry'
            })
            continue

        result = process_album(album, i, total)
        results.append(result)

        if result['success']:
            success_count += 1
        else:
            failed_count += 1

        # 保存进度
        if (success_count + failed_count) % SAVE_INTERVAL == 0:
            print(f"\n[CHECKPOINT] 已处理 {success_count + failed_count} 张，保存进度...")
            progress['current_index'] = i + 1
            progress['success_count'] = success_count
            progress['failed_count'] = failed_count
            progress['results'] = results
            progress['failed'] = failed
            progress['last_updated'] = datetime.now().isoformat()
            save_progress()

        # 延迟
        if i < min(end_index, total - 1):
            print(f"[DELAY] 等待 {DELAY_BETWEEN_ALBUMS} 秒...")
            time.sleep(DELAY_BETWEEN_ALBUMS)

    # 最终保存
    print(f"\n{'='*60}")
    print("批次处理完成")
    print(f"{'='*60}")

    progress['current_index'] = min(end_index + 1, total)
    progress['success_count'] = success_count
    progress['failed_count'] = failed_count
    progress['results'] = results
    progress['failed'] = failed
    progress['completed_at'] = datetime.now().isoformat()
    save_progress()

    # 打印摘要
    total_processed = success_count + failed_count
    success_rate = success_rate = success_count / total_processed * 100 if total_processed > 0 else 0
    print(f"\n摘要:")
    print(f"  已处理：{total_processed} 张")
    print(f"  成功：{success_count} 张")
    print(f"  失败：{failed_count} 张")
    print(f"  成功率：{success_rate:.1f}%")


if __name__ == '__main__':
    # 独立运行时（不使用 MCP 工具）
    print("独立运行模式：仅测试标签生成")
    load_data()

    # 测试索引 1
    album = albums[1]
    subject_id = album.get('subject_id', '')
    print(f"\n测试专辑：{album.get('title', 'Unknown')}")
    print(f"Subject ID: {subject_id}")

    tags = generate_tags(subject_id, album)
    print(f"\n生成标签：{' '.join(tags)}")
