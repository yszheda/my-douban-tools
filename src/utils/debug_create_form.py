#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban create new album form structure
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
    print("Debug Douban Create Album Form")
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

    # Check for security check
    print("\n[Security Check]")
    is_security = eval_js("document.body.innerText.includes('安全') || document.body.innerText.includes('验证')")
    print(f"Is security page: {is_security}")

    # Find all form fields
    print("\n[All Form Fields]")
    fields = eval_js("""
        (function() {
            const inputs = document.querySelectorAll('input, textarea, select');
            return Array.from(inputs).map(inp => ({
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

    if fields:
        for f in fields:
            if f.get('visible') and not f.get('disabled'):
                print(f"  {f['tag']} name={f.get('name','')} id={f.get('id','')} type={f.get('type','')} placeholder={f.get('placeholder','')}")
    else:
        print("  No form fields found")

    # Find all labels
    print("\n[All Labels]")
    labels = eval_js("""
        (function() {
            const lbls = document.querySelectorAll('label');
            return Array.from(lbls).map(l => ({
                text: l.textContent?.trim(),
                for: l.htmlFor,
                id: l.id
            }));
        })()
    """)

    if labels:
        for lbl in labels:
            print(f"  '{lbl['text']}' for='{lbl['for']}'")
    else:
        print("  No labels found")

    # Find submit button
    print("\n[Submit Button]")
    submit = eval_js("""
        (function() {
            const btns = document.querySelectorAll('input[type="submit"], button[type="submit"], button:contains("提交"), button:contains("确定")');
            return Array.from(btns).map(b => ({
                tag: b.tagName,
                type: b.type,
                value: b.value,
                text: b.textContent?.trim(),
                id: b.id,
                class: b.className
            }));
        })()
    """)

    if submit:
        for s in submit:
            print(f"  {s}")
    else:
        print("  No submit button found")

    # Get full HTML of form area
    print("\n[Form HTML]")
    form_html = eval_js("""
        (function() {
            const form = document.querySelector('form');
            if (form) {
                return form.outerHTML.substring(0, 2000);
            }
            // Try to find main content
            const main = document.querySelector('#content, .main, .wrapper');
            if (main) {
                return main.outerHTML.substring(0, 2000);
            }
            return document.body.innerHTML.substring(0, 2000);
        })()
    """)

    if form_html:
        print(f"  {form_html[:1500]}...")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
