#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban - Test different search URL formats
"""

import json
import time
import sys
import requests
import websocket


def main():
    debug_port = 9222
    debug_url = f"http://127.0.0.1:{debug_port}"

    print("="*60)
    print("Test Search URL Formats")
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

    # Drain events
    page_ws.settimeout(0.5)
    while True:
        try:
            page_ws.recv()
        except:
            break

    # Test different URL formats
    test_query = "Giacomo Lauri-Volpi"
    urls = [
        f"https://music.douban.com/search?query={test_query}&type=1",
        f"https://music.douban.com/search?keyword={test_query}&type=1",
        f"https://music.douban.com/subject_search?search_text={test_query}&cat=1003",
        f"https://music.douban.com/subject_search?search_text={test_query}&type=1",
        f"https://music.douban.com/search?q={test_query}",
    ]

    for i, url in enumerate(urls):
        print(f"\n[Test {i+1}] {url[:70]}...")

        # Navigate
        send_cmd("Page.navigate", {"url": url})
        wait_for_load(8)
        time.sleep(2)

        # Check result
        result_url = eval_js("location.href")
        title = eval_js("document.title")

        print(f"  Result URL: {result_url[:70] if result_url else 'None'}...")
        print(f"  Title: {title}")

        # Check for results
        has_results = eval_js("""
            (function() {
                const selectors = ['.result-list .result', '.result-list li', 'a[href*="/subject/"]'];
                for (const sel of selectors) {
                    if (document.querySelectorAll(sel).length > 0) {
                        return true;
                    }
                }
                return false;
            })()
        """)
        print(f"  Has results: {has_results}")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
