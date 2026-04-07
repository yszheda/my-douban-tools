#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze cover upload form and try to submit
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
    print("Analyze Cover Upload Form")
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

    # Get form info
    print("\n[Form Info]")
    form_info = eval_js("""
        (function() {
            const form = document.querySelector('form');
            if (!form) return null;

            return {
                action: form.action,
                method: form.method,
                outerHTML: form.outerHTML
            };
        })()
    """)

    if form_info:
        print(f"Action: {form_info.get('action')}")
        print(f"Method: {form_info.get('method')}")
        print(f"HTML: {form_info.get('outerHTML', '')[:1000]}...")

    # Check all hidden fields
    print("\n[Hidden Fields]")
    hidden_fields = eval_js("""
        (function() {
            const hidden = document.querySelectorAll('input[type="hidden"]');
            return Array.from(hidden).map(h => ({
                name: h.name,
                value: h.value
            }));
        })()
    """)
    for h in hidden_fields:
        print(f"  {h['name']}: {h['value']}")

    # Try submitting without a file (see what error we get)
    print("\n[Try Submit Without File]")
    submit_result = eval_js("""
        (function() {
            // Find the form and submit it without a file
            const form = document.querySelector('form');
            if (form) {
                // Remove the 'required' attribute if present
                const fileInput = document.querySelector('input[type="file"]');
                if (fileInput) {
                    fileInput.removeAttribute('required');
                }
                form.submit();
                return 'submitted';
            }
            return 'no form';
        })()
    """)
    print(f"Submit result: {submit_result}")

    time.sleep(5)

    # Check result
    print("\n[After Submit]")
    new_url = eval_js("location.href")
    new_title = eval_js("document.title")
    print(f"URL: {new_url}")
    print(f"Title: {new_title}")

    # Check for errors
    errors = eval_js("""
        (function() {
            const errs = document.querySelectorAll('.error, .alert');
            return Array.from(errs).map(e => e.textContent.trim());
        })()
    """)
    if errors:
        print(f"Errors: {errors}")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)

if __name__ == '__main__':
    main()
