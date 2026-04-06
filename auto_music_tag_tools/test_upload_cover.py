#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete album creation - upload cover image
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
    print("Complete Album Creation - Upload Cover")
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

    # Check current page
    print("\n[Current Page]")
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Check if we're on the cover upload page
    if 'upload_cover' in url or '上传' in title:
        print("\n[Cover Upload Page Detected]")

        # Find cover input fields
        cover_fields = eval_js("""
            (function() {
                const fields = {
                    has_cover_url: !!document.querySelector('input[name="cover_url"]'),
                    has_file_input: !!document.querySelector('input[type="file"]'),
                    has_submit: !!document.querySelector('input[type="submit"]')
                };
                return fields;
            })()
        """)
        print(f"Cover fields: {cover_fields}")

        # Get all inputs
        inputs = eval_js("""
            (function() {
                return Array.from(document.querySelectorAll('input')).map(i => ({
                    name: i.name,
                    type: i.type,
                    value: i.value,
                    placeholder: i.placeholder
                }));
            })()
        """)
        print(f"Inputs: {inputs}")

        # Get all labels
        labels = eval_js("""
            (function() {
                return Array.from(document.querySelectorAll('label')).map(l => ({
                    text: l.textContent?.trim(),
                    htmlFor: l.htmlFor
                }));
            })()
        """)
        print(f"Labels: {labels}")

        # Try to submit with a placeholder cover URL
        print("\n[Try to submit with cover URL]")
        submit_result = eval_js("""
            (function() {
                // Find cover URL input
                const coverInput = document.querySelector('input[name="cover_url"]');
                if (coverInput) {
                    // Set a placeholder URL or leave empty for now
                    coverInput.value = '';
                    return 'cover_input_found';
                }

                // Find submit button
                const submitBtn = document.querySelector('input[type="submit"]');
                if (submitBtn) {
                    // Check if there's a 'skip' or 'next' option
                    const text = submitBtn.value || '';
                    if (text.includes('跳过') || text.includes('下一步') || text.includes('提交')) {
                        return 'can_submit';
                    }
                }

                return 'need_more_info';
            })()
        """)
        print(f"Submit check: {submit_result}")

        # Find and show all buttons
        buttons = eval_js("""
            (function() {
                return Array.from(document.querySelectorAll('input[type="submit"], button')).map(b => ({
                    tag: b.tagName,
                    type: b.type,
                    value: b.value,
                    text: b.textContent?.trim(),
                    name: b.name
                }));
            })()
        """)
        print(f"Buttons: {buttons}")

    else:
        print("Not on cover upload page")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)

if __name__ == '__main__':
    main()
