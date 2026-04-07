#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban - Check execution context after navigation
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
    print("Debug Execution Context After Navigation")
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
                print(f"  <- {resp.get('method', 'response')} id={resp.get('id')}")
                if resp.get('id') == expected_id:
                    return resp
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as e:
                print(f"  Recv error: {e}")
                return None
        print(f"  Timeout waiting for response")
        return None

    # Enable domains
    print("\n[1] Enabling domains...")
    resp_id = send_cmd("Page.enable")
    resp = get_response(resp_id, 5)

    resp_id = send_cmd("Runtime.enable")
    resp = get_response(resp_id, 5)

    # Drain events for 2 seconds
    print("\n[2] Draining initial events...")
    page_ws.settimeout(0.5)
    events = 0
    while True:
        try:
            msg = page_ws.recv()
            events += 1
            print(f"  Event: {msg[:100]}")
        except:
            break
    print(f"  Drained {events} events")

    # Navigate
    test_query = "Giacomo Lauri-Volpi"
    search_url = f"https://music.douban.com/search?query={urllib.parse.quote(test_query)}&type=1"
    print(f"\n[3] Navigating to search...")
    nav_id = send_cmd("Page.navigate", {"url": search_url})

    # Wait for load event
    print("  Waiting for load event...")
    page_ws.settimeout(15)
    while True:
        msg = json.loads(page_ws.recv())
        if msg.get('method') == 'Page.loadEventFired':
            print(f"  Load event fired!")
            break
        elif msg.get('method') == 'Runtime.executionContextCreated':
            ctx = msg.get('params', {}).get('context', {})
            print(f"  Context created: id={ctx.get('id')} origin={ctx.get('origin')}")

    # Wait a bit more
    time.sleep(2)

    # Drain more events
    print("\n[4] Draining post-load events...")
    page_ws.settimeout(0.5)
    events = 0
    while True:
        try:
            msg = page_ws.recv()
            events += 1
        except:
            break
    print(f"  Drained {events} post-load events")

    # Try evaluation
    print("\n[5] Trying JavaScript evaluation...")
    eval_id = send_cmd("Runtime.evaluate", {
        "expression": "'test-' + Date.now()",
        "returnByValue": True
    })
    resp = get_response(eval_id, 5)

    if resp:
        print(f"\nFull response:")
        print(json.dumps(resp, indent=2, default=str)[:1000])

        if 'result' in resp:
            result = resp['result']
            print(f"\nResult type: {result.get('type')}")
            print(f"Result value: {result.get('value')}")

    # Try with explicit context
    print("\n[6] Trying with explicit contextId...")
    # Get current context
    contexts = []
    page_ws.settimeout(0.5)
    while True:
        try:
            msg = json.loads(page_ws.recv())
            if msg.get('method') == 'Runtime.executionContextCreated':
                ctx = msg.get('params', {}).get('context', {})
                contexts.append(ctx)
                print(f"  Context: id={ctx.get('id')} origin={ctx.get('origin')}")
        except:
            break

    if contexts:
        # Use the music.douban.com context
        music_ctx = None
        for ctx in contexts:
            if 'music.douban.com' in ctx.get('origin', ''):
                music_ctx = ctx.get('id')
                break

        if music_ctx:
            print(f"\n  Using context {music_ctx}")
            eval_id = send_cmd("Runtime.evaluate", {
                "expression": "document.title",
                "returnByValue": True,
                "contextId": music_ctx
            })
            resp = get_response(eval_id, 5)

            if resp and 'result' in resp:
                print(f"  Result: {resp['result'].get('value')}")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
