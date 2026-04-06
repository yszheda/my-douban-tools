#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban - Check search results content
"""

import json
import time
import sys
import urllib.parse
import requests
import websocket


def main():
    debug_port = 9222
    debug_url = f"http://127.0.0.1:{debug_port}"

    print("="*60)
    print("Debug Search Results Content")
    print("="*60)

    # Get pages
    pages = requests.get(f"{debug_url}/json/list", timeout=5).json()
    douban_page = None
    for page in pages:
        if 'douban.com' in page.get('url', ''):
            douban_page = page
            break

    if not douban_page:
        print("No Douban page found")
        sys.exit(1)

    print(f"Found page: {douban_page.get('url')}")

    # Connect to page
    page_ws = websocket.create_connection(douban_page.get('webSocketDebuggerUrl'), timeout=10)
    print("Connected!")

    # Enable domains
    page_ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
    page_ws.send(json.dumps({"id": 2, "method": "Runtime.enable"}))
    time.sleep(2)

    # Drain events
    page_ws.settimeout(0.5)
    while True:
        try:
            page_ws.recv()
        except:
            break

    def eval_js(script):
        cmd = {
            "id": page_ws._command_id if hasattr(page_ws, '_command_id') else 100,
            "method": "Runtime.evaluate",
            "params": {
                "expression": script,
                "returnByValue": True
            }
        }
        if not hasattr(page_ws, '_command_id'):
            page_ws._command_id = 100
        page_ws._command_id += 1

        page_ws.send(json.dumps(cmd))
        page_ws.settimeout(5)

        while True:
            try:
                resp = json.loads(page_ws.recv())
                if resp.get('id') == cmd['id']:
                    if 'result' in resp and 'value' in resp.get('result', {}):
                        return resp['result']['value']
                    return None
            except:
                return None

    # Navigate to search
    test_query = "Giacomo Lauri-Volpi"
    search_url = f"https://music.douban.com/search?query={urllib.parse.quote(test_query)}&type=1"
    print(f"\nNavigating to: {search_url}")

    nav_cmd = {"id": 10, "method": "Page.navigate", "params": {"url": search_url}}
    page_ws.send(json.dumps(nav_cmd))
    time.sleep(5)  # Wait for navigation

    # Check URL
    url = eval_js("location.href")
    print(f"Current URL: {url[:100] if url else 'None'}")

    # Check title
    title = eval_js("document.title")
    print(f"Title: {title}")

    # Check if we see login page
    is_login = eval_js("document.body.innerText.includes('登录') || document.title.includes('登录')")
    print(f"Is login page: {is_login}")

    # Get body text
    body_text = eval_js("document.body.innerText")
    if body_text:
        print(f"\nBody text (first 500 chars):")
        print(body_text[:500])

    # Check for result items
    result_count = eval_js("""
        (function() {
            const selectors = [
                '.result-list .result',
                '.result-list li',
                '.card-wrap',
                '.music-item',
                'article[data-id]',
                'a[href*="/subject/"]'
            ];
            let total = 0;
            for (const sel of selectors) {
                const count = document.querySelectorAll(sel).length;
                if (count > 0) {
                    total += count;
                    console.log(sel + ': ' + count);
                }
            }
            return total;
        })()
    """)
    print(f"\nResult items found: {result_count}")

    # Get all links
    links = eval_js("""
        (function() {
            const links = Array.from(document.querySelectorAll('a[href]'));
            return links.slice(0, 30).map(a => ({
                href: a.href,
                text: a.textContent.trim().substring(0, 30)
            }));
        })()
    """)
    if links:
        print(f"\nLinks on page ({len(links)}):")
        for link in links[:10]:
            print(f"  {link['href'][:60]}... - '{link['text']}'")

    # Get HTML structure
    html_length = eval_js("document.documentElement.outerHTML.length")
    print(f"\nHTML length: {html_length}")

    # Check for specific indicators
    checks = eval_js("""
        (function() {
            const html = document.documentElement.outerHTML;
            return {
                has_result: html.includes('result'),
                has_subject: html.includes('subject'),
                has_search: html.includes('search'),
                has_login: html.includes('登录') || html.includes('login'),
                has_captcha: html.includes('captcha') || html.includes('验证码'),
                has_antibot: html.includes('antibot') || html.includes('安全')
            };
        })()
    """)
    print(f"\nPage checks: {checks}")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
