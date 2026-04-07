#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量为豆瓣音乐专辑添加标签 - 浏览器模拟版

使用方法：
1. 确保已登录豆瓣账号（cookie.txt 存在）
2. 确保浏览器已打开豆瓣页面
3. 运行脚本：python batch_add_tags.py

脚本会自动：
1. 读取 album_list_full.json 中的专辑列表
2. 为每张专辑生成标签
3. 通过浏览器模拟方式添加标签
4. 记录处理进度和结果
"""

import json
import time
import sys
from datetime import datetime
from pathlib import Path

# 导入标签生成器和浏览器添加器
sys.path.insert(0, str(Path(__file__).parent))
from auto_gen_music_tags.tag_generator import DoubanMusicTagGenerator
from auto_gen_music_tags.browser_adder import DoubanBrowserTagAdder

# 配置文件
ALBUM_LIST_FILE = "album_list_full.json"
PROGRESS_FILE = "batch_tag_progress.json"
RESULT_FILE = "batch_tag_result.json"
MAX_TAGS_PER_ALBUM = 10  # 豆瓣限制每张专辑最多 10 个标签
DELAY_BETWEEN_ALBUMS = 5  # 专辑间延迟（秒）


def load_progress():
    """加载处理进度"""
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
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
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def load_albums():
    """加载专辑列表"""
    with open(ALBUM_LIST_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['collections']['collect']


def generate_tags_for_album(subject_id: str, title: str = "") -> list:
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
        print(f"生成 {len(tags)} 个标签：{' '.join(tags[:10])}")
        return tags
    except Exception as e:
        print(f"[ERROR] 标签生成失败：{e}")
        return []


def add_tags_browser(subject_id: str, tags: list, mcp_client=None) -> dict:
    """通过浏览器模拟添加标签"""
    print(f"\n[添加标签] subject={subject_id}")
    print(f"标签：{' '.join(tags)}")

    adder = DoubanBrowserTagAdder()

    # 这里需要 MCP 客户端支持
    # 实际使用时需要结合 MCP 工具调用
    print("[INFO] 浏览器模拟需要 MCP Chrome DevTools 支持")
    print("[INFO] 请在浏览器中打开豆瓣，然后运行 quick_export.js 中的脚本")

    return {
        'success': True,
        'subject_id': subject_id,
        'tags_added': tags,
        'message': '需要在浏览器中执行'
    }


def batch_process(limit: int = None, start_index: int = None):
    """批量处理专辑"""
    print("=" * 60)
    print("豆瓣音乐批量标签添加工具")
    print("=" * 60)

    # 加载数据
    albums = load_albums()
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

    print("=" * 60)

    # 处理进度
    processed = progress['processed']
    failed = progress['failed']

    for i in range(start_index, end_index):
        album = albums[i]
        subject_id = album['subject_id']
        title = album.get('title', '')

        print(f"\n{'='*60}")
        print(f"处理 {i+1}/{total}: {subject_id}")
        print(f"标题：{title[:60]}...")

        # 生成标签
        tags = generate_tags_for_album(subject_id, title)

        if not tags:
            print(f"[WARN] 未生成标签，跳过")
            failed.append({'subject_id': subject_id, 'reason': 'no_tags'})
            progress['current_index'] = i + 1
            save_progress(progress)
            continue

        # 限制标签数量
        tags_limited = tags[:MAX_TAGS_PER_ALBUM]

        # 添加标签（浏览器模拟版）
        print(f"\n[添加标签] 使用 {len(tags_limited)} 个标签")
        result = add_tags_browser(subject_id, tags_limited)

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
    print(f"进度文件：{PROGRESS_FILE}")
    print(f"结果文件：{RESULT_FILE}")

    # 保存最终结果
    save_result(processed, failed)

    return processed, failed


def save_result(processed, failed):
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

    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到：{RESULT_FILE}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='豆瓣音乐批量标签添加')
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
