#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban create album step 2 - detail form
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
    print("Debug Create Album Step 2 - Detail Form")
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

    # Navigate to create page and fill step 1
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
                titleField.value = 'Test Album Debug';
                titleField.dispatchEvent(new Event('input', { bubbles: true }));
            }

            if (artistField) {
                artistField.value = 'Test Artist';
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
    time.sleep(5)

    # Check current page
    print("\n[Step 2 Page Info]")
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Find ALL form fields on step 2
    print("\n[All Form Fields on Step 2]")
    fields = eval_js("""
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
                disabled: el.disabled,
                readonly: el.readOnly,
                required: el.required
            }));
        })()
    """)

    if fields:
        for f in fields:
            if f.get('visible') and not f.get('disabled'):
                print(f"  {f}")
    else:
        print("  No fields found")

    # Find all labels
    print("\n[All Labels]")
    labels = eval_js("""
        (function() {
            const all = document.querySelectorAll('label');
            return Array.from(all).map(l => ({
                text: l.textContent?.trim(),
                for: l.htmlFor,
                id: l.id
            }));
        })()
    """)

    if labels:
        for lbl in labels:
            if lbl.get('text'):
                print(f"  '{lbl['text']}' for='{lbl['for']}'")
    else:
        print("  No labels found")

    # Find submit button
    print("\n[Submit Button]")
    submit = eval_js("""
        (function() {
            const all = document.querySelectorAll('input[type="submit"], button[type="submit"], button');
            return Array.from(all).map(el => ({
                tag: el.tagName,
                type: el.type,
                name: el.name,
                value: el.value,
                text: el.textContent?.trim().substring(0, 30),
                id: el.id,
                class: el.className,
                visible: el.offsetParent !== null
            }));
        })()
    """)

    if submit:
        for s in submit:
            print(f"  {s}")
    else:
        print("  No submit button found")

    # Get full form HTML
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
        print(f"  {form_html[:2500]}...")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
