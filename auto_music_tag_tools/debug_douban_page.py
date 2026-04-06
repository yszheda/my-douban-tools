#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban page structure
"""

import json
import time
import sys
import urllib.parse

try:
    import websocket
    import requests
except ImportError:
    print("需要安装：pip install websocket-client requests")
    sys.exit(1)


class DebugBot:
    def __init__(self, debug_port=9222):
        self.debug_url = f"http://127.0.0.1:{debug_port}"
        self.ws = None
        self.page_ws = None
        self.page_id = None

    def connect(self):
        try:
            resp = requests.get(f"{self.debug_url}/json/version", timeout=5)
            browser_ws = resp.json().get("webSocketDebuggerUrl")
            if not browser_ws:
                print("无法获取浏览器 WebSocket URL")
                return False
            self.ws = websocket.create_connection(browser_ws, timeout=10)
            return True
        except Exception as e:
            print(f"连接失败：{e}")
            return False

    def find_douban_page(self):
        try:
            pages = requests.get(f"{self.debug_url}/json/list", timeout=5).json()
            print(f"找到 {len(pages)} 个页面:")
            for page in pages[:5]:
                print(f"  - {page.get('title', '')[:50]}... {page.get('url', '')[:50]}")

            for page in pages:
                if 'douban.com' in page.get('url', ''):
                    self.page_id = page.get('id')
                    page_ws_url = page.get('webSocketDebuggerUrl')
                    if page_ws_url:
                        self.page_ws = websocket.create_connection(page_ws_url, timeout=10)
                        print(f"\n已连接到豆瓣页面：{page.get('url')}")
                        return True
            return False
        except Exception as e:
            print(f"查找页面失败：{e}")
            return False

    def evaluate(self, script):
        if not self.page_ws:
            return None
        try:
            self.page_ws.send(json.dumps({
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": script,
                    "returnByValue": True
                }
            }))
            resp = json.loads(self.page_ws.recv())
            return resp.get("result", {}).get("value")
        except Exception as e:
            print(f"执行脚本失败：{e}")
            return None

    def navigate(self, url):
        if not self.page_ws:
            return
        self.page_ws.send(json.dumps({
            "id": 2,
            "method": "Page.navigate",
            "params": {"url": url}
        }))
        self.page_ws.recv()

    def wait_load(self, seconds=3):
        time.sleep(seconds)


def main():
    print("="*60)
    print("Debug Douban Page Structure")
    print("="*60)

    bot = DebugBot(9222)
    if not bot.connect():
        print("连接 Chrome 失败")
        sys.exit(1)

    if not bot.find_douban_page():
        print("未找到豆瓣页面")
        sys.exit(1)

    # 检查当前页面状态
    print("\n[1] 检查当前页面信息:")
    page_info = bot.evaluate("({url: location.href, title: document.title, cookie: document.cookie.length})")
    if page_info:
        print(f"  URL: {page_info.get('url', '')[:80]}")
        print(f"  Title: {page_info.get('title', '')[:80]}")
        print(f"  Cookie length: {page_info.get('cookie', 0)}")

    # 检查搜索框
    print("\n[2] 检查搜索框:")
    search_inputs = bot.evaluate("""
        (function() {
            const inputs = document.querySelectorAll('input[type="text"], input[type="search"], input[name="q"]');
            const results = [];
            for (const input of inputs) {
                results.push({
                    type: input.type,
                    name: input.name,
                    placeholder: input.placeholder,
                    className: input.className,
                    id: input.id,
                    visible: input.offsetParent !== null
                });
            }
            return results;
        })()
    """)
    if search_inputs:
        for inp in search_inputs[:5]:
            print(f"  - {inp}")
    else:
        print("  未找到搜索输入框")

    # 检查页面所有类名
    print("\n[3] 页面主要元素类名:")
    classes = bot.evaluate("""
        (function() {
            const allClasses = new Set();
            document.querySelectorAll('*').forEach(el => {
                for (const cls of el.classList) {
                    allClasses.add(cls);
                }
            });
            return Array.from(allClasses).sort().slice(0, 100);
        })()
    """)
    if classes:
        print(f"  找到 {len(classes)} 个类名，前 50 个:")
        for cls in classes[:50]:
            print(f"    .{cls}")

    # 尝试执行搜索
    print("\n[4] 尝试执行搜索 'test album':")
    test_query = "test album"

    # 方法 1: 找到搜索框并输入
    search_result = bot.evaluate(f"""
        (function() {{
            const searchInput = document.querySelector('input[name="q"], input[type="search"]');
            if (searchInput) {{
                searchInput.value = "{test_query}";
                searchInput.dispatchEvent(new Event('input', {{ bubbles: true }}));

                const form = searchInput.closest('form');
                if (form) {{
                    form.submit();
                    return 'submitted_via_form';
                }}

                const enterEvent = new KeyboardEvent('keydown', {{
                    key: 'Enter',
                    bubbles: true
                }});
                searchInput.dispatchEvent(enterEvent);
                return 'submitted_via_enter';
            }}
            return 'no_search_input';
        }})()
    """)
    print(f"  搜索结果：{search_result}")

    bot.wait_load(5)

    # 检查搜索结果
    print("\n[5] 检查搜索后的页面:")
    result_info = bot.evaluate("({url: location.href, title: document.title})")
    if result_info:
        print(f"  URL: {result_info.get('url', '')[:80]}")
        print(f"  Title: {result_info.get('title', '')[:80]}")

    # 查找结果项
    print("\n[6] 查找结果项:")
    result_items = bot.evaluate("""
        (function() {
            const selectors = [
                '.result-list .result',
                '.result-list li',
                '.card-wrap',
                '.music-item',
                'article[data-id]',
                'a[href*="/subject/"]'
            ];
            const results = [];
            for (const sel of selectors) {
                const items = document.querySelectorAll(sel);
                if (items.length > 0) {
                    results.push({
                        selector: sel,
                        count: items.length,
                        firstHref: items[0].href || (items[0].querySelector && items[0].querySelector('a')?.href)
                    });
                }
            }
            return results;
        })()
    """)
    if result_items:
        for item in result_items:
            print(f"  - {item}")
    else:
        print("  未找到结果项")

    print("\n" + "="*60)
    print("Debug 完成")
    print("="*60)


if __name__ == '__main__':
    main()
