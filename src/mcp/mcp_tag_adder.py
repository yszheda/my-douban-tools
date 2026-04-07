#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCP 标签添加器 - 读取已生成的标签数据，通过 MCP Chrome DevTools 批量添加

使用方法：
    在 Claude Code 会话中运行此脚本，它会自动读取标签数据并调用 MCP 工具添加
"""

import json
import sys
from pathlib import Path

def load_tags(tags_file: str) -> list:
    """加载标签数据"""
    with open(tags_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 支持多种格式
    if 'albums' in data:
        return data['albums']
    elif 'all_tags' in data:
        return data['all_tags']
    elif 'results' in data:
        # 从 results 中提取有标签的专辑
        return [r for r in data['results'] if r.get('tags')]
    else:
        print(f"未知的数据格式：{list(data.keys())}")
        return []

def main():
    if len(sys.argv) < 2:
        print("用法：python mcp_tag_adder.py <tags_file> [start_index] [end_index]")
        print("例如：python mcp_tag_adder.py progress_a.json 0 10")
        sys.exit(1)

    tags_file = sys.argv[1]
    start_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    end_index = int(sys.argv[3]) if len(sys.argv) > 3 else None

    # 加载标签数据
    albums = load_tags(tags_file)
    if end_index:
        albums = albums[start_index:end_index]
    else:
        albums = albums[start_index:]

    print(f"=" * 60)
    print(f"MCP 标签添加器")
    print(f"=" * 60)
    print(f"数据源：{tags_file}")
    print(f"专辑数量：{len(albums)}")
    print(f"=" * 60)

    # 输出待处理的专辑列表，供 Claude Code 读取并执行
    print("\n待处理专辑列表：")
    for i, album in enumerate(albums[:10]):  # 只显示前 10 张
        print(f"  {i+1}. {album['subject_id']}: {album['title'][:50]}...")
        print(f"     标签：{' '.join(album.get('tags', []))}")

    if len(albums) > 10:
        print(f"  ... 还有 {len(albums) - 10} 张专辑")

    print("\n" + "=" * 60)
    print("请将以下指令发送给 Claude Code 执行标签添加：")
    print("=" * 60)
    print(f"""
# 为这些专辑添加标签（使用 MCP Chrome DevTools）
for album in albums:
    1. navigate_page(url="https://music.douban.com/subject/{{album['subject_id']}}/")
    2. take_snapshot() → 找到"修改"按钮
    3. click(uid) → 打开编辑对话框
    4. take_snapshot() → 找到标签输入框
    5. fill(uid, " ".join(album['tags'])) → 填入标签
    6. take_snapshot() → 找到"保存"按钮
    7. click(uid) → 保存
    8. 等待 2 秒
""")

if __name__ == '__main__':
    main()
