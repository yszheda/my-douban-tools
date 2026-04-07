#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug what happens after clicking 'no barcode' button
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
    print("Debug After Click 'No Barcode'")
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

    # Fill and click no-barcode button
    print("\n[Fill and click]")
    eval_js("""
        (function() {
            document.querySelector('input[name="p_title"]').value = 'Test No Barcode';
            document.querySelector('input[name="p_uid"]').value = 'Test Artist';
            document.querySelector('input[name="no_uid_submit"]').click();
        })()
    """)

    # Wait
    print("Waiting 5 seconds...")
    time.sleep(5)

    # Check for NEW fields after click
    print("\n[All Elements After Click]")
    all_elements = eval_js("""
        (function() {
            const result = {
                inputs: [],
                labels: [],
                errors: [],
                newSections: []
            };

            // All inputs
            document.querySelectorAll('input, textarea, select').forEach(el => {
                result.inputs.push({
                    tag: el.tagName,
                    type: el.type,
                    name: el.name,
                    id: el.id,
                    placeholder: el.placeholder,
                    value: el.value,
                    visible: el.offsetParent !== null
                });
            });

            // All labels
            document.querySelectorAll('label').forEach(el => {
                result.labels.push({
                    text: el.textContent?.trim(),
                    htmlFor: el.htmlFor
                });
            });

            // Error messages
            document.querySelectorAll('.error, .alert, .msg, .tip').forEach(el => {
                result.errors.push(el.textContent.trim());
            });

            // New sections that might appear
            document.querySelectorAll('fieldset, .form-item, .field-group, .section').forEach(el => {
                result.newSections.push({
                    tag: el.tagName,
                    class: el.className,
                    id: el.id,
                    html: el.innerHTML.substring(0, 300)
                });
            });

            return result;
        })()
    """)

    if all_elements:
        print("\n[Inputs]")
        for inp in all_elements.get('inputs', []):
            if inp.get('visible'):
                print(f"  {inp}")

        print("\n[Labels]")
        for lbl in all_elements.get('labels', []):
            if lbl.get('text'):
                print(f"  '{lbl['text']}' for='{lbl['htmlFor']}'")

        print("\n[Errors/Messages]")
        for err in all_elements.get('errors', []):
            print(f"  {err}")

        print("\n[Sections]")
        for sec in all_elements.get('newSections', []):
            print(f"  {sec.get('class', '')}: {sec.get('html', '')[:200]}...")

    # Check if form action changed
    print("\n[Form Action]")
    form_action = eval_js("""
        (function() {
            const form = document.querySelector('form');
            if (form) {
                return {
                    action: form.action,
                    method: form.method,
                    outerHTML: form.outerHTML.substring(0, 500)
                };
            }
            return null;
        })()
    """)
    print(f"  {form_action}")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)

if __name__ == '__main__':
    main()
