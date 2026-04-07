#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""豆瓣音乐批量标签添加 - MCP Chrome DevTools 版

使用方法：
1. 打开 Chrome 浏览器，访问豆瓣音乐并登录
2. 确保 MCP Chrome DevTools 已配置
3. 运行脚本：python batch_tagger_mcp.py --limit 10

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
from datetime import datetime
from pathlib import Path

# 导入标签生成器和添加器
sys.path.insert(0, str(Path(__file__).parent))
from auto_gen_music_tags.tag_generator import DoubanMusicTagGenerator
from auto_gen_music_tags.api_adder import DoubanApiTagAdder

# 配置
ALBUM_LIST_FILE = "album_list_full.json"
PROGRESS_FILE = "batch_tag_progress.json"
RESULT_FILE = "batch_tag_result.json"
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


class ApiTagger:
    """API 版标签添加器"""

    def __init__(self):
        self.tagger = DoubanApiTagAdder()

    def add_tags(self, subject_id: str, tags: list) -> dict:
        """执行标签添加流程"""
        print(f"\n[API] 开始添加标签 - subject={subject_id}")
        print(f"[API] 标签：{' '.join(tags)}")
        print("=" * 50)

        try:
            # 使用 API 批量添加标签（逐标签提交）
            result = self.tagger.add_tags(subject_id, tags, delay=0.5)

            if result['success']:
                print(f"[API] 成功添加 {len(result['success'])} 个标签")
                return {
                    'success': True,
                    'message': f"成功添加 {len(result['success'])} 个标签",
                    'added': result['success'],
                    'failed': result['failed']
                }
            else:
                return {'success': False, 'message': '所有标签添加失败'}

        except Exception as e:
            print(f"[API] 错误：{e}")
            return {'success': False, 'message': str(e)}


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
    api_tagger = ApiTagger()

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

        # 通过 API 添加标签
        print(f"\n[添加标签] 使用 {len(tags_limited)} 个标签：{' '.join(tags_limited)}")
        result = api_tagger.add_tags(subject_id, tags_limited)

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
