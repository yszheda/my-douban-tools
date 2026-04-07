#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣音乐 MCP 批量标签添加器 - 会话执行版
直接在当前 Claude Code 会话中使用 MCP 工具执行
"""

import json
import time
import sys
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from auto_gen_music_tags.tag_generator import DoubanMusicTagGenerator

# 配置
MAX_TAGS = 10
DELAY = 5
SAVE_INTERVAL = 5

def load_albums():
    with open('album_list_full.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict) and 'collections' in data:
        return data['collections'].get('collect', [])
    return data if isinstance(data, list) else []

def load_progress():
    try:
        with open('mcp_executor_progress.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'current_index': 0, 'success_count': 0, 'failed_count': 0, 'results': [], 'failed': []}

def save_progress(data):
    with open('mcp_executor_progress.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_tags(subject_id, album_info=None):
    tagger = DoubanMusicTagGenerator(cookie_file='cookie.txt')
    result = tagger.generate_tags(subject_id, album_info, verbose=False)
    return result.get('tags_all', [])[:MAX_TAGS]

def find_button(snapshot_text, btn_name):
    for line in snapshot_text.split('\n'):
        if btn_name in line and ('link' in line or 'button' in line):
            match = re.search(r'uid=(\d+_\d+)', line)
            if match:
                return match.group(1)
    return None

def find_input(snapshot_text):
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

def process_album(subject_id, title, idx, total):
    """处理单张专辑"""
    safe_title = title[:50].encode('utf-8', errors='ignore').decode('utf-8')
    print(f"\n[{idx+1}/{total}] {safe_title} ({subject_id})")

    try:
        # 生成标签
        tags = generate_tags(subject_id)
        if not tags:
            print(f"  [ERROR] 未生成标签")
            return False, []
        print(f"  标签：{' '.join(tags)}")

        # 导航
        mcp__chrome-devtools__navigate_page(url=f"https://music.douban.com/subject/{subject_id}/", type="url")
        time.sleep(2)

        # 找修改按钮
        snapshot = mcp__chrome-devtools__take_snapshot()
        text = json.dumps(snapshot, ensure_ascii=False, indent=2)
        modify_uid = find_button(text, '修改')
        if not modify_uid:
            print(f"  [ERROR] 未找到修改按钮")
            return False, []

        # 点击修改
        mcp__chrome-devtools__click(uid=modify_uid)
        time.sleep(1)

        # 找输入框
        snapshot = mcp__chrome-devtools__take_snapshot()
        text = json.dumps(snapshot, ensure_ascii=False, indent=2)
        input_uid = find_input(text)
        if not input_uid:
            print(f"  [ERROR] 未找到输入框")
            return False, []

        # 填充标签
        mcp__chrome-devtools__fill(uid=input_uid, value=' '.join(tags))
        time.sleep(0.5)

        # 找保存按钮
        snapshot = mcp__chrome-devtools__take_snapshot()
        text = json.dumps(snapshot, ensure_ascii=False, indent=2)
        save_uid = find_button(text, '保存')
        if not save_uid:
            print(f"  [ERROR] 未找到保存按钮")
            return False, []

        # 保存
        mcp__chrome-devtools__click(uid=save_uid)
        time.sleep(1.5)

        print(f"  [OK] 成功")
        return True, tags

    except Exception as e:
        print(f"  [ERROR] {e}")
        return False, []

def run_batch(start_idx=0, end_idx=None):
    """批量执行"""
    albums = load_albums()
    total = len(albums)
    progress = load_progress()

    if start_idx == 0 and progress.get('current_index', 0) > 0:
        start_idx = progress['current_index']

    if end_idx is None:
        end_idx = total - 1

    print("=" * 60)
    print(f"豆瓣音乐 MCP 批量标签添加器")
    print(f"专辑总数：{total}")
    print(f"起始索引：{start_idx}")
    print(f"结束索引：{end_idx}")
    print(f"待处理：{end_idx - start_idx + 1} 张")
    print("=" * 60)

    results = progress.get('results', [])
    failed = progress.get('failed', [])
    success_count = progress.get('success_count', 0)
    failed_count = progress.get('failed_count', 0)

    for i in range(start_idx, min(end_idx + 1, total)):
        album = albums[i]
        subject_id = album.get('subject_id', '')
        title = album.get('title', 'Unknown')

        if not subject_id:
            print(f"\n[{i+1}/{total}] [SKIP] 无效条目")
            failed_count += 1
            failed.append({'index': i, 'reason': 'invalid_entry'})
            continue

        success, tags = process_album(subject_id, title, i, total)

        results.append({
            'index': i,
            'subject_id': subject_id,
            'title': title,
            'success': success,
            'tags': tags
        })

        if success:
            success_count += 1
        else:
            failed_count += 1

        # 保存进度
        if (success_count + failed_count) % SAVE_INTERVAL == 0:
            progress.update({
                'current_index': i + 1,
                'success_count': success_count,
                'failed_count': failed_count,
                'results': results,
                'failed': failed,
                'last_updated': datetime.now().isoformat()
            })
            save_progress(progress)
            print(f"\n[CHECKPOINT] 进度已保存")

        # 延迟
        if i < min(end_idx, total - 1):
            time.sleep(DELAY)

    # 最终保存
    progress.update({
        'current_index': min(end_idx + 1, total),
        'success_count': success_count,
        'failed_count': failed_count,
        'results': results,
        'failed': failed,
        'completed_at': datetime.now().isoformat()
    })
    save_progress(progress)

    print("\n" + "=" * 60)
    print(f"处理完成!")
    print(f"成功：{success_count} 张")
    print(f"失败：{failed_count} 张")
    print(f"成功率：{success_count/(success_count+failed_count)*100:.1f}%")
    print("=" * 60)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--end', type=int, default=None)
    args = parser.parse_args()

    run_batch(start_idx=args.start, end_idx=args.end)
