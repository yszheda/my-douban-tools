#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复失败专辑的艺术家字段
扫描所有专辑信息文件，将缺少"艺术家"字段的文件修复
"""

import re
from pathlib import Path
import sys

# 强制使用 UTF-8 编码输出
sys.stdout.reconfigure(encoding='utf-8')

# 需要替换的字段名映射
INSTRUMENT_FIELDS = [
    '钢琴', '小提琴', '大提琴', '中提琴', '长笛', '单簧管', '双簧管', '巴松管',
    '圆号', '小号', '长号', '大号', '指挥', '男高音', '女高音', '男中音',
    '女中音', '男低音', '管风琴', '羽管键琴', '吉他', '竖琴', '打击乐',
    '歌唱家', '歌手', '演奏家', '乐团', '乐队'
]

def fix_album_info_file(file_path: Path) -> tuple[bool, str]:
    """
    修复专辑信息文件
    返回：(是否修改，消息)
    """
    if not file_path.exists():
        return False, "文件不存在"

    content = file_path.read_text(encoding='utf-8')

    # 检查是否已有"艺术家"字段
    if '**艺术家**:' in content:
        return False, "已有艺术家字段"

    # 1. 将"## 专辑信息"改为"## 基础信息"
    content = content.replace('## 专辑信息', '## 基础信息')

    # 2. 查找第一个乐器字段并替换为"艺术家"
    for instrument in INSTRUMENT_FIELDS:
        # 匹配"- **乐器**:"格式
        pattern = rf'-\s*\*\*{re.escape(instrument)}\*\*:\s*([^\n]+)'
        match = re.search(pattern, content)
        if match:
            field_content = match.group(1).strip()
            # 添加角色说明
            if instrument not in field_content:
                field_content = f"{field_content}（{instrument}）"
            replacement = f'- **艺术家**: {field_content}'
            content = re.sub(pattern, replacement, content, count=1)
            print(f"  替换字段：{instrument} -> 艺术家")
            break

    # 写回文件
    file_path.write_text(content, encoding='utf-8')
    return True, "已修复"


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
                # print(f"跳过：{album_dir.name} - {msg}")

    print(f"\n\n修复完成！")
    print(f"总专辑数：{total_count}")
    print(f"已修复：{fixed_count}")
    print(f"已跳过：{skipped_count}")


if __name__ == '__main__':
    main()
