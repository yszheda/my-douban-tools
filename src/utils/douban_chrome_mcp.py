#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 Chrome DevTools MCP 控制已登录的 Chrome 浏览器
访问豆瓣音乐并批量处理专辑

前提条件:
1. Chrome 浏览器已安装
2. 已在 Chrome 中登录豆瓣音乐
3. Chrome 已启动并开启远程调试端口
"""

import json
import time
import sys
from pathlib import Path
import re

try:
    import requests
except ImportError:
    print("需要安装 requests: pip install requests")
    sys.exit(1)


class DoubanChromeBot:
    """使用 Chrome DevTools Protocol 的豆瓣音乐机器人"""

    def __init__(self, debug_port: int = 9222):
        self.debug_url = f"http://127.0.0.1:{debug_port}"
        self.ws_url = None
        self.session = requests.Session()

    def get_browser_ws_url(self) -> str:
        """获取浏览器 WebSocket URL"""
        try:
            resp = self.session.get(f"{self.debug_url}/json/version", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get("webSocketDebuggerUrl")
        except Exception as e:
            print(f"获取 WebSocket URL 失败：{e}")
            return None

    def get_pages(self) -> list:
        """获取所有页面"""
        try:
            resp = self.session.get(f"{self.debug_url}/json/list", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"获取页面列表失败：{e}")
            return []

    def find_douban_page(self) -> dict:
        """查找豆瓣音乐页面"""
        pages = self.get_pages()
        for page in pages:
            if page.get("type") == "page" and "douban.com" in page.get("url", ""):
                return page
        return None

    def execute_script(self, target_id: str, script: str) -> dict:
        """执行 JavaScript"""
        ws_url = self.get_browser_ws_url()
        if not ws_url:
            return None

        import websocket
        ws = websocket.create_connection(ws_url, timeout=10)

        # 创建 target
        ws.send(json.dumps({
            "id": 1,
            "method": "Target.attachToTarget",
            "params": {"targetId": target_id}
        }))
        resp = json.loads(ws.recv())
        session_id = resp.get("result", {}).get("sessionId")

        # 执行脚本
        ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {
                "expression": script,
                "returnByValue": True
            },
            "sessionId": session_id
        }))
        resp = json.loads(ws.recv())

        ws.close()
        return resp

    def check_douban_login(self) -> bool:
        """检查豆瓣登录状态"""
        pages = self.get_pages()
        douban_page = self.find_douban_page()

        if not douban_page:
            # 没有豆瓣页面，创建一个
            self.execute_script("", "window.open('https://music.douban.com')")
            time.sleep(3)

        douban_page = self.find_douban_page()
        if not douban_page:
            return False

        # 检查 Cookie
        target_id = douban_page.get("id")
        result = self.execute_script(target_id, "document.cookie")

        if result:
            cookie = result.get("result", {}).get("value", "")
            has_dbcl2 = "dbcl2" in cookie
            print(f"豆瓣 Cookie: {'已登录' if has_dbcl2 else '未登录'}")
            return has_dbcl2

        return False


def start_chrome_with_debug():
    """启动 Chrome 并开启远程调试"""
    import subprocess

    # Windows Chrome 路径
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
    ]

    chrome_exe = None
    for path in chrome_paths:
        expanded = Path(path.replace("%LOCALAPPDATA%", str(Path.home() / "AppData/Local")))
        if expanded.exists():
            chrome_exe = str(expanded)
            break

    if not chrome_exe:
        print("未找到 Chrome，请手动启动 Chrome 并带上 --remote-debugging-port=9222 参数")
        return False

    # 检查是否已有 Chrome 进程在运行
    import psutil
    for proc in psutil.process_iter(['cmdline']):
        try:
            cmdline = proc.info.get('cmdline') or []
            if 'chrome' in ' '.join(cmdline).lower() and '--remote-debugging-port' in ' '.join(cmdline):
                print("检测到已在运行的 Chrome (带调试端口)")
                return True
        except:
            pass

    # 启动 Chrome
    user_data_dir = Path.home() / ".cache/chrome-douban-profile"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        chrome_exe,
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        "https://music.douban.com"
    ]

    print(f"启动 Chrome: {cmd}")
    subprocess.Popen(cmd)
    time.sleep(3)
    return True


def parse_album_file(directory: str) -> dict:
    """解析专辑信息文件"""
    file_path = Path(directory) / "专辑基本信息.md"

    if not file_path.exists():
        return None

    try:
        content = file_path.read_text(encoding='utf-8')

        title = ""
        artist = ""
        label = ""
        composers = []

        # 解析标题
        title_match = re.search(r'##\s*专辑名称\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()

        # 解析艺术家
        artist_match = re.search(r'##\s*艺术家\s*\n.*?\*\*(.+?)\*\*', content, re.DOTALL)
        if artist_match:
            artist = artist_match.group(1).strip()
            if '(' in artist:
                artist = artist.split('(')[0].strip()

        # 解析厂牌
        label_match = re.search(r'-\s*\*\*厂牌\*\*:\s*(.+?)\n', content)
        if label_match:
            label = label_match.group(1).strip()

        # 解析作曲家
        composer_matches = re.findall(r'\*\*(.+?)\s*\(\d{4}[-–]\d{4}\)\*\*', content)
        composers = list(set(c.strip() for c in composer_matches[:5]))

        return {
            'directory': directory,
            'title': title,
            'artist': artist,
            'label': label,
            'composers': composers
        }

    except Exception as e:
        print(f"  解析失败：{e}")
        return None


def generate_search_url(artist: str, title: str) -> str:
    """生成豆瓣搜索 URL"""
    query = f"{artist} {title}".strip()
    return f"https://music.douban.com/search?query={query}&type=1"


def main():
    import argparse

    parser = argparse.ArgumentParser(description='豆瓣音乐批量处理 (Chrome DevTools)')
    parser.add_argument('--path', '-p', default='.', help='专辑目录路径')
    parser.add_argument('--port', type=int, default=9222, help='Chrome 调试端口')
    parser.add_argument('--limit', '-l', type=int, help='限制处理数量')
    parser.add_argument('--start-chrome', action='store_true', help='自动启动 Chrome')

    args = parser.parse_args()

    print("="*60)
    print("豆瓣音乐批量处理 - Chrome DevTools 模式")
    print("="*60)

    # 启动 Chrome
    if args.start_chrome:
        print("\n正在启动 Chrome...")
        if not start_chrome_with_debug():
            print("启动 Chrome 失败，请手动启动")
            sys.exit(1)

    # 等待用户确认登录
    print("\n请确保:")
    print("1. Chrome 已启动并带 --remote-debugging-port=9222 参数")
    print("2. 已在浏览器中登录豆瓣音乐 (https://music.douban.com)")
    print()

    bot = DoubanChromeBot(debug_port=args.port)

    # 检查登录状态
    print("检查豆瓣登录状态...")
    for _ in range(5):
        if bot.check_douban_login():
            print("[OK] 已登录豆瓣音乐")
            break
        print("等待用户登录豆瓣...")
        time.sleep(2)
    else:
        print("[FAIL] 未检测到豆瓣登录")
        print("请在打开的 Chrome 中访问 https://music.douban.com 并登录")
        sys.exit(1)

    # 获取专辑列表
    base_path = Path(args.path)
    directories = sorted([
        d for d in base_path.iterdir()
        if d.is_dir() and not d.name.startswith('.') and d.name != 'scripts'
    ])

    if args.limit:
        directories = directories[:args.limit]

    print(f"\n找到 {len(directories)} 个专辑目录")

    # 生成搜索链接列表
    print("\n生成搜索链接...")
    for i, directory in enumerate(directories, 1):
        album = parse_album_file(str(directory))
        if not album:
            continue

        search_url = generate_search_url(album['artist'], album['title'])
        print(f"[{i}/{len(directories)}] {album['title'][:50]}... -> {search_url}")

    print("\n" + "="*60)
    print("下一步操作:")
    print("1. 在 Chrome 中批量打开搜索链接")
    print("2. 手动标记'听过'并添加标签")
    print("="*60)


if __name__ == '__main__':
    main()
