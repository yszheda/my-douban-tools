#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug submit button on Douban create page
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
    print("Debug Submit Button")
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

    # Navigate to create page
    create_url = "https://music.douban.com/new_subject?cat=1003"
    print(f"\nNavigate to: {create_url}")
    eval_js(f"window.location.href = '{create_url}';")
    wait_for_load(15)
    time.sleep(5)

    # Check page
    print("\n[Page Info]")
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Find ALL buttons and inputs
    print("\n[ALL Buttons and Inputs]")
    all_buttons = eval_js("""
        (function() {
            const all = document.querySelectorAll('button, input[type="submit"], input[type="button"], input[type="reset"], a[href*="javascript"]');
            return Array.from(all).map(el => ({
                tag: el.tagName,
                type: el.type,
                value: el.value,
                text: el.textContent?.trim().substring(0, 30),
                id: el.id,
                class: el.className,
                name: el.name,
                href: el.href,
                visible: el.offsetParent !== null,
                outerHTML: el.outerHTML.substring(0, 200)
            }));
        })()
    """)

    if all_buttons:
        for btn in all_buttons:
            print(f"  {btn}")
    else:
        print("  No buttons found")

    # Find ALL input elements
    print("\n[ALL Input Elements]")
    all_inputs = eval_js("""
        (function() {
            const all = document.querySelectorAll('input, textarea, select');
            return Array.from(all).map(inp => ({
                tag: inp.tagName,
                type: inp.type,
                name: inp.name,
                id: inp.id,
                class: inp.className,
                placeholder: inp.placeholder,
                value: inp.value,
                visible: inp.offsetParent !== null,
                disabled: inp.disabled,
                readonly: inp.readOnly
            }));
        })()
    """)

    if all_inputs:
        for inp in all_inputs:
            if inp.get('visible') and not inp.get('disabled'):
                print(f"  {inp}")
    else:
        print("  No inputs found")

    # Get form HTML
    print("\n[Form HTML]")
    form_html = eval_js("""
        (function() {
            const form = document.querySelector('form');
            if (form) {
                return form.outerHTML;
            }
            return null;
        })()
    """)

    if form_html:
        print(f"  {form_html[:2000]}...")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
