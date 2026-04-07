#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试豆瓣登录"""

import sys
from pathlib import Path

# 读取 Cookie
cookie_file = Path(__file__).parent / 'douban_cookie.txt'
if not cookie_file.exists():
    print("[FAIL] Cookie 文件不存在")
    sys.exit(1)

cookie = cookie_file.read_text(encoding='utf-8').strip()
print(f"Cookie 内容：{cookie}")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # 显示浏览器以便观察
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080}
    )

    # 添加 Cookie
    cookies = []
    for item in cookie.split(';'):
        if '=' not in item:
            continue
        key, value = item.split('=', 1)
        key = key.strip()
        value = value.strip()
        print(f"添加 Cookie: {key} = {value[:20]}...")
        cookies.append({
            'name': key,
            'value': value,
            'domain': '.douban.com',
            'path': '/'
        })

    if cookies:
        context.add_cookies(cookies)
        print(f"已添加 {len(cookies)} 个 Cookie")

    page = context.new_page()

    # 访问豆瓣音乐
    print("正在访问豆瓣音乐...")
    page.goto('https://music.douban.com', wait_until='domcontentloaded', timeout=60000)
    page.wait_for_timeout(5000)

    # 检查登录状态
    print(f"\n当前 URL: {page.url}")
    print(f"页面标题：{page.title()}")

    # 获取所有 Cookie
    current_cookies = context.cookies()
    print(f"\n当前 Cookie 列表:")
    for c in current_cookies:
        print(f"  {c['name']}: {c['value'][:30]}...")

    # 检查是否有 dbcl2
    dbcl2 = [c for c in current_cookies if c['name'] == 'dbcl2']
    if dbcl2:
        print(f"\n[OK] dbcl2 Cookie 存在：{dbcl2[0]['value'][:20]}...")
    else:
        print("\n[FAIL] dbcl2 Cookie 不存在")

    # 截图
    page.screenshot(path='debug_douban.png')
    print("\n已保存截图：debug_douban.png")

    input("\n按回车键关闭浏览器...")
    browser.close()
