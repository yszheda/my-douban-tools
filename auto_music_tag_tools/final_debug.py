#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final debug - Check what's on the search results page
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
    print("Final Search Debug")
    print("="*60)

    pages = requests.get(f"{debug_url}/json/list", timeout=5).json()
    douban_page = None
    for page in pages:
        if 'douban.com' in page.get('url', ''):
            douban_page = page
            break

    if not douban_page:
        print("No Douban page found")
        sys.exit(1)

    page_ws = websocket.create_connection(douban_page.get('webSocketDebuggerUrl'), timeout=10)
    print("Connected!")

    cmd_id = [100]

    def send_cmd(method, params=None):
        cmd = {"id": cmd_id[0], "method": method, "params": params or {}}
        cmd_id[0] += 1
        page_ws.send(json.dumps(cmd))
        return cmd['id']

    def get_response(expected_id, timeout=10):
        page_ws.settimeout(timeout)
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = json.loads(page_ws.recv())
                if resp.get('id') == expected_id:
                    return resp
            except:
                continue
        return None

    def eval_js(script):
        resp_id = send_cmd("Runtime.evaluate", {
            "expression": script,
            "returnByValue": True
        })
        resp = get_response(resp_id, 10)
        if resp and 'result' in resp:
            inner = resp['result'].get('result', {})
            return inner.get('value')
        return None

    def wait_for_load(timeout=10):
        page_ws.settimeout(timeout)
        start = time.time()
        while time.time() - start < timeout:
            try:
                msg = json.loads(page_ws.recv())
                if msg.get('method') == 'Page.loadEventFired':
                    return True
            except:
                continue
        return False

    send_cmd("Page.enable")
    send_cmd("Runtime.enable")
    time.sleep(1)

    # Drain
    page_ws.settimeout(0.5)
    while True:
        try:
            page_ws.recv()
        except:
            break

    # Navigate to search
    test_query = "Giacomo Lauri-Volpi"
    search_url = f"https://music.douban.com/search?query={urllib.parse.quote(test_query)}&type=1"
    print(f"Navigate to: {search_url}")

    eval_js(f"window.location.href = '{search_url}';")
    wait_for_load(15)
    time.sleep(5)

    # Check state
    print("\n[State Check]")
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Get all text content
    print("\n[Page Text Content]")
    text = eval_js("document.body.innerText")
    if text:
        print(f"Body text (first 1000 chars):")
        print(text[:1000])

    # Get all links
    print("\n[All Links]")
    links = eval_js("""
        (function() {
            const links = document.querySelectorAll('a[href]');
            return Array.from(links).map(l => ({
                href: l.href,
                text: l.textContent.trim().substring(0, 50)
            })).filter(l => l.href.includes('douban'));
        })()
    """)
    if links:
        for link in links[:20]:
            print(f"  {link['href'][:70]} - '{link['text']}'")

    # Check HTML for specific patterns
    print("\n[HTML Analysis]")
    html = eval_js("document.documentElement.outerHTML")
    if html:
        # Look for result-related content
        if 'result' in html.lower():
            print("  Contains 'result': YES")
            # Find the context
            import re
            matches = re.findall(r'.{50}result.{50}', html.lower())
            if matches:
                print(f"  Context: {matches[0][:100]}")

        if 'subject' in html.lower():
            print("  Contains 'subject': YES")

        if '没有找到' in html or 'no result' in html.lower():
            print("  Contains 'no results' message: YES")

        if 'captcha' in html.lower():
            print("  Contains 'captcha': YES")

        if '安全' in html or '验证' in html:
            print("  Contains security check: YES")

    # Check for specific elements
    print("\n[DOM Elements]")
    elements = eval_js("""
        (function() {
            const result = [];
            document.querySelectorAll('*').forEach(el => {
                if (el.className) {
                    const classes = el.className.split(' ');
                    for (const cls of classes) {
                        if (cls.toLowerCase().includes('result') ||
                            cls.toLowerCase().includes('item') ||
                            cls.toLowerCase().includes('card')) {
                            result.push({
                                tag: el.tagName,
                                class: el.className,
                                id: el.id,
                                text: el.textContent.substring(0, 50)
                            });
                        }
                    }
                }
            });
            return result.slice(0, 20);
        })()
    """)
    if elements:
        for el in elements:
            print(f"  {el['tag']}.{el['class']} - '{el['text']}'")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
