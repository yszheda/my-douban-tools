#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find all forms on cover upload page
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
    print("Find All Forms on Cover Upload Page")
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

    # Find ALL forms
    print("\n[All Forms]")
    all_forms = eval_js("""
        (function() {
            const forms = document.querySelectorAll('form');
            return Array.from(forms).map((f, i) => ({
                index: i,
                action: f.action,
                method: f.method,
                class: f.className,
                id: f.id,
                inputs: Array.from(f.querySelectorAll('input')).map(inp => ({
                    name: inp.name,
                    type: inp.type,
                    value: inp.value
                }))
            }));
        })()
    """)

    for form in all_forms:
        print(f"\n--- Form {form['index']} ---")
        print(f"Action: {form['action']}")
        print(f"Method: {form['method']}")
        print(f"Class: {form['class']}")
        print(f"ID: {form['id']}")
        print("Inputs:")
        for inp in form['inputs']:
            print(f"  {inp['type']}: name={inp['name']}, value={inp['value']}")

    # Get full HTML of the page
    print("\n[Full Page HTML - First 5000 chars]")
    full_html = eval_js("document.documentElement.outerHTML")
    if full_html:
        print(full_html[:5000])

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)

if __name__ == '__main__':
    main()
