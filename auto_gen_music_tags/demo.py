#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""豆瓣标签添加演示脚本

演示两种方式：
1. API 版 - 快速但可能被反爬
2. 浏览器模拟版 - 稳定可靠
"""

import json
import sys

def load_tags(subject_id: str = "35617623"):
    """加载标签数据"""
    try:
        with open(f'tags_{subject_id}.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['subject_id'], data['tags_all']
    except Exception as e:
        print(f"[WARN] 无法加载标签文件：{e}")
        # 回退到生成标签
        from generate_tags_unified import DoubanMusicTagGenerator
        tagger = DoubanMusicTagGenerator()
        result = tagger.generate_tags(subject_id, verbose=False)
        return result['subject_id'], result['tags_all']

def demo_api(subject_id: str, tags: list):
    """演示 API 版"""
    print("\n" + "=" * 60)
    print("【方式 A】API 版标签添加")
    print("=" * 60)

    from api_tag_adder import DoubanApiTagAdder
    adder = DoubanApiTagAdder()

    # 豆瓣限制最多 10 个标签
    tags_limited = tags[:10]
    print(f"[API] 使用标签 ({len(tags_limited)} 个): {' '.join(tags_limited)}")

    result = adder.add_tags(subject_id, tags_limited)

    print(f"\n结果：{'成功' if result['success'] else '失败'}")
    print(f"消息：{result['message']}")
    return result

def demo_browser(subject_id: str, tags: list):
    """演示浏览器模拟版"""
    print("\n" + "=" * 60)
    print("【方式 B】浏览器模拟版标签添加")
    print("=" * 60)

    from browser_tag_adder import DoubanBrowserTagAdder
    adder = DoubanBrowserTagAdder()

    tags_limited = tags[:10]
    print(f"[Browser] 使用标签 ({len(tags_limited)} 个): {' '.join(tags_limited)}")

    result = adder.add_tags(subject_id, tags_limited)

    print(f"\n结果：{'成功' if result['success'] else '失败'}")
    print(f"消息：{result['message']}")
    return result

def main():
    """主函数"""
    print("=" * 60)
    print("豆瓣音乐标签添加演示")
    print("=" * 60)

    # 加载标签数据
    subject_id, tags = load_tags("35617623")

    print(f"\n专辑：{subject_id}")
    print(f"标题：Chopin: Cello Sonata Op.65; Alkan:Cello Sonata Op.47")
    print(f"标签总数：{len(tags)}")
    print(f"使用前 10 个：{' '.join(tags[:10])}")

    # 演示两种方式
    print("\n按 Enter 键开始 API 版演示...")
    input()

    api_result = demo_api(subject_id, tags)

    # 如果 API 失败，提供浏览器版选项
    if not api_result['success']:
        print("\n[INFO] API 版失败，是否切换到浏览器模拟版？")
        print("按 Enter 键继续浏览器版，或输入 'n' 跳过...")
        choice = input().strip().lower()
        if choice != 'n':
            browser_result = demo_browser(subject_id, tags)
            return browser_result
    else:
        print("\n[INFO] API 版成功，是否继续浏览器模拟版演示？")
        print("按 Enter 键继续，或输入 'n' 跳过...")
        choice = input().strip().lower()
        if choice != 'n':
            browser_result = demo_browser(subject_id, tags)
            return browser_result

    return api_result

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] 未预期错误：{e}")
        sys.exit(1)
