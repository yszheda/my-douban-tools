#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""豆瓣标签 API 添加器 - 逐标签提交版"""

import requests
import time
from typing import List, Dict

class DoubanApiTagAdder:
    """豆瓣 API 标签添加器 - 逐标签提交"""

    def __init__(self, cookie_file: str = "cookie.txt"):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://music.douban.com/',
            'Origin': 'https://music.douban.com',
        })
        self.ck = ""
        self._load_cookie(cookie_file)

    def _load_cookie(self, cookie_file: str):
        """加载 cookie 获取 ck 值"""
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            cookies = {}
            for item in content.split(';'):
                if '=' in item:
                    k, v = item.strip().split('=', 1)
                    cookies[k] = v

            self.ck = cookies.get('ck', '')
            self.session.cookies.update(cookies)

            if not self.ck:
                raise ValueError("ck not found in cookie file")

            print(f"[API] Cookie 加载成功，ck={self.ck}")
        except Exception as e:
            raise RuntimeError(f"Cookie 加载失败：{e}")

    def add_tag(self, subject_id: str, tag: str) -> bool:
        """添加单个标签"""
        # 正确的豆瓣标签 API endpoint
        url = f'https://www.douban.com/j/subject/{subject_id}/tags'

        # POST 数据 - 豆瓣期望的格式
        data = {
            'ck': self.ck,
            'tags': tag  # 单个标签
        }

        # 必要的 headers
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        try:
            resp = self.session.post(url, data=data, headers=headers, timeout=10)

            print(f"       URL: {url}, ck: {self.ck}, 响应：{resp.status_code}")

            if resp.status_code == 200:
                try:
                    result = resp.json()
                    if result.get('r') == 0:
                        return True
                    else:
                        print(f"[API] 标签 '{tag}' 失败：{result}")
                        return False
                except:
                    # 非 JSON 响应
                    return True
            else:
                print(f"[API] 标签 '{tag}' HTTP {resp.status_code}")
                return False

        except Exception as e:
            print(f"[API] 标签 '{tag}' 错误：{e}")
            return False

    def add_tags(self, subject_id: str, tags: List[str], delay: float = 1.0) -> Dict:
        """批量添加标签"""
        result = {'success': [], 'failed': []}

        print(f"\n开始为专辑 {subject_id} 添加标签...")
        print(f"标签数量：{len(tags)}")
        print(f"标签列表：{' '.join(tags)}")
        print("=" * 50)

        for i, tag in enumerate(tags):
            print(f"[{i+1}/{len(tags)}] 处理：{tag}")

            if self.add_tag(subject_id, tag):
                result['success'].append(tag)
                print(f"     [OK] 成功")
            else:
                result['failed'].append(tag)
                print(f"     [X] 失败")

            if i < len(tags) - 1:
                time.sleep(delay)

        print("=" * 50)
        print(f"完成：成功 {len(result['success'])}/{len(tags)}, 失败 {len(result['failed'])}")

        return result


def main():
    """测试 API 版标签添加"""
    subject_id = "35617623"
    tags = [
        'Alkan', 'Cello', 'CelloPiano', 'Chamber', 'Chopin',
        'Classical', 'Mirare', 'Neuburger', 'Piano', 'Romantic'
    ]

    print("=" * 60)
    print("豆瓣 API 标签添加测试")
    print("=" * 60)

    adder = DoubanApiTagAdder()
    result = adder.add_tags(subject_id, tags, delay=1.5)

    print(f"\n结果:")
    print(f"  成功：{result['success']}")
    print(f"  失败：{result['failed']}")

    return result


if __name__ == '__main__':
    main()
