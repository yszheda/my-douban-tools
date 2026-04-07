#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣收藏列表抓取器

从豆瓣音乐用户主页抓取已听、在听、想听的专辑列表。
支持多页遍历，导出到 JSON 文件。
"""

import requests
import json
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from bs4 import BeautifulSoup

from .config import USER_AGENT, DEFAULT_COOKIE_FILE


@dataclass
class AlbumEntry:
    """专辑条目数据类"""
    subject_id: str
    title: str = ""
    artists: str = ""
    rating: str = ""
    comment: str = ""
    tags: List[str] = None
    status: str = "pending"  # pending, done, failed
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


class DoubanCollector:
    """豆瓣收藏列表抓取器"""

    def __init__(self, user_id: str = "63343218", cookie_file: str = DEFAULT_COOKIE_FILE):
        self.user_id = user_id
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
        })
        self._load_cookie(cookie_file)

        # 收藏类型
        self.collection_types = ['collect', 'do', 'wish']
        self.items_per_page = 30  # 豆瓣每页显示数量

    def _load_cookie(self, cookie_file: str):
        """加载豆瓣 cookie"""
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            cookies = {}
            for item in content.split(';'):
                if '=' in item:
                    k, v = item.strip().split('=', 1)
                    cookies[k] = v

            self.session.cookies.update(cookies)
            print(f"[INFO] Cookie 加载成功")
        except Exception as e:
            print(f"[WARN] Cookie 加载失败：{e}")
            print(f"[INFO] 将尝试无认证方式访问")

    def _get_collection_url(self, collection_type: str, start: int = 0) -> str:
        """生成收藏页面 URL"""
        # 使用 list 模式以便解析
        return f"https://music.douban.com/people/{self.user_id}/{collection_type}?start={start}&mode=list"

    def _parse_collection_page(self, html: str, mode: str = "list") -> tuple:
        """解析收藏页面 HTML，提取专辑信息

        Returns:
            (entries, has_next): entries 是专辑列表，has_next 表示是否有下一页
        """
        entries = []
        soup = BeautifulSoup(html, 'html.parser')

        # 检查是否有"后页"链接
        has_next = False
        next_link = soup.find('a', text=lambda x: x and '后页' in x)
        if next_link:
            has_next = True

        if mode == "list":
            # List 模式：查找所有 link 元素，href 包含 /subject/
            # 过滤掉包含 /people/ 的链接（用户主页链接）
            links = soup.find_all('a', href=lambda x: x and '/subject/' in x)

            seen_ids = set()
            for link in links:
                try:
                    href = link.get('href', '')
                    # 跳过包含 /people/ 的链接（用户主页）
                    if '/people/' in href:
                        continue

                    subject_id = href.split('/subject/')[-1].strip('/')

                    # 去重
                    if subject_id in seen_ids:
                        continue
                    seen_ids.add(subject_id)

                    title = link.get('title', '') or link.get_text(strip=True)

                    entry = AlbumEntry(
                        subject_id=subject_id,
                        title=title
                    )
                    entries.append(entry)

                except Exception as e:
                    print(f"[WARN] 解析条目失败：{e}")
                    continue
        else:
            # Grid/Table 模式：查找 table 元素
            tables = soup.find_all('table', width='100%')

            for table in tables:
                try:
                    img_link = table.find('a', href=lambda x: x and '/subject/' in x)
                    if not img_link:
                        continue

                    href = img_link.get('href', '')
                    subject_id = href.split('/subject/')[-1].strip('/')

                    title_elem = table.find('a', href=lambda x: x and '/subject/' in x)
                    title = title_elem.get('title', '') if title_elem else ''

                    artists_elem = table.find('span', class_='attrs')
                    artists = artists_elem.get_text(strip=True) if artists_elem else ''
                    if artists.startswith('艺术家：'):
                        artists = artists.replace('艺术家：', '').strip()

                    rating_elem = table.find('span', class_='rating')
                    rating = rating_elem.get('title', '') if rating_elem else ''

                    comment_elem = table.find('span', class_='comment')
                    comment = comment_elem.get_text(strip=True) if comment_elem else ''

                    tags_elem = table.find('div', class_='tags')
                    tags = []
                    if tags_elem:
                        tag_links = tags_elem.find_all('a')
                        tags = [tag.get_text(strip=True) for tag in tag_links]

                    entry = AlbumEntry(
                        subject_id=subject_id,
                        title=title,
                        artists=artists,
                        rating=rating,
                        comment=comment,
                        tags=tags
                    )
                    entries.append(entry)

                except Exception as e:
                    print(f"[WARN] 解析条目失败：{e}")
                    continue

        return entries, has_next

    def fetch_collection(self, collection_type: str, max_pages: int = None, delay: float = 2.0) -> List[AlbumEntry]:
        """
        抓取单个类型的收藏列表

        Args:
            collection_type: 'collect', 'do', 或 'wish'
            max_pages: 最大页数，None 表示抓取全部
            delay: 页面间延迟（秒）

        Returns:
            AlbumEntry 列表
        """
        all_entries = []
        start = 0
        page = 1

        print(f"\n[INFO] 开始抓取 {collection_type} 列表...")

        while True:
            url = self._get_collection_url(collection_type, start)
            print(f"[INFO] 第 {page} 页：{url}")

            try:
                resp = self.session.get(url, timeout=10)

                if resp.status_code == 403:
                    print(f"[ERROR] 访问被拒绝 (403)，可能需要更新 cookie")
                    break

                if resp.status_code != 200:
                    print(f"[ERROR] HTTP {resp.status_code}")
                    break

                html = resp.text
                entries, has_next = self._parse_collection_page(html)

                if not entries:
                    print(f"[INFO] 没有更多条目")
                    break

                all_entries.extend(entries)
                print(f"       抓取到 {len(entries)} 个条目，累计 {len(all_entries)} 个")

                # 如果没有下一页，停止
                if not has_next:
                    print(f"[INFO] 已达列表末尾")
                    break

                # 检查是否达到最大页数
                if max_pages and page >= max_pages:
                    print(f"[INFO] 已达最大页数 {max_pages}")
                    break

                # 延迟后继续下一页
                time.sleep(delay)
                start += self.items_per_page
                page += 1

            except requests.exceptions.RequestException as e:
                print(f"[ERROR] 请求失败：{e}")
                break
            except Exception as e:
                print(f"[ERROR] 未知错误：{e}")
                break

        print(f"[INFO] {collection_type} 抓取完成：共 {len(all_entries)} 个条目")
        return all_entries

    def fetch_all(self, max_pages_per_type: int = None, delay: float = 2.0) -> Dict[str, List[AlbumEntry]]:
        """
        抓取所有类型的收藏列表

        Args:
            max_pages_per_type: 每种类型的最大页数
            delay: 页面间延迟

        Returns:
            字典：{'collect': [...], 'do': [...], 'wish': [...]}
        """
        results = {}

        for collection_type in self.collection_types:
            entries = self.fetch_collection(collection_type, max_pages_per_type, delay)
            results[collection_type] = entries

        return results

    def save_to_file(self, results: Dict[str, List[AlbumEntry]], output_file: str = "album_list.json"):
        """保存结果到 JSON 文件"""
        output = {
            'exported_at': datetime.now().isoformat(),
            'user_id': self.user_id,
            'stats': {
                k: len(v) for k, v in results.items()
            },
            'collections': {}
        }

        for collection_type, entries in results.items():
            output['collections'][collection_type] = [asdict(entry) for entry in entries]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n[INFO] 结果已保存到：{output_file}")
        return output_file

    def load_from_file(self, input_file: str = "album_list.json") -> Dict[str, List[AlbumEntry]]:
        """从 JSON 文件加载收藏列表"""
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        results = {}
        for collection_type in self.collection_types:
            if collection_type in data.get('collections', {}):
                entries = []
                for entry_data in data['collections'][collection_type]:
                    entry = AlbumEntry(**entry_data)
                    entries.append(entry)
                results[collection_type] = entries
            else:
                results[collection_type] = []

        return results


def main():
    """主函数：导出收藏列表"""
    collector = DoubanCollector(user_id="63343218")

    # 抓取所有收藏
    results = collector.fetch_all(max_pages_per_type=None, delay=2.0)

    # 打印统计
    print("\n" + "=" * 60)
    print("收藏列表统计")
    print("=" * 60)
    for collection_type, entries in results.items():
        print(f"  {collection_type}: {len(entries)} 个条目")

    # 保存到文件
    collector.save_to_file(results, "album_list.json")

    return results


if __name__ == '__main__':
    main()
