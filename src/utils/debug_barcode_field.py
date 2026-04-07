#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban create page - find all fields including barcode
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
    print("Debug Create Page - All Fields")
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
    time.sleep(3)

    # Fill title and artist, click next
    print("\n[Filling Step 1]")
    step1 = eval_js("""
        (function() {
            document.querySelector('input[name="p_title"]').value = 'Test Barcode Field';
            document.querySelector('input[name="p_uid"]').value = 'Test Artist';
            document.querySelector('input[name="subject_submit"]').click();
            return 'clicked';
        })()
    """)
    print(f"Step 1: {step1}")
    time.sleep(5)

    # Check current state
    print("\n[Page State]")
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Find ALL input fields
    print("\n[ALL Input Fields]")
    all_inputs = eval_js("""
        (function() {
            const all = document.querySelectorAll('input, textarea, select');
            return Array.from(all).map(el => ({
                tag: el.tagName,
                type: el.type,
                name: el.name,
                id: el.id,
                class: el.className,
                placeholder: el.placeholder,
                value: el.value,
                visible: el.offsetParent !== null,
                disabled: el.disabled
            }));
        })()
    """)

    if all_inputs:
        for inp in all_inputs:
            if inp.get('visible') and not inp.get('disabled'):
                print(f"  {inp}")
    else:
        print("  No inputs found")

    # Find ALL labels
    print("\n[ALL Labels]")
    labels = eval_js("""
        (function() {
            const all = document.querySelectorAll('label');
            return Array.from(all).map(l => ({
                text: l.textContent?.trim(),
                htmlFor: l.htmlFor,
                id: l.id
            }));
        })()
    """)

    if labels:
        for lbl in labels:
            if lbl.get('text'):
                print(f"  '{lbl['text']}' for='{lbl['htmlFor']}'")
    else:
        print("  No labels found")

    # Check for barcode field specifically
    print("\n[Barcode Field Check]")
    barcode_field = eval_js("""
        (function() {
            const selectors = [
                'input[name="p_barcode"]',
                'input[name="barcode"]',
                'input#barcode',
                'input#p_barcode',
                'input[placeholder*="条码"]',
                'input[placeholder*="条形码"]',
                'input[placeholder*="EAN"]',
                'input[placeholder*="UPC"]'
            ];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el) {
                    return {
                        found: true,
                        selector: sel,
                        name: el.name,
                        id: el.id,
                        type: el.type,
                        placeholder: el.placeholder,
                        visible: el.offsetParent !== null
                    };
                }
            }
            return { found: false };
        })()
    """)
    print(f"  {barcode_field}")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)

if __name__ == '__main__':
    main()
