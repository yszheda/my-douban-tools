#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search for barcode 8712177053346 to check if album already exists
"""

import json
import time
import sys
import requests
import websocket

sys.stdout.reconfigure(encoding='utf-8')

def main():
    debug_port = 9222
    debug_url = f"http://127.0.0.1:{debug_port}"

    print("="*60)
    print("Search for existing album by barcode")
    print("Barcode: 8712177053346")
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

    # Navigate to music.douban.com
    print("\nNavigate to music.douban.com")
    eval_js("window.location.href = 'https://music.douban.com/';")
    wait_for_load(15)
    time.sleep(3)

    # Search using the search box
    print("\nSearch for barcode 8712177053346")
    search_result = eval_js("""
        (function() {
            const searchInput = document.querySelector('input[name="search_text"], #inp-query');
            if (searchInput) {
                searchInput.value = '8712177053346';
                searchInput.dispatchEvent(new Event('input', { bubbles: true }));

                // Submit form
                const form = searchInput.closest('form');
                if (form) {
                    form.submit();
                    return 'submitted';
                }
            }
            return 'not found';
        })()
    """)
    print(f"Search: {search_result}")

    # Wait for results
    print("Waiting for search results...")
    time.sleep(5)

    # Check results
    print("\n[Search Results]")
    url = eval_js("location.href")
    print(f"URL: {url}")

    # Check if we're on a subject page
    if '/subject/' in url:
        print("Album already exists!")
        print(f"Subject URL: {url}")
        return

    # Check result count
    result_count = eval_js("""
        (function() {
            const count = document.querySelector('.result_count');
            if (count) {
                return count.textContent;
            }
            const subjects = document.querySelectorAll('.subject-list .subject, .result-list .subject');
            return subjects.length.toString();
        })()
    """)
    print(f"Result count: {result_count}")

    # List results
    results = eval_js("""
        (function() {
            const subjects = document.querySelectorAll('.subject-list .subject, .result-list .subject');
            return Array.from(subjects).map(s => ({
                title: s.querySelector('a[href*=\"/subject/\"]')?.textContent?.trim(),
                href: s.querySelector('a[href*=\"/subject/\"]')?.href,
                info: s.querySelector('.attrs')?.textContent?.trim()
            }));
        })()
    """)

    if results:
        print("\nFound albums:")
        for r in results:
            print(f"  Title: {r.get('title')}")
            print(f"  URL: {r.get('href')}")
            print(f"  Info: {r.get('info')}")
            print()
    else:
        print("No results found")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)

if __name__ == '__main__':
    main()
