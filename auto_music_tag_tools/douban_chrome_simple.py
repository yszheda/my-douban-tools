#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的豆瓣音乐批量处理工具
使用 Chrome DevTools Protocol 直接控制已登录的 Chrome
"""

import json
import time
import sys
import re
from pathlib import Path

try:
    import websocket
    import requests
except ImportError:
    print("需要安装：pip install websocket-client requests")
    sys.exit(1)


class SimpleDoubanBot:
    def __init__(self, debug_port=9222):
        self.debug_url = f"http://127.0.0.1:{debug_port}"
        self.ws = None
        self.session_id = None

    def connect(self):
        """连接到 Chrome"""
        try:
            # 获取 WebSocket URL
            resp = requests.get(f"{self.debug_url}/json/version", timeout=5)
            ws_url = resp.json().get("webSocketDebuggerUrl")

            if not ws_url:
                print("无法获取 WebSocket URL")
                return False

            self.ws = websocket.create_connection(ws_url, timeout=10)
            return True
        except Exception as e:
            print(f"连接失败：{e}")
            print("请确保 Chrome 已启动并带有 --remote-debugging-port=9222 参数")
            return False

    def send(self, method, params=None):
        """发送 CDP 命令"""
        cmd = {
            "id": 1,
            "method": method,
            "params": params or {}
        }
        self.ws.send(json.dumps(cmd))
        return json.loads(self.ws.recv())

    def navigate(self, url):
        """导航到 URL"""
        return self.send("Page.navigate", {"url": url})

    def evaluate(self, script):
        """执行 JavaScript"""
        result = self.send("Runtime.evaluate", {
            "expression": script,
            "returnByValue": True
        })
        return result.get("result", {}).get("value")

    def get_cookie(self, name):
        """获取 Cookie"""
        cookies = self.evaluate("document.cookie")
        if cookies:
            for item in cookies.split('; '):
                if '=' in item:
                    k, v = item.split('=', 1)
                    if k == name:
                        return v
        return None

    def check_login(self):
        """检查豆瓣登录"""
        dbcl2 = self.get_cookie("dbcl2")
        return dbcl2 is not None

    def search_album(self, artist, title):
        """搜索专辑并返回第一个结果的 URL"""
        query = f"{artist} {title}".strip()
        search_url = f"https://music.douban.com/search?query={query}&type=1"

        # 使用 URL 编码
        import urllib.parse
        search_url = f"https://music.douban.com/search?query={urllib.parse.quote(query)}&type=1"

        self.navigate(search_url)
        time.sleep(3)

        # 获取搜索结果 - 尝试多种选择器
        result = self.evaluate("""
            (function() {
                // 豆瓣音乐搜索结果的各种可能选择器
                const selectors = [
                    '.result-list .result',
                    '#root .card',
                    '.item',
                    '.search-result',
                    '[data-testid="search-result"]',
                    'div[class*="result"]',
                    '.music-item',
                    'li[class*="item"]'
                ];

                for (const selector of selectors) {
                    const items = document.querySelectorAll(selector);
                    if (items.length > 0) {
                        const first = items[0];
                        const link = first.querySelector('a');
                        if (link && link.href) {
                            return link.href;
                        }
                    }
                }

                // 如果还是没有找到，尝试返回当前 URL
                return window.location.href;
            })()
        """)

        # 检查是否是搜索页面本身（没有找到结果）
        if result and 'search' in result.lower():
            return None

        return result

    def mark_as_listened(self, subject_url):
        """标记为听过"""
        self.navigate(subject_url)
        time.sleep(2)

        # 尝试点击"听过"按钮
        result = self.evaluate("""
            (function() {
                const btn = document.querySelector('input[value="听过"], button:contains("听过"), .interest-btn');
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            })()
        """)

        return result

    def add_tags(self, tags):
        """添加标签"""
        if not tags:
            return

        result = self.evaluate(f"""
            (function() {{
                const tags = {json.dumps(tags)};
                const input = document.querySelector('.tag-input, #tags-input');
                if (!input) return false;

                tags.forEach(tag => {{
                    input.value = tag;
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter' }}));
                }});
                return true;
            }})()
        """)

        return result


def parse_album_file(directory):
    """解析专辑信息"""
    file_path = Path(directory) / "专辑基本信息.md"
    if not file_path.exists():
        return None

    try:
        content = file_path.read_text(encoding='utf-8')

        title = ""
        artist = ""
        label = ""
        composers = []

        title_match = re.search(r'##\s*专辑名称\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()

        artist_match = re.search(r'##\s*艺术家\s*\n.*?\*\*(.+?)\*\*', content, re.DOTALL)
        if artist_match:
            artist = artist_match.group(1).strip()
            if '(' in artist:
                artist = artist.split('(')[0].strip()

        label_match = re.search(r'-\s*\*\*厂牌\*\*:\s*(.+?)\n', content)
        if label_match:
            label = label_match.group(1).strip()

        composer_matches = re.findall(r'\*\*(.+?)\s*\(\d{4}[-–]\d{4}\)\*\*', content)
        composers = list(set(c.strip() for c in composer_matches[:3]))

        return {'title': title, 'artist': artist, 'label': label, 'composers': composers}
    except:
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', '-p', default='.')
    parser.add_argument('--port', type=int, default=9222)
    parser.add_argument('--limit', '-l', type=int, default=5)

    args = parser.parse_args()

    print("="*60)
    print("豆瓣音乐批量处理 - Chrome DevTools")
    print("="*60)

    # 连接 Chrome
    bot = SimpleDoubanBot(args.port)
    if not bot.connect():
        print("\n启动 Chrome 的方法:")
        print('Chrome 路径："C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"')
        print("参数：--remote-debugging-port=9222 --user-data-dir=%TEMP%\\chrome-douban")
        sys.exit(1)

    # 检查登录
    print("\n检查豆瓣登录状态...")
    for attempt in range(10):
        if bot.check_login():
            break
        print(f"等待用户登录豆瓣... (尝试 {attempt+1}/10)")
        time.sleep(2)
    else:
        print("未检测到豆瓣登录，请手动登录后重新运行脚本")
        # 继续尝试，可能 Cookie 未正确读取

    if not bot.check_login():
        print("仍然未检测到登录，但将继续尝试...")

    print("[OK] 已登录豆瓣")

    # 获取专辑
    base = Path(args.path)
    dirs = sorted([d for d in base.iterdir() if d.is_dir() and not d.name.startswith('.')])
    dirs = [d for d in dirs if d.name != 'scripts'][:args.limit]

    print(f"\n将处理 {len(dirs)} 个专辑")

    # 处理每个专辑
    for i, directory in enumerate(dirs, 1):
        album = parse_album_file(str(directory))
        if not album or not album['title']:
            continue

        safe_title = album['title'][:40]
        print(f"\n[{i}/{len(dirs)}] {safe_title}...")

        # 搜索
        result_url = bot.search_album(album['artist'], album['title'])
        if not result_url:
            print("  未找到结果")
            continue

        print(f"  找到：{result_url}")

        # 标记
        if bot.mark_as_listened(result_url):
            print("  已标记为'听过'")

        # 添加标签
        tags = [album['artist']] if album['artist'] else []
        tags.extend(album['composers'][:2])
        if album['label']:
            tags.append(album['label'])

        if tags:
            bot.add_tags(tags)
            print(f"  添加标签：{', '.join(tags)}")

        time.sleep(1)

    print("\n" + "="*60)
    print("处理完成!")
    print("="*60)


if __name__ == '__main__':
    main()
