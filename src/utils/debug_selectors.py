#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban - Find correct search result selectors
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
    print("Find Search Result Selectors")
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

    # Enable domains
    send_cmd("Page.enable")
    send_cmd("Runtime.enable")
    time.sleep(2)

    # Drain events
    page_ws.settimeout(0.5)
    while True:
        try:
            page_ws.recv()
        except:
            break

    # Navigate to search
    test_query = "Giacomo Lauri-Volpi"
    search_url = f"https://music.douban.com/search?query={urllib.parse.quote(test_query)}&type=1"
    print(f"\nNavigating to: {search_url[:80]}...")

    nav_id = send_cmd("Page.navigate", {"url": search_url})

    # Wait for load
    page_ws.settimeout(15)
    while True:
        msg = json.loads(page_ws.recv())
        if msg.get('method') == 'Page.loadEventFired':
            print("Load event fired!")
            break

    time.sleep(3)

    # Check page
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url[:80] if url else 'None'}")
    print(f"Title: {title}")

    # Get all elements with their classes and IDs
    print("\n[1] Scanning page structure...")
    elements_info = eval_js("""
        (function() {
            const all = document.querySelectorAll('*');
            const info = [];
            for (const el of all) {
                if (el.className || el.id || el.tagName === 'A') {
                    info.push({
                        tag: el.tagName,
                        id: el.id || null,
                        class: el.className || null,
                        href: el.href || null,
                        text: (el.textContent || '').trim().substring(0, 50)
                    });
                }
            }
            return info.slice(0, 100);
        })()
    """)

    if elements_info:
        print(f"Found {len(elements_info)} elements with class/id/links")

        # Look for album-like elements
        print("\n[2] Album-like elements:")
        for el in elements_info:
            href = el.get('href') or ''
            if '/subject/' in href or 'music' in href.lower():
                print(f"  {el['tag']} #{el['id']} .{el['class']}")
                print(f"    href: {href[:80]}")
                print(f"    text: {el['text'][:50]}")

        # Look for result containers
        print("\n[3] Potential result containers:")
        for el in elements_info:
            cls = el.get('class') or ''
            if 'result' in cls.lower() or 'card' in cls.lower() or 'item' in cls.lower() or 'list' in cls.lower():
                print(f"  {el['tag']} #{el['id']} .{cls}")

    # Check document structure
    print("\n[4] Document structure:")
    structure = eval_js("""
        (function() {
            const body = document.body;
            if (!body) return 'no body';
            return {
                childCount: body.childElementCount,
                children: Array.from(body.children).map(c => ({
                    tag: c.tagName,
                    id: c.id,
                    class: c.className
                }))
            };
        })()
    """)
    print(f"  Structure: {structure}")

    # Try to find ANY link to a subject
    print("\n[5] All subject links:")
    subject_links = eval_js("""
        (function() {
            const links = document.querySelectorAll('a[href*="/subject/"]');
            return Array.from(links).map(l => ({
                href: l.href,
                text: l.textContent.trim().substring(0, 50),
                parentClass: l.parentElement?.className,
                parentTag: l.parentElement?.tagName
            }));
        })()
    """)
    if subject_links and len(subject_links) > 0:
        for link in subject_links[:10]:
            print(f"  {link['href'][:60]}")
            print(f"    Text: {link['text']}")
            print(f"    Parent: {link['parentTag']} .{link['parentClass']}")
    else:
        print("  No subject links found!")

    # Get full HTML for analysis
    print("\n[6] HTML analysis:")
    html = eval_js("document.documentElement.outerHTML")
    if html:
        print(f"  HTML length: {len(html)}")

        # Check for specific patterns
        patterns = {
            'result': 'result',
            'subject': 'subject',
            'card': 'card',
            'item': 'item',
            'list': 'list',
            'search-result': 'search-result',
            'music-item': 'music-item'
        }
        for pattern, name in patterns.items():
            if pattern.lower() in html.lower():
                print(f"  Contains '{name}': YES")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
