#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修复专辑信息文件 - 添加缺失的专辑名称和艺术家字段
"""

import re
from pathlib import Path
import sys

# 强制使用 UTF-8 编码输出
sys.stdout.reconfigure(encoding='utf-8')

def extract_info_from_dirname(dir_name):
    """从目录名中提取专辑名称和艺术家信息"""
    # 移除年份和格式信息 (如 1956, 2CD, 3CD 等)
    clean_name = re.sub(r'\s+\(\w+\s*\d*CD\)', '', dir_name)
    clean_name = re.sub(r'\s+\(\d{4}\)', '', clean_name)

    # 尝试提取艺术家（通常是目录名开头的部分）
    # 格式：艺术家 - 专辑名称
    match = re.match(r'^([^-]+)\s*-\s*(.+)$', clean_name)
    if match:
        artist = match.group(1).strip()
        title = match.group(2).strip()
        # 恢复被移除的年份和格式信息
        title = dir_name.replace(artist + ' - ', '').strip()
        return title, artist

    return dir_name, ''

def fix_album_info_file(file_path: Path) -> tuple[bool, str]:
    """
    修复专辑信息文件
    返回：(是否修改，消息)
    """
    if not file_path.exists():
        return False, "文件不存在"

    content = file_path.read_text(encoding='utf-8')
    original_content = content

    # 检查是否已有"专辑名称"字段（支持多种格式）
    has_title = bool(
        re.search(r'-\s*\*\*专辑名称\*\*\s*[:：]\s*(.+?)(?:\n|$)', content) or
        re.search(r'##\s*专辑名称\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    )

    # 检查是否已有"艺术家"字段（支持多种格式）
    has_artist = bool(
        re.search(r'-\s*\*\*艺术家\*\*\s*[:：]\s*(.+?)(?:\n|$)', content) or
        re.search(r'##\s*艺术家\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    )

    if has_title and has_artist:
        return False, "已有专辑名称和艺术家字段"

    # 确保有## 基础信息部分
    if '## 基础信息' not in content:
        content = content.replace('## 专辑信息', '## 基础信息')
        # 如果是段落格式，转换为列表格式
        title_match = re.search(r'##\s*专辑名称\s*\n(.+?)(?=\n##)', content, re.DOTALL)
        if title_match and '## 基础信息' not in content:
            title_text = title_match.group(1).strip()
            content = re.sub(
                r'##\s*专辑名称\s*\n.+?(?=\n##)',
                f'## 基础信息\n- **专辑名称**: {title_text}',
                content,
                flags=re.DOTALL
            )

        artist_match = re.search(r'##\s*艺术家\s*\n(.+?)(?=\n##)', content, re.DOTALL)
        if artist_match:
            artist_text = artist_match.group(1).strip()
            # 提取**名字**部分
            name_match = re.search(r'\*\*(.+?)\*\*', artist_text)
            if name_match:
                artist_name = name_match.group(1).strip()
                content = re.sub(
                    r'##\s*艺术家\s*\n.+?(?=\n##)',
                    f'- **艺术家**: {artist_name}',
                    content,
                    flags=re.DOTALL
                )

    # 如果需要添加专辑名称
    if not has_title:
        # 从目录名中提取专辑名称
        dir_name = file_path.parent.name
        album_title, _ = extract_info_from_dirname(dir_name)

        # 在## 基础信息后添加专辑名称
        insert_text = f"- **专辑名称**: {album_title}\n"
        content = re.sub(r'(##\s*基础信息\s*\n)', r'\1' + insert_text, content)
        print(f"  添加专辑名称：{album_title[:50]}...")

    # 如果需要添加艺术家
    if not has_artist:
        # 从目录名中提取艺术家
        dir_name = file_path.parent.name
        _, album_artist = extract_info_from_dirname(dir_name)

        if album_artist:
            # 在专辑名称后添加艺术家
            insert_text = f"- **艺术家**: {album_artist}\n"
            content = re.sub(r'(\*\*专辑名称\*\*\s*[:：].*\n)', r'\1' + insert_text, content)
            print(f"  添加艺术家：{album_artist[:50]}...")

    # 写回文件
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        return True, "已修复"
    else:
        return False, "无需修改"


def main():
    base_dir = Path(__file__).parent.parent

    # 扫描所有专辑目录
    album_dirs = [d for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]

    fixed_count = 0
    skipped_count = 0
    total_count = 0

    for album_dir in sorted(album_dirs):
        info_file = album_dir / "专辑基本信息.md"
        if info_file.exists():
            total_count += 1
            fixed, msg = fix_album_info_file(info_file)
            if fixed:
                fixed_count += 1
                print(f"\n修复：{album_dir.name}")
            else:
                skipped_count += 1

    print(f"\n\n修复完成！")
    print(f"总专辑数：{total_count}")
    print(f"已修复：{fixed_count}")
    print(f"已跳过：{skipped_count}")


if __name__ == '__main__':
    main()
