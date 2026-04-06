#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspect Douban search box structure
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
    print("Inspect Douban Search Box")
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

    # Find search inputs
    print("\n[Search Inputs]")
    inputs = eval_js("""
        (function() {
            const inputs = document.querySelectorAll('input[type="text"], input[type="search"], input[name]');
            return Array.from(inputs).map(inp => ({
                tag: inp.tagName,
                type: inp.type,
                name: inp.name,
                id: inp.id,
                class: inp.className,
                placeholder: inp.placeholder,
                value: inp.value,
                visible: inp.offsetParent !== null
            }));
        })()
    """)

    if inputs:
        for inp in inputs:
            print(f"  {inp}")
    else:
        print("  No inputs found")

    # Find forms
    print("\n[Forms]")
    forms = eval_js("""
        (function() {
            const forms = document.querySelectorAll('form');
            return Array.from(forms).map(form => ({
                id: form.id,
                class: form.className,
                action: form.action,
                method: form.method,
                inputs: Array.from(form.querySelectorAll('input')).map(i => ({
                    type: i.type,
                    name: i.name,
                    value: i.value
                }))
            }));
        })()
    """)

    if forms:
        for form in forms:
            print(f"  {form}")
    else:
        print("  No forms found")

    # Find search buttons
    print("\n[Search Buttons]")
    buttons = eval_js("""
        (function() {
            const buttons = document.querySelectorAll('button, input[type="submit"]');
            return Array.from(buttons).map(btn => ({
                tag: btn.tagName,
                type: btn.type,
                text: btn.textContent?.trim(),
                value: btn.value,
                class: btn.className,
                id: btn.id
            }));
        })()
    """)

    if buttons:
        for btn in buttons:
            print(f"  {btn}")
    else:
        print("  No buttons found")

    # Check page structure
    print("\n[Page Structure]")
    structure = eval_js("""
        (function() {
            const wrapper = document.getElementById('wrapper');
            if (wrapper) {
                return {
                    id: 'wrapper',
                    children: Array.from(wrapper.children).map(c => ({
                        tag: c.tagName,
                        id: c.id,
                        class: c.className
                    }))
                };
            }
            return {
                bodyChildren: Array.from(document.body.children).map(c => ({
                    tag: c.tagName,
                    id: c.id,
                    class: c.className
                }))
            };
        })()
    """)
    print(f"  {structure}")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
