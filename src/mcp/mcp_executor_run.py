#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣音乐 MCP 自动标签添加器 - 直接执行版本

在 Claude Code 环境中运行，通过 MCP 工具注入
"""

import json
import time
import sys
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

def load_album_list(album_list_file: str = "album_list_full.json") -> List[Dict]:
    """加载专辑列表"""
    with open(album_list_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict) and 'collections' in data:
        return data['collections'].get('collect', [])
    return data if isinstance(data, list) else []

def load_progress(progress_file: str = "mcp_executor_progress.json") -> Dict:
    """加载进度"""
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'current_index': 0, 'success_count': 0, 'failed_count': 0, 'results': [], 'failed': []}

def save_progress(data: Dict, progress_file: str = "mcp_executor_progress.json") -> None:
    """保存进度"""
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_tags(subject_id: str, album_info: Dict = None) -> List[str]:
    """生成标签"""
    tagger = DoubanMusicTagGenerator(cookie_file='cookie.txt')
    result = tagger.generate_tags(subject_id, album_info, verbose=False)
    tags = result.get('tags_all', [])[:MAX_TAGS_PER_ALBUM]
    return tags

def navigate_to_album(subject_id: str) -> None:
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

def click_element(uid: str) -> None:
    """点击元素"""
    if mcp_click:
        mcp_click(uid=uid)

def fill_input(uid: str, value: str) -> None:
    """填充输入框"""
    if mcp_fill:
        mcp_fill(uid=uid, value=value)

def find_modify_button(snapshot_text: str) -> Optional[str]:
    """查找修改按钮"""
    for line in snapshot_text.split('\n'):
        if '修改' in line and 'link' in line:
            import re
            match = re.search(r'uid=(\d+_\d+)', line)
            if match:
                return match.group(1)
    return None

def find_tag_input(snapshot_text: str) -> Optional[str]:
    """查找标签输入框"""
    import re
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
    import re
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

    result = {'index': index, 'subject_id': subject_id, 'title': title, 'success': False, 'message': '', 'tags': []}

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

def run(start_index: int = 0, end_index: int = None):
    """主执行函数"""
    print("\n" + "=" * 60)
    print("豆瓣音乐 MCP 自动标签添加器")
    print("=" * 60)

    albums = load_album_list()
    total = len(albums)
    print(f"专辑总数：{total}")

    # 加载进度
    progress = load_progress()
    if start_index == 0 and progress.get('current_index', 0) > 0:
        start_index = progress['current_index']
        print(f"[INFO] 从进度文件恢复：从索引 {start_index} 开始")

    if end_index is None:
        end_index = total - 1

    print(f"起始索引：{start_index}")
    print(f"结束索引：{end_index}")
    print(f"待处理：{end_index - start_index + 1} 张专辑")
    print("=" * 60)

    results = progress.get('results', [])
    failed = progress.get('failed', [])
    success_count = progress.get('success_count', 0)
    failed_count = progress.get('failed_count', 0)

    # 主循环
    for i in range(start_index, min(end_index + 1, total)):
        album = albums[i]
        subject_id = album.get('subject_id', '')

        if not subject_id:
            print(f"\n[{i+1}/{total}] [SKIP] 无效条目，跳过")
            failed_count += 1
            failed.append({'index': i, 'subject_id': '', 'title': album.get('title', 'Unknown'), 'reason': 'invalid_entry'})
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
            save_progress(progress)

        # 延迟
        if i < min(end_index, total - 1):
            print(f"[DELAY] 等待 {DELAY_BETWEEN_ALBUMS} 秒...")
            time.sleep(DELAY_BETWEEN_ALBUMS)

    # 最终保存
    print("\n" + "=" * 60)
    print("批次处理完成")
    print("=" * 60)

    progress['current_index'] = min(end_index + 1, total)
    progress['success_count'] = success_count
    progress['failed_count'] = failed_count
    progress['results'] = results
    progress['failed'] = failed
    progress['completed_at'] = datetime.now().isoformat()
    save_progress(progress)

    # 保存最终结果
    total_processed = success_count + failed_count
    final_result = {
        'completed_at': datetime.now().isoformat(),
        'start_index': start_index,
        'end_index': end_index,
        'processed_count': total_processed,
        'success_count': success_count,
        'failed_count': failed_count,
        'success_rate': success_count / total_processed if total_processed > 0 else 0,
        'results': results,
        'failed': failed
    }

    with open('mcp_executor_result.json', 'w', encoding='utf-8') as f:
        json.dump(final_result, f, ensure_ascii=False, indent=2)

    print(f"\n摘要:")
    print(f"  已处理：{total_processed} 张")
    print(f"  成功：{success_count} 张")
    print(f"  失败：{failed_count} 张")
    print(f"  成功率：{success_count / total_processed * 100:.1f}%")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='豆瓣音乐 MCP 自动标签添加器')
    parser.add_argument('--start', type=int, default=0, help='起始索引')
    parser.add_argument('--end', type=int, default=None, help='结束索引')
    args = parser.parse_args()

    run(start_index=args.start, end_index=args.end)
