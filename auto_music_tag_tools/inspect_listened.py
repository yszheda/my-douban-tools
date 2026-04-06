#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspect Douban album - Find listened button and tags
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
    print("Find Listened Button and Tags")
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

    # Navigate to album
    album_url = "https://music.douban.com/subject/36188591/"
    print(f"Navigate to: {album_url}")
    eval_js(f"window.location.href = '{album_url}';")
    wait_for_load(15)
    time.sleep(5)

    # Full HTML analysis
    print("\n[HTML Analysis]")
    html = eval_js("document.documentElement.outerHTML")
    if html:
        # Check for specific patterns
        patterns = ['听过', '想听', '不听', '收藏', '标签', 'tag', 'rating', 'star']
        for p in patterns:
            if p in html:
                count = html.lower().count(p.lower())
                print(f"  Contains '{p}': YES ({count} times)")

    # Find all buttons with text
    print("\n[All Buttons with Text]")
    buttons = eval_js("""
        (function() {
            const all = document.querySelectorAll('button, input[type="button"], input[type="submit"], a[href*="javascript"]');
            return Array.from(all).map(el => ({
                tag: el.tagName,
                type: el.type,
                text: el.textContent?.trim().substring(0, 20),
                value: el.value,
                class: el.className,
                id: el.id,
                href: el.href
            }));
        })()
    """)
    if buttons:
        for btn in buttons:
            text = btn.get('text') or btn.get('value') or ''
            if text:
                print(f"  {btn}")

    # Find collection-related elements
    print("\n[Collection Elements]")
    collect = eval_js("""
        (function() {
            const els = document.querySelectorAll('.collect_btn, .ckd-collect, [data-utility-key="collection"], .interest-btn');
            return Array.from(els).map(el => ({
                tag: el.tagName,
                class: el.className,
                id: el.id,
                text: el.textContent?.trim().substring(0, 30),
                outerHTML: el.outerHTML.substring(0, 200)
            }));
        })()
    """)
    if collect:
        for el in collect:
            print(f"  {el}")
    else:
        print("  Not found")

    # Find all elements in sidebar/right column (where tags usually are)
    print("\n[Sidebar Elements]")
    sidebar = eval_js("""
        (function() {
            const sidebars = document.querySelectorAll('.aside, #aside, .sidebar, aside, #content .aside');
            const result = [];
            sidebars.forEach(sb => {
                result.push({
                    class: sb.className,
                    id: sb.id,
                    html: sb.innerHTML.substring(0, 500)
                });
            });
            return result;
        })()
    """)
    if sidebar:
        for el in sidebar:
            print(f"  Class: {el.get('class', 'none')}")
            print(f"  ID: {el.get('id', 'none')}")
            print(f"  HTML: {el.get('html', '')[:300]}...")
    else:
        print("  No sidebar found")

    # Find tag section
    print("\n[Tag Section]")
    tags = eval_js("""
        (function() {
            // Look for tag-related sections
            const selectors = ['.tags', '.tag', '#tags', '.user-tags', '.subject-tags', '.tag-list'];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el) {
                    return {
                        selector: sel,
                        class: el.className,
                        html: el.innerHTML.substring(0, 500)
                    };
                }
            }
            return null;
        })()
    """)
    if tags:
        print(f"  Found: {tags}")
    else:
        print("  Not found")

    # Look for any input elements
    print("\n[All Inputs]")
    inputs = eval_js("""
        (function() {
            return Array.from(document.querySelectorAll('input, textarea')).map(inp => ({
                tag: inp.tagName,
                type: inp.type,
                name: inp.name,
                id: inp.id,
                class: inp.className,
                placeholder: inp.placeholder,
                value: inp.value
            }));
        })()
    """)
    if inputs:
        for inp in inputs:
            print(f"  {inp}")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
