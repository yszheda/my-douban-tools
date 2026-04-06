#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban create album - Check for errors and messages
"""

import json
import time
import sys
import os
import requests
import websocket

# Set UTF-8 encoding for console output
sys.stdout.reconfigure(encoding='utf-8')


def main():
    debug_port = 9222
    debug_url = f"http://127.0.0.1:{debug_port}"

    print("="*60)
    print("Debug Create Album - Check for Errors")
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

    # Fill step 1
    print("\n[Filling Step 1]")
    step1_result = eval_js("""
        (function() {
            const titleField = document.querySelector('input[name="p_title"]');
            const artistField = document.querySelector('input[name="p_uid"]');

            if (titleField) {
                titleField.value = 'Test Album Debug Step 2';
                titleField.dispatchEvent(new Event('input', { bubbles: true }));
            }

            if (artistField) {
                artistField.value = 'Test Artist Debug';
                artistField.dispatchEvent(new Event('input', { bubbles: true }));
            }

            // Click "Next" button
            const nextBtn = document.querySelector('input[name="subject_submit"]');
            if (nextBtn) {
                nextBtn.click();
                return 'clicked_next';
            }
            return 'no_next_button';
        })()
    """)

    print(f"Step 1 result: {step1_result}")

    # Wait for step 2
    print("\nWaiting for step 2 page...")
    time.sleep(8)

    # Check current page
    print("\n[Step 2 Page Info]")
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Check for error messages
    print("\n[Error Messages]")
    errors = eval_js("""
        (function() {
            const msgs = [];
            // Look for error/warning messages
            const selectors = ['.error', '.warning', '.alert', '.msg', '.message', '.error-message', '.tip', '.notice'];
            selectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => {
                    msgs.push({
                        class: el.className,
                        text: el.textContent?.trim(),
                        id: el.id
                    });
                });
            });
            return msgs;
        })()
    """)

    if errors and len(errors) > 0:
        for e in errors:
            print(f"  {e}")
    else:
        print("  No error messages found")

    # Check body text for any messages
    print("\n[Body Text]")
    try:
        body_text = eval_js("document.body.innerText")
        if body_text:
            # Print first 500 chars, encode to avoid console errors
            print(f"  Body text (first 500): {body_text[:500].encode('gbk', 'ignore').decode('gbk')}")
    except Exception as e:
        print(f"  Could not read body text: {e}")

    # Check if p_title and p_uid are still visible (means we didn't advance)
    print("\n[Field Visibility]")
    field_visibility = eval_js("""
        (function() {
            const titleField = document.querySelector('input[name="p_title"]');
            const artistField = document.querySelector('input[name="p_uid"]');

            return {
                titleVisible: titleField ? titleField.offsetParent !== null : 'not found',
                artistVisible: artistField ? artistField.offsetParent !== null : 'not found',
                titleValue: titleField ? titleField.value : 'not found',
                artistValue: artistField ? artistField.value : 'not found'
            };
        })()
    """)

    print(f"  {field_visibility}")

    # Check for any new fields that might appear on step 2
    print("\n[All Inputs After Step 2]")
    all_inputs = eval_js("""
        (function() {
            const all = document.querySelectorAll('input, textarea, select');
            return Array.from(all).map(el => ({
                tag: el.tagName,
                type: el.type,
                name: el.name,
                id: el.id,
                value: el.value,
                visible: el.offsetParent !== null
            }));
        })()
    """)

    if all_inputs:
        for inp in all_inputs:
            if inp.get('visible'):
                print(f"  {inp}")
    else:
        print("  No inputs found")

    # Get full body HTML
    print("\n[Body HTML]")
    body_html = eval_js("document.body.innerHTML")
    if body_html:
        print(f"  {body_html[:3000]}...")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
