#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban - Navigate with proper wait for load
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
    print("Debug Navigate With Load Wait")
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
    time.sleep(1)

    # Drain events
    page_ws.settimeout(0.5)
    while True:
        try:
            page_ws.recv()
        except:
            break

    cmd_id = [100]

    def send_cmd(method, params=None):
        cmd = {"id": cmd_id[0], "method": method, "params": params or {}}
        cmd_id[0] += 1
        page_ws.send(json.dumps(cmd))
        return cmd['id']

    def get_response(expected_id):
        page_ws.settimeout(10)
        while True:
            try:
                resp = json.loads(page_ws.recv())
                if resp.get('id') == expected_id:
                    return resp
            except Exception as e:
                print(f"Receive error: {e}")
                return None

    def eval_js(script):
        resp_id = send_cmd("Runtime.evaluate", {
            "expression": script,
            "returnByValue": True
        })
        resp = get_response(resp_id)
        if resp and 'result' in resp and 'value' in resp.get('result', {}):
            return resp['result']['value']
        return None

    # Navigate with proper wait
    test_query = "Giacomo Lauri-Volpi"
    search_url = f"https://music.douban.com/search?query={urllib.parse.quote(test_query)}&type=1"
    print(f"\nNavigating to: {search_url[:80]}...")

    # Navigate and wait for load
    nav_id = send_cmd("Page.navigate", {"url": search_url})
    print("Waiting for page load...")

    # Wait for loadEventFired
    page_ws.settimeout(15)
    load_fired = False
    start = time.time()
    while time.time() - start < 10 and not load_fired:
        try:
            msg = json.loads(page_ws.recv())
            if msg.get('method') == 'Page.loadEventFired':
                load_fired = True
                print("Load event fired!")
        except websocket.WebSocketTimeoutException:
            continue
        except Exception as e:
            print(f"Event error: {e}")
            break

    if not load_fired:
        print("Timeout waiting for load event")

    # Extra wait for JavaScript to initialize
    print("Waiting for JS to initialize...")
    time.sleep(3)

    # Now try to evaluate
    print("\nChecking page state...")
    url = eval_js("location.href")
    print(f"URL: {url[:100] if url else 'None'}")

    title = eval_js("document.title")
    print(f"Title: {title}")

    ready = eval_js("document.readyState")
    print(f"Ready: {ready}")

    # Get body content
    body_text = eval_js("document.body.innerText")
    if body_text:
        print(f"\nBody text (first 300 chars):")
        print(body_text[:300])

    # Check for search results
    result_info = eval_js("""
        (function() {
            const results = document.querySelectorAll('.result-list .result, .result-list li, a[href*="/subject/"]');
            return {
                count: results.length,
                firstHref: results[0]?.href,
                firstText: results[0]?.textContent?.trim().substring(0, 50)
            };
        })()
    """)
    print(f"\nSearch results: {result_info}")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
