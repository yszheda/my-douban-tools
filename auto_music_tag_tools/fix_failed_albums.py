#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复失败专辑的艺术家字段
将"## 专辑信息"改为"## 基础信息"
将"钢琴"、"小提琴"等乐器字段改为"艺术家"
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
    '女中音', '男低音', '管风琴', '羽管键琴', '吉他', '竖琴', '打击乐'
]

def fix_album_info_file(file_path: Path) -> bool:
    """修复专辑信息文件"""
    if not file_path.exists():
        print(f"  文件不存在：{file_path}")
        return False

    content = file_path.read_text(encoding='utf-8')
    original_content = content

    # 1. 将"## 专辑信息"改为"## 基础信息"
    content = content.replace('## 专辑信息', '## 基础信息')

    # 2. 将乐器字段改为"艺术家"
    for instrument in INSTRUMENT_FIELDS:
        # 匹配"- **乐器**:"格式
        pattern = rf'-\s*\*\*{re.escape(instrument)}\*\*:'
        if re.search(pattern, content):
            content = re.sub(pattern, f'- **艺术家**:', content)
            print(f"  替换字段：{instrument} -> 艺术家")
            break  # 只替换第一个找到的字段

    # 如果内容有变化，写回文件
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        return True
    else:
        print(f"  无需修改")
        return False


def main():
    base_dir = Path(__file__).parent.parent

    # 从失败记录中读取需要修复的专辑目录
    failed_albums = [
        "Leoš Janáček - Osud (Das Schicksal) in German Translation, Op. 58 (Supraphon 2CD)",
        "Lukas Geniušas - 16th International Chopin Piano Competition - Final Concert (Proniphon 2CD)",
        "Maria Gambaryan - Russian Piano School - Beethoven, Schumann, Schubert-Liszt (Talents of Russia)",
        "Mikhail Voskresensky - Alexander Scriabin: 24 Preludes, Op. 11; Sonata No. 3, Op. 23 (Northern Flowers)",
        "Russian Piano Music, Volume 1: Shostakovich - Preludes and Fugues Nos. 1, 4, 7, 24 (BIS)",
        "Nikita Magaloff - Last Recital in Tokyo 1991 (VICTOR 2CD)",
        "Anton Bruckner - Symphony No. 3 in D minor 'Wagner Symphonie' (1944 recording) (Urania)",
        "Giacomo Puccini - La Bohème (1955 Live Recording) (Cantus Classics 2CD)",
        "Richard Strauss - Der Rosenkavalier (1949 Recording) (Archipel 3CD)",
        "Richard Strauss - The Last Concerts 1947-1949 (Music & Arts 2CD)",
        "Chopin - Concertos pour piano / 肖邦 - 第一、二钢琴协奏曲 (EMI 2CD)",
        "Sviatoslav Richter in Budapest - The Concert of 9 February 1958 (Testament)",
        "Tchaikovsky - Eugene Onegin - Lemeshev, Krutikova, Dobrokhotova / Melik-Pashayev 1948 (Melodiya 2CD)",
        "Three Tenors of the Opéra-Comique - Louis Cazette, José Luccioni, César Vezzani (Marston 2CD)",
        "Sergey Taneyev - String Trio in E-flat minor; String Sextet in A minor (Northern Flowers)",
        "Rachmaninov Preludes Plus piano sonatas (BBCMM415)",
        "Tito Schipa - The Romance of Spain (Pearl)",
        "Leoš Janáček - Sinfonietta Op.60 / Violin Sonata 1. X. 1905 (Supraphon)",
        "Bedřich Smetana - Má Vlast (My Country) (Supraphon)",
    ]

    fixed_count = 0
    for album_name in failed_albums:
        album_dir = base_dir / album_name
        info_file = album_dir / "专辑基本信息.md"

        if info_file.exists():
            print(f"\n修复：{album_name}")
            if fix_album_info_file(info_file):
                fixed_count += 1
        else:
            print(f"\n跳过（无信息文件）：{album_name}")

    print(f"\n\n修复完成！共修复 {fixed_count}/{len(failed_albums)} 个专辑文件")


if __name__ == '__main__':
    main()
