#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check album creation success page
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
    print("Check Album Creation Success Page")
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

    # Check current page
    print("\n[Current Page]")
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Get page content
    print("\n[Page Content]")
    content = eval_js("document.body.innerText")
    if content:
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        for line in lines[:20]:
            print(f"  {line}")

    # Find any links
    print("\n[Links]")
    links = eval_js("""
        (function() {
            const links = document.querySelectorAll('a[href]');
            return Array.from(links).map(a => ({
                text: a.textContent?.trim(),
                href: a.href
            })).filter(l => l.text && l.href);
        })()
    """)

    if links:
        for link in links:
            print(f"  {link['text']}: {link['href']}")

    # Check for subject URL
    print("\n[Check for Album URL]")
    subject_link = eval_js("""
        (function() {
            const links = document.querySelectorAll('a[href*="/subject/"]');
            if (links.length > 0) {
                return links[0].href;
            }
            return null;
        })()
    """)

    if subject_link:
        print(f"Found album link: {subject_link}")
    else:
        print("No album link found")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)

if __name__ == '__main__':
    main()
