#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆瓣音乐自动化脚本
用于批量处理古典音乐专辑：搜索、标记已听、添加标签、创建新条目

使用前需要安装：
    pip install playwright
    playwright install

使用前需要配置：
    1. 豆瓣账号登录信息
    2. 豆瓣 Cookie（需要手动登录后获取）
"""

import json
import os
import re
import sys
import time
import hashlib
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Tuple
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout


@dataclass
class AlbumInfo:
    """专辑信息数据结构"""
    directory: str
    title: str
    artist: str
    label: str = ""
    catalog_number: str = ""
    year: str = ""
    composers: List[str] = None
    performers: List[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.composers is None:
            self.composers = []
        if self.performers is None:
            self.performers = []
        if self.tags is None:
            self.tags = []


class DoubanMusicBot:
    """豆瓣音乐自动化机器人"""

    BASE_URL = "https://music.douban.com"
    SEARCH_URL = f"{BASE_URL}/search"

    def __init__(self, cookie: str = None, headless: bool = False):
        self.cookie = cookie
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.logged_in = False
        self.results = []

    def start(self):
        """启动浏览器"""
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )

        # 使用真实的用户代理
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

        self.context = self.browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai'
        )

        # 添加反检测脚本 - 更全面的覆盖
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
            Object.defineProperty(navigator, 'connection', {get: () => ({effectiveType: '4g', rtt: 50, downlink: 10, saveData: false})});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});

            // 覆盖 permissions API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({state: 'default'}) :
                    originalQuery(parameters)
            );
        """)

        self.page = self.context.new_page()
        return self

    def load_cookie(self, cookie: str):
        """加载 Cookie"""
        if not cookie:
            return False

        try:
            # 解析 cookie 字符串
            cookies = []
            for item in cookie.split(';'):
                if '=' not in item:
                    continue
                key, value = item.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key in ['dbcl2', 'douban-fav-remind', 'gr', '_pk_id', '_pk_ses', 'ck']:
                    cookies.append({
                        'name': key,
                        'value': value,
                        'domain': '.douban.com',
                        'path': '/'
                    })

            if cookies:
                self.context.add_cookies(cookies)
                return True
        except Exception as e:
            print(f"加载 Cookie 失败：{e}")
        return False

    def check_login(self) -> bool:
        """检查登录状态"""
        try:
            # 使用更宽松的等待条件
            self.page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=60000)
            self.page.wait_for_timeout(5000)  # 等待 5 秒让页面加载

            # 检查页面标题
            title = self.page.title()
            print(f"页面标题：{title}")

            # 获取所有 Cookie
            cookies = self.context.cookies()
            dbcl2_cookies = [c for c in cookies if c['name'] == 'dbcl2']

            if dbcl2_cookies:
                print(f"[OK] dbcl2 Cookie 存在，已登录")
                return True

            # 备用检查：查看是否有用户相关元素
            # 检查是否有 nav-login（未登录时显示）
            nav_login = self.page.query_selector('a[name="nav-login"]')

            # 如果 dbcl2 存在且没有 nav-login，说明已登录
            if not nav_login:
                print("[OK] 未检测到 nav-login，可能已登录")
                return True

            print("[FAIL] 未检测到登录状态")
            return False
        except Exception as e:
            print(f"检查登录状态失败：{e}")
            # Cookie 存在就认为已登录
            try:
                cookies = self.context.cookies()
                dbcl2_cookies = [c for c in cookies if c['name'] == 'dbcl2']
                if dbcl2_cookies:
                    print("[OK] Cookie 存在，继续尝试")
                    return True
            except:
                pass
            return False

    def search_album(self, artist: str, title: str) -> Optional[dict]:
        """
        搜索专辑
        返回：找到的第一个匹配项的信息，或 None
        """
        # 构建搜索查询
        query = f"{artist} {title}".strip()

        try:
            # 访问搜索页面
            search_url = f"{self.SEARCH_URL}?query={query}&type=1"  # type=1 表示音乐
            print(f"  搜索：{query}")
            self.page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
            self.page.wait_for_timeout(5000)  # 等待页面加载

            # 获取页面 HTML 用于调试
            html = self.page.content()

            # 查找搜索结果 - 尝试多种选择器
            result_items = []
            selectors_to_try = [
                '.result-list .result',
                '#root .card',
                '.item',
                '.search-result',
                '[data-testid="search-result"]',
                'div[class*="result"]',
            ]

            for selector in selectors_to_try:
                result_items = self.page.query_selector_all(selector)
                if result_items:
                    print(f"  找到 {len(result_items)} 个结果 (使用选择器：{selector})")
                    break

            if not result_items:
                print(f"  未找到搜索结果（页面长度：{len(html)}）")
                # 检查是否有验证码
                if '验证码' in html or 'captcha' in html.lower():
                    print("  [警告] 可能触发了验证码！")

                # 保存调试信息
                with open('debug_search.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                self.page.screenshot(path='debug_search.png')
                print("  [调试] 已保存 debug_search.html 和 debug_search.png")

                # 尝试检查页面是否包含音乐条目
                # 豆瓣音乐的条目通常有 class="item" 或 class="music-item"
                music_items = self.page.query_selector_all('.music-item')
                if music_items:
                    print(f"  找到 {len(music_items)} 个音乐条目 (使用 .music-item)")
                    result_items = music_items

                # 尝试豆瓣新的结构
                general_items = self.page.query_selector_all('[class*="Item"]')
                if general_items and not result_items:
                    print(f"  找到 {len(general_items)} 个通用条目")
                    result_items = general_items

                if not result_items:
                    return None

            # 分析第一个结果
            first_result = result_items[0]

            # 提取信息
            try:
                title_el = first_result.query_selector('.title a')
                found_title = title_el.text_content().strip() if title_el else ""

                link = title_el.get_attribute('href') if title_el else ""

                # 提取艺术家
                artist_el = first_result.query_selector('.desc')
                found_artist = artist_el.text_content().strip() if artist_el else ""

                # 检查匹配度
                match_score = self._calculate_match_score(
                    title, artist, found_title, found_artist
                )

                if match_score < 0.3:
                    print(f"  匹配度较低 ({match_score:.2f})")
                    return None

                return {
                    'title': found_title,
                    'artist': found_artist,
                    'url': link if link.startswith('http') else f"{self.BASE_URL}{link}",
                    'match_score': match_score
                }

            except Exception as e:
                print(f"  提取搜索结果失败：{e}")
                return None

        except PlaywrightTimeout:
            print(f"  搜索超时")
            return None
        except Exception as e:
            print(f"  搜索失败：{e}")
            return None

    def _calculate_match_score(self, search_title, search_artist, found_title, found_artist) -> float:
        """计算匹配分数 (0-1)"""
        score = 0.0

        # 标题匹配
        search_title_lower = search_title.lower()
        found_title_lower = found_title.lower()

        if search_title_lower in found_title_lower or found_title_lower in search_title_lower:
            score += 0.5
        elif any(word in found_title_lower for word in search_title_lower.split() if len(word) > 2):
            score += 0.3

        # 艺术家匹配
        search_artist_lower = search_artist.lower()
        found_artist_lower = found_artist.lower()

        if search_artist_lower in found_artist_lower or found_artist_lower in search_artist_lower:
            score += 0.5
        elif any(word in found_artist_lower for word in search_artist_lower.split() if len(word) > 2):
            score += 0.3

        return min(score, 1.0)

    def mark_as_listened(self, album_url: str) -> bool:
        """标记为已听"""
        try:
            self.page.goto(album_url, wait_until='domcontentloaded', timeout=60000)
            self.page.wait_for_timeout(3000)

            # 查找"想听"、"在听"、"听过"按钮
            listen_button = None

            # 尝试多种选择器
            selectors = [
                'input[value="听过"]',
                'button:has-text("听过")',
                '.interest-btn:has-text("听过")',
                '[name="interest"]'
            ]

            for selector in selectors:
                try:
                    listen_button = self.page.query_selector(selector)
                    if listen_button:
                        break
                except:
                    continue

            if listen_button:
                # 检查是否已经标记为"听过"
                is_checked = listen_button.get_attribute('checked')
                if is_checked:
                    print("  已标记为'听过'")
                    return True

                listen_button.click()
                time.sleep(1)
                print("  已标记为'听过'")
                return True
            else:
                print("  未找到标记按钮")
                return False

        except Exception as e:
            print(f"  标记失败：{e}")
            return False

    def add_tags(self, album_url: str, tags: List[str]) -> bool:
        """添加标签"""
        if not tags:
            return True

        try:
            self.page.goto(album_url, wait_until='domcontentloaded', timeout=60000)
            self.page.wait_for_timeout(3000)

            # 查找标签输入区域
            tag_input = self.page.query_selector('#tags-section')
            if not tag_input:
                print("  未找到标签输入区域")
                return False

            # 获取现有标签
            existing_tags = set()
            tag_els = self.page.query_selector_all('.tag')
            for tag_el in tag_els:
                existing_tags.add(tag_el.text_content().strip().lower())

            # 添加新标签
            for tag in tags:
                tag_lower = tag.lower()
                if tag_lower in existing_tags:
                    continue

                # 查找标签输入框
                input_field = self.page.query_selector('.tag-input')
                if not input_field:
                    input_field = self.page.query_selector('#tags-input')

                if input_field:
                    input_field.fill(tag)
                    input_field.press('Enter')
                    time.sleep(0.5)
                    print(f"  添加标签：{tag}")
                    existing_tags.add(tag_lower)

            return True

        except Exception as e:
            print(f"  添加标签失败：{e}")
            return False

    def create_album_entry(self, album: AlbumInfo) -> Optional[str]:
        """
        创建新的专辑条目
        返回：新条目的 URL，或 None
        """
        print("  豆瓣音乐不支持用户直接创建音乐条目，需要管理员审核")
        print("  建议：手动提交至 https://music.douban.com/new_subject")
        return None

    def parse_album_file(self, directory: str) -> Optional[AlbumInfo]:
        """解析专辑信息文件"""
        file_path = Path(directory) / "专辑基本信息.md"

        if not file_path.exists():
            # 尝试其他可能的文件名
            for name in ["专辑信息.md", "info.md", "INFO.md", "metadata.md"]:
                alt_path = Path(directory) / name
                if alt_path.exists():
                    file_path = alt_path
                    break
            else:
                return None

        try:
            content = file_path.read_text(encoding='utf-8')

            album = AlbumInfo(
                directory=directory,
                title="",
                artist=""
            )

            # 解析标题
            title_match = re.search(r'##\s*专辑名称\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
            if title_match:
                album.title = title_match.group(1).strip()

            # 解析艺术家
            artist_match = re.search(r'##\s*艺术家\s*\n.*?\*\*(.+?)\*\*', content, re.DOTALL)
            if artist_match:
                album.artist = artist_match.group(1).strip()

            # 解析厂牌
            label_match = re.search(r'-\s*\*\*厂牌\*\*:\s*(.+?)\n', content)
            if label_match:
                album.label = label_match.group(1).strip()

            # 解析编号
            catalog_match = re.search(r'-\s*\*\*编号\*\*:\s*(.+?)\n', content)
            if catalog_match:
                album.catalog_number = catalog_match.group(1).strip()

            # 解析年份
            year_match = re.search(r'-\s*\*\*录音年份\*\*:\s*(.+?)\n', content)
            if year_match:
                album.year = year_match.group(1).strip()

            # 解析作曲家（从曲目列表中提取）
            composers = set()
            composer_matches = re.findall(r'\*\*(.+?)\s*\(\d{4}[-–]\d{4}\)\*\*', content)
            for composer in composer_matches:
                composers.add(composer.strip())
            album.composers = list(composers)

            # 生成标签
            if album.artist:
                album.tags.append(album.artist.split('(')[0].strip())
            if album.label:
                album.tags.append(album.label)
            if album.composers:
                for composer in album.composers[:3]:  # 最多 3 个作曲家
                    album.tags.append(composer)

            return album

        except Exception as e:
            print(f"  解析文件失败：{e}")
            return None

    def process_album(self, album: AlbumInfo, create_if_missing: bool = True) -> Dict:
        """
        处理单个专辑
        返回：处理结果
        """
        result = {
            'directory': album.directory,
            'title': album.title,
            'artist': album.artist,
            'status': 'unknown',
            'url': None,
            'message': ''
        }

        # 使用 ASCII 安全的方式打印
        title_ascii = album.title.encode('ascii', errors='replace').decode('ascii') if album.title else ''
        artist_ascii = album.artist.encode('ascii', errors='replace').decode('ascii') if album.artist else ''
        print(f"\n处理专辑：{title_ascii} - {artist_ascii}")

        # 搜索专辑
        search_result = self.search_album(album.artist, album.title)

        if search_result:
            print(f"  找到匹配：{search_result['title']}")
            print(f"  URL: {search_result['url']}")

            # 标记为已听
            if self.mark_as_listened(search_result['url']):
                result['status'] = 'marked'

            # 添加标签
            if album.tags:
                self.add_tags(search_result['url'], album.tags)

            result['url'] = search_result['url']
            result['message'] = f"已标记，匹配度：{search_result['match_score']:.2f}"

        else:
            print("  未找到匹配的专辑条目")
            result['status'] = 'not_found'
            result['message'] = '未在豆瓣找到对应条目'

            if create_if_missing:
                new_url = self.create_album_entry(album)
                if new_url:
                    result['status'] = 'created'
                    result['url'] = new_url
                    result['message'] = '已创建新条目'
                else:
                    result['message'] += ' - 需要手动创建'

        self.results.append(result)
        return result

    def process_directory(self, base_path: str, create_if_missing: bool = True):
        """处理整个目录"""
        base_path = Path(base_path)

        # 获取所有子目录
        directories = sorted([
            d for d in base_path.iterdir()
            if d.is_dir() and not d.name.startswith('.') and d.name != 'scripts'
        ])

        print(f"找到 {len(directories)} 个专辑目录")

        for i, directory in enumerate(directories, 1):
            # 使用 ASCII 安全的名称（替换非 ASCII 字符）
            safe_name = directory.name.encode('ascii', errors='replace').decode('ascii')
            print(f"\n{'='*60}")
            print(f"[{i}/{len(directories)}] {safe_name}")
            print(f"{'='*60}")

            # 解析专辑信息
            album = self.parse_album_file(str(directory))
            if not album:
                print(f"  跳过：未找到专辑信息文件")
                continue

            # 处理专辑
            self.process_album(album, create_if_missing)

            # 添加延迟，避免触发反爬虫
            time.sleep(3)

    def save_results(self, output_path: str):
        """保存处理结果"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存至：{output_path}")

    def print_summary(self):
        """打印处理摘要"""
        total = len(self.results)
        marked = sum(1 for r in self.results if r['status'] == 'marked')
        created = sum(1 for r in self.results if r['status'] == 'created')
        not_found = sum(1 for r in self.results if r['status'] == 'not_found')

        print(f"\n{'='*60}")
        print("处理摘要")
        print(f"{'='*60}")
        print(f"总计：{total} 个专辑")
        print(f"已标记：{marked}")
        print(f"已创建：{created}")
        print(f"未找到：{not_found}")

        if not_found > 0:
            print(f"\n未找到的专辑:")
            for r in self.results:
                if r['status'] == 'not_found':
                    print(f"  - {r['title']} - {r['artist']}")

    def close(self):
        """关闭浏览器"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()


def load_cookie_from_file(cookie_file: str) -> str:
    """从文件加载 Cookie"""
    cookie_path = Path(cookie_file)
    if cookie_path.exists():
        return cookie_path.read_text(encoding='utf-8').strip()
    return None


def main():
    import argparse

    parser = argparse.ArgumentParser(description='豆瓣音乐自动化脚本')
    parser.add_argument('--path', '-p', default='.', help='专辑目录路径')
    parser.add_argument('--cookie', '-c', help='豆瓣 Cookie 字符串')
    parser.add_argument('--cookie-file', help='Cookie 文件路径')
    parser.add_argument('--headless', action='store_true', help='无头模式运行')
    parser.add_argument('--no-create', action='store_true', help='不创建新条目')
    parser.add_argument('--output', '-o', default='douban_results.json', help='结果输出文件')
    parser.add_argument('--limit', '-l', type=int, help='限制处理的专辑数量')

    args = parser.parse_args()

    # 获取 Cookie
    cookie = args.cookie
    if not cookie and args.cookie_file:
        cookie = load_cookie_from_file(args.cookie_file)
    if not cookie:
        # 尝试默认 Cookie 文件
        default_cookie_file = Path(__file__).parent / 'douban_cookie.txt'
        if default_cookie_file.exists():
            cookie = load_cookie_from_file(str(default_cookie_file))

    if not cookie:
        print("="*60)
        print("错误：未提供豆瓣 Cookie")
        print("="*60)
        print("\n获取 Cookie 的方法：")
        print("1. 在浏览器中登录豆瓣音乐 (https://music.douban.com)")
        print("2. 打开开发者工具 (F12)")
        print("3. 找到 Application/存储 标签")
        print("4. 找到 Cookies -> https://music.douban.com")
        print("5. 复制以下 Cookie 的值：dbcl2, gr, ck, douban-fav-remind")
        print("6. 格式：dbcl2=xxx; gr=xxx; ck=xxx; douban-fav-remind=xxx")
        print("\n或者将 Cookie 保存到 douban_cookie.txt 文件中")
        sys.exit(1)

    # 创建机器人实例
    bot = DoubanMusicBot(cookie=cookie, headless=args.headless)

    try:
        bot.start()

        # 检查登录状态
        if not bot.check_login():
            print("="*60)
            print("错误：Cookie 无效或已过期，请重新获取")
            print("="*60)
            sys.exit(1)

        print("登录成功!")

        # 处理目录
        bot.process_directory(args.path, create_if_missing=not args.no_create)

        # 保存结果
        bot.save_results(args.output)

        # 打印摘要
        bot.print_summary()

    finally:
        bot.close()


if __name__ == '__main__':
    main()
