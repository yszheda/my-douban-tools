#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test creating album on Douban with detailed feedback
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
    print("Test Create Album on Douban")
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

    # Test data
    test_album = {
        'title': 'Test Album For Debug',
        'artist': 'Test Artist',
        'label': 'Test Label',
        'barcode': '1234567890123'
    }

    # Navigate to create page
    create_url = "https://music.douban.com/new_subject?cat=1003"
    print(f"\nNavigate to: {create_url}")
    eval_js(f"window.location.href = '{create_url}';")
    wait_for_load(15)
    time.sleep(3)

    # Check page state
    print("\n[Page State]")
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Get detailed form info
    print("\n[Detailed Form Analysis]")
    form_info = eval_js("""
        (function() {
            const result = {
                inputs: [],
                buttons: [],
                labels: [],
                fullHTML: ''
            };

            // All inputs
            const inputs = document.querySelectorAll('input, textarea, select');
            inputs.forEach(inp => {
                result.inputs.push({
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
                });
            });

            // All buttons
            const buttons = document.querySelectorAll('button, input[type="submit"], input[type="button"]');
            buttons.forEach(btn => {
                result.buttons.push({
                    tag: btn.tagName,
                    type: btn.type,
                    value: btn.value,
                    text: btn.textContent?.trim(),
                    id: btn.id,
                    class: btn.className,
                    visible: btn.offsetParent !== null
                });
            });

            // All labels
            const labels = document.querySelectorAll('label');
            labels.forEach(lbl => {
                result.labels.push({
                    text: lbl.textContent?.trim(),
                    htmlFor: lbl.htmlFor,
                    id: lbl.id
                });
            });

            return result;
        })()
    """)

    if form_info:
        print("\n[Inputs]")
        for inp in form_info.get('inputs', []):
            if inp.get('visible') and not inp.get('disabled'):
                print(f"  {inp['tag']} name='{inp.get('name','')}' id='{inp.get('id','')}' type='{inp.get('type','')}' placeholder='{inp.get('placeholder','')}'")

        print("\n[Buttons]")
        for btn in form_info.get('buttons', []):
            if btn.get('visible'):
                print(f"  {btn['tag']} type='{btn.get('type','')}' value='{btn.get('value','')}' text='{btn.get('text','')}'")

        print("\n[Labels]")
        for lbl in form_info.get('labels', []):
            if lbl.get('text'):
                print(f"  '{lbl.get('text')}' for='{lbl.get('htmlFor','')}'")

    # Try to fill and submit
    print(f"\n[Attempting to fill form]")
    fill_result = eval_js(f"""
        (function() {{
            const info = {json.dumps(test_album)};
            const result = {{ filled: {{}} }};

            // Find title field (p_title)
            const titleField = document.querySelector('input[name="p_title"]');
            if (titleField) {{
                titleField.value = info.title;
                titleField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                result.filled.title = true;
            }}

            // Find artist field (uid)
            const artistField = document.querySelector('input[name="uid"], input[id="uid"]');
            if (artistField) {{
                artistField.value = info.artist;
                artistField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                result.filled.artist = true;
            }}

            // Find submit button (not search button)
            const buttons = document.querySelectorAll('input[type="submit"], button');
            for (const btn of buttons) {{
                const text = (btn.value || btn.textContent || '').toLowerCase();
                if (text && !text.includes('搜索') && !text.includes('search')) {{
                    result.submitBtn = {{
                        tag: btn.tagName,
                        type: btn.type,
                        value: btn.value,
                        text: btn.textContent?.trim()
                    }};
                    // Don't click yet, just identify
                    break;
                }}
            }}

            return result;
        }})()
    """)

    print(f"Fill result: {fill_result}")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
