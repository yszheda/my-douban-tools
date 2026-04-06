#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新处理失败专辑 - 修复艺术家字段后重新提交到豆瓣
"""

import json
import time
import sys
import re
import urllib.parse
import random
from pathlib import Path

# 强制使用 UTF-8 编码输出
sys.stdout.reconfigure(encoding='utf-8')

try:
    import websocket
    import requests
except ImportError:
    print("需要安装：pip install websocket-client requests")
    sys.exit(1)


# 随机延迟配置
MIN_DELAY = 2.0
MAX_DELAY = 5.0
SEARCH_DELAY = 8.0
MARK_DELAY = 5.0


def random_delay(min_sec=MIN_DELAY, max_sec=MAX_DELAY):
    """随机延迟"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


# 失败的专辑目录列表（从失败记录中提取）
FAILED_ALBUMS = [
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


def parse_album_file(file_path):
    """解析专辑信息文件"""
    album = {}
    if not Path(file_path).exists():
        return album

    content = Path(file_path).read_text(encoding='utf-8')

    # 提取专辑名称
    match = re.search(r'\*\*专辑名称\*\*:\s*(.+)', content)
    if match:
        album['title'] = match.group(1).strip()

    # 提取艺术家
    match = re.search(r'\*\*艺术家\*\*:\s*(.+)', content)
    if match:
        album['artist'] = match.group(1).strip()

    # 提取作曲家
    match = re.search(r'\*\*作曲家\*\*:\s*(.+)', content)
    if match:
        album['composer'] = match.group(1).strip()

    # 提取厂牌
    match = re.search(r'\*\*厂牌\*\*:\s*(.+)', content)
    if match:
        album['label'] = match.group(1).strip()

    # 提取条形码
    match = re.search(r'\*\*条形码\*\*:\s*(.+)', content)
    if match:
        album['barcode'] = match.group(1).strip()

    return album


def main():
    base_dir = Path(__file__).parent.parent

    print("=" * 60)
    print("重新处理失败专辑 - 修复艺术家字段后")
    print("=" * 60)

    # 检查哪些失败专辑现在已经修复了艺术家字段
    fixed_albums = []
    for album_name in FAILED_ALBUMS:
        album_dir = base_dir / album_name
        info_file = album_dir / "专辑基本信息.md"

        if info_file.exists():
            album = parse_album_file(info_file)
            if album.get('artist'):
                fixed_albums.append(album_name)
                print(f"已修复：{album_name}")
            else:
                print(f"仍缺少艺术家字段：{album_name}")
        else:
            print(f"未找到信息文件：{album_name}")

    print(f"\n已修复的专辑数：{len(fixed_albums)}/{len(FAILED_ALBUMS)}")
    print("\n提示：现在可以运行 douban_chrome_v2.py 重新处理这些专辑")


if __name__ == '__main__':
    main()
