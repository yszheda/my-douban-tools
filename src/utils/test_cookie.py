#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 Cookie 是否有效"""

import sys
from pathlib import Path

# 读取 Cookie
cookie_file = Path(__file__).parent / 'douban_cookie.txt'
if not cookie_file.exists():
    print("❌ Cookie 文件不存在")
    sys.exit(1)

cookie = cookie_file.read_text(encoding='utf-8').strip()
print(f"Cookie 内容：{cookie}")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()

    # 添加 Cookie
    cookies = []
    for item in cookie.split(';'):
        if '=' not in item:
            continue
        key, value = item.split('=', 1)
        key = key.strip()
        value = value.strip()
        cookies.append({
            'name': key,
            'value': value,
            'domain': '.douban.com',
            'path': '/'
        })

    context.add_cookies(cookies)
    page = context.new_page()

    # 访问豆瓣音乐
    page.goto('https://music.douban.com', wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(3000)  # 等待 3 秒

    # 检查登录状态
    logged_in = False

    # 方法 1: 检查是否有登录用户信息
    try:
        profile = page.query_selector('a[name="nav-login"]')
        if profile:
            logged_in = True
    except:
        pass

    # 方法 2: 检查是否有登出链接
    try:
        logout = page.query_selector('a[href*="logout"]')
        if logout:
            logged_in = True
    except:
        pass

    # 方法 3: 检查页面标题是否包含用户信息
    try:
        title = page.title()
        if '豆瓣音乐' in title:
            logged_in = True
    except:
        pass

    if logged_in:
        print("[OK] Cookie 有效！已登录豆瓣音乐")
    else:
        print("[FAIL] Cookie 可能已过期或未正确设置")
        print(f"当前页面：{page.url}")
        try:
            print(f"页面标题：{page.title()}")
        except:
            pass

    browser.close()
