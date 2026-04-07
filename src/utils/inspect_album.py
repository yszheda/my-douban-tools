#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspect Douban album page structure
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
    print("Inspect Douban Album Page")
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

    print(f"Page: {douban_page.get('url')}")

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

    # Navigate to an album page
    album_url = "https://music.douban.com/subject/36188591/"
    print(f"\nNavigate to album: {album_url}")

    eval_js(f"window.location.href = '{album_url}';")
    wait_for_load(15)
    time.sleep(3)

    # Check page
    print("\n[Page Info]")
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Find interest buttons
    print("\n[Interest Buttons]")
    buttons = eval_js("""
        (function() {
            const buttons = document.querySelectorAll('input[value], button, .interest-btn, [data-utility-key]');
            return Array.from(buttons).map(btn => ({
                tag: btn.tagName,
                type: btn.type,
                value: btn.value,
                text: btn.textContent?.trim().substring(0, 20),
                class: btn.className,
                id: btn.id,
                checked: btn.checked,
                'data-utility-key': btn.getAttribute?.('data-utility-key')
            }));
        })()
    """)

    if buttons:
        for btn in buttons:
            if btn.get('value') or '听' in str(btn.get('text', '')):
                print(f"  {btn}")
    else:
        print("  No buttons found")

    # Find tag inputs
    print("\n[Tag Inputs]")
    inputs = eval_js("""
        (function() {
            const inputs = document.querySelectorAll('input[name*="tag"], .tag-input, #tags-input, [placeholder*="标签"]');
            return Array.from(inputs).map(inp => ({
                tag: inp.tagName,
                type: inp.type,
                name: inp.name,
                id: inp.id,
                class: inp.className,
                placeholder: inp.placeholder
            }));
        })()
    """)

    if inputs:
        for inp in inputs:
            print(f"  {inp}")
    else:
        print("  No tag inputs found")

    # Find all classes related to tags
    print("\n[Tag Related Classes]")
    tag_classes = eval_js("""
        (function() {
            const allClasses = new Set();
            document.querySelectorAll('*').forEach(el => {
                for (const cls of el.classList) {
                    if (cls.toLowerCase().includes('tag')) {
                        allClasses.add(cls);
                    }
                }
            });
            return Array.from(allClasses);
        })()
    """)

    if tag_classes:
        for cls in tag_classes:
            print(f"  .{cls}")
    else:
        print("  No tag-related classes found")

    # Find all classes related to interest/collection
    print("\n[Interest Related Classes]")
    interest_classes = eval_js("""
        (function() {
            const allClasses = new Set();
            document.querySelectorAll('*').forEach(el => {
                for (const cls of el.classList) {
                    const name = cls.toLowerCase();
                    if (name.includes('interest') || name.includes('collect') || name.includes('listen')) {
                        allClasses.add(cls);
                    }
                }
            });
            return Array.from(allClasses);
        })()
    """)

    if interest_classes:
        for cls in interest_classes:
            print(f"  .{cls}")
    else:
        print("  No interest-related classes found")

    # Check for utility bar
    print("\n[Utility Bar]")
    utility = eval_js("""
        (function() {
            const utilityBar = document.querySelector('.utility-bar, .interest-bar, .utility-list');
            if (utilityBar) {
                return {
                    class: utilityBar.className,
                    id: utilityBar.id,
                    html: utilityBar.innerHTML.substring(0, 500)
                };
            }
            return null;
        })()
    """)
    if utility:
        print(f"  {utility}")
    else:
        print("  No utility bar found")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
