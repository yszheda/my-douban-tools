#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test click 'add album without barcode' button directly
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
    print("Test Add Album Without Barcode")
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

    # Fill title and artist ONLY, click 'add without barcode'
    print("\n[Fill form and click 'no barcode' button]")
    result = eval_js("""
        (function() {
            // Fill title
            const titleField = document.querySelector('input[name="p_title"]');
            if (titleField) {
                titleField.value = 'Test No Barcode Album';
                titleField.dispatchEvent(new Event('input', { bubbles: true }));
            }

            // Fill artist
            const artistField = document.querySelector('input[name="p_uid"]');
            if (artistField) {
                artistField.value = 'Test Artist No Barcode';
                artistField.dispatchEvent(new Event('input', { bubbles: true }));
            }

            // Click 'add without barcode' button
            const noBarcodeBtn = document.querySelector('input[name="no_uid_submit"]');
            if (noBarcodeBtn) {
                noBarcodeBtn.click();
                return 'clicked_no_barcode';
            }

            return 'no_button_found';
        })()
    """)

    print(f"Result: {result}")

    # Wait for navigation
    print("\nWaiting for page navigation...")
    time.sleep(8)

    # Check result
    print("\n[Result Page]")
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Check for error messages
    error = eval_js("""
        (function() {
            const err = document.querySelector('.error, .alert');
            if (err) {
                return err.textContent.trim();
            }
            return null;
        })()
    """)

    if error:
        print(f"Error: {error}")

    # Check if we're on a subject page
    if url and '/subject/' in url:
        print(f"SUCCESS! Created album: {url}")
    else:
        print("Album creation may require additional steps")

    # Get current form state
    print("\n[Current Form State]")
    form_state = eval_js("""
        (function() {
            return {
                title: document.querySelector('input[name="p_title"]')?.value,
                artist: document.querySelector('input[name="p_uid"]')?.value,
                url: window.location.href
            };
        })()
    """)
    print(f"  {form_state}")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)

if __name__ == '__main__':
    main()
