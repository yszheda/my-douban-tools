#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban - Check navigation behavior
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
    print("Debug Navigation Behavior")
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

    print(f"Starting page: {douban_page.get('url')}")

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

    # Check initial URL
    initial_url = eval_js("location.href")
    print(f"Initial URL: {initial_url}")

    # Navigate to search
    test_query = "Giacomo Lauri-Volpi"
    search_url = f"https://music.douban.com/search?query={urllib.parse.quote(test_query)}&type=1"
    print(f"\nNavigating to: {search_url}")

    # Use Page.navigate
    nav_id = send_cmd("Page.navigate", {"url": search_url})
    print("Sent Page.navigate command")

    # Wait for various events
    events = []
    page_ws.settimeout(10)
    start = time.time()
    while time.time() - start < 8:
        try:
            msg = json.loads(page_ws.recv())
            method = msg.get('method', '')
            events.append(method)
            print(f"Event: {method}")

            if method == 'Page.loadEventFired':
                print("  -> Load event fired!")
            elif method == 'Page.frameStartedLoading':
                print(f"  -> Frame loading: {msg.get('params', {}).get('frameId', '')}")
            elif method == 'Page.frameStoppedLoading':
                print(f"  -> Frame stopped loading")
            elif method == 'Page.navigatedWithinDocument':
                url = msg.get('params', {}).get('url', '')
                print(f"  -> In-page navigation: {url[:80]}")
        except websocket.WebSocketTimeoutException:
            break
        except Exception as e:
            print(f"Event error: {e}")
            break

    print(f"\nTotal events received: {len(events)}")

    # Wait more for page to settle
    time.sleep(3)

    # Check URL again
    current_url = eval_js("location.href")
    print(f"\nCurrent URL: {current_url}")

    # Check if URL matches expected
    if current_url and search_url in current_url:
        print("SUCCESS: URL matches search URL!")
    else:
        print("ISSUE: URL does not match search URL")
        print(f"  Expected: {search_url}")
        print(f"  Got: {current_url}")

    # Try direct JavaScript navigation as alternative
    print("\n[Trying JavaScript navigation...]")
    eval_js(f"window.location.href = '{search_url}';")
    time.sleep(5)

    js_url = eval_js("location.href")
    print(f"After JS navigation: {js_url}")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
