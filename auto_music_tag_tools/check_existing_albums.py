#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check if failing albums already exist on Douban
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

    # Test searches
    searches = [
        "Fabienne Jacquinot A Tribute",
        "Debussy Early Works Piano Duet",
    ]

    for search_query in searches:
        print(f"\n{'='*60}")
        print(f"Search: {search_query}")
        print(f"{'='*60}")

        # Navigate to music.douban.com first
        eval_js("window.location.href = 'https://music.douban.com/';")
        time.sleep(3)

        # Search
        eval_js(f"""
            (function() {{
                const input = document.querySelector('input[name="search_text"]');
                if (input) {{
                    input.value = {json.dumps(search_query)};
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    const form = input.closest('form');
                    if (form) form.submit();
                }}
            }})()
        """)
        time.sleep(5)

        # Check results
        url = eval_js("location.href")
        print(f"Result URL: {url}")

        results = eval_js("""
            (function() {
                const subjects = document.querySelectorAll('.subject-list .subject, .result-list .subject');
                return Array.from(subjects).map(s => ({
                    title: s.querySelector('a[href*="/subject/"]')?.textContent?.trim(),
                    href: s.querySelector('a[href*="/subject/"]')?.href
                }));
            })()
        """)

        if results:
            print(f"Found {len(results)} results:")
            for r in results:
                print(f"  - {r.get('title', 'N/A')}: {r.get('href', 'N/A')}")
        else:
            print("No results found")

    page_ws.close()
    print(f"\n{'='*60}")
    print("Done")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
