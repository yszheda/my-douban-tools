#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug why album creation fails - check for validation errors
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
    print("Debug Album Creation Failure")
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

    # Fill with failing album info (Fabienne Jacquinot)
    album = {
        'title': 'A Tribute to Fabienne Jacquinot',
        'artist': 'Fabienne Jacquinot',
        'label': 'Green Door',
        'year': '2013-01-01'
    }

    print(f"\n[Fill Step 1]")
    eval_js(f"""
        (function() {{
            document.querySelector('input[name="p_title"]').value = {json.dumps(album['title'])};
            document.querySelector('input[name="p_uid"]').value = {json.dumps(album['artist'])};
        }})()
    """)
    time.sleep(2)

    # Click no-barcode button
    print(f"[Click 'add without barcode']")
    eval_js("""
        (function() {
            document.querySelector('input[name="no_uid_submit"]').click();
        })()
    """)
    time.sleep(5)

    # Check if detail form appeared
    print(f"\n[Check Detail Form]")
    detail_fields = eval_js("""
        (function() {
            return {
                has_p27: !!document.querySelector('input[name="p_27"]'),
                has_p48: !!document.querySelector('input[name="p_48"]'),
                has_p51: !!document.querySelector('input[name="p_51"]'),
                has_p50: !!document.querySelector('input[name="p_50"]'),
                has_p152: !!document.querySelector('textarea[name="p_152_other"]'),
                has_p49: !!document.querySelector('select[name="p_49"]'),
                has_p57: !!document.querySelector('select[name="p_57"]')
            };
        })()
    """)
    print(f"Detail fields: {detail_fields}")

    # Fill detail form
    print(f"\n[Fill Detail Form]")
    fill_result = eval_js(f"""
        (function() {{
            const result = {{}};

            const p27 = document.querySelector('input[name="p_27"]');
            if (p27) {{ p27.value = {json.dumps(album['title'])}; result.p27 = 'ok'; }}

            const p48 = document.querySelector('input[name="p_48"]');
            if (p48) {{ p48.value = {json.dumps(album['artist'])}; result.p48 = 'ok'; }}

            const p51 = document.querySelector('input[name="p_51"]');
            if (p51) {{ p51.value = '{album['year']}'; result.p51 = 'ok'; }}

            const p50 = document.querySelector('input[name="p_50"]');
            if (p50) {{ p50.value = {json.dumps(album['label'])}; result.p50 = 'ok'; }}

            const p152 = document.querySelector('textarea[name="p_152_other"]');
            if (p152) {{ p152.value = 'Barcode: N/A\\nReference: https://www.discogs.com/search?q=Fabienne+Jacquinot'; result.p152 = 'ok'; }}

            const p49 = document.querySelector('select[name="p_49"]');
            if (p49) {{ p49.value = '11'; result.p49 = 'selected'; }}

            const p57 = document.querySelector('select[name="p_57"]');
            if (p57) {{ p57.value = '1'; result.p57 = 'selected'; }}

            return result;
        }})()
    """)
    print(f"Fill result: {fill_result}")
    time.sleep(2)

    # Check for errors BEFORE submit
    print(f"\n[Check Errors Before Submit]")
    pre_errors = eval_js("""
        (function() {
            const errs = document.querySelectorAll('.error, .alert');
            return Array.from(errs).map(e => e.textContent.trim());
        })()
    """)
    if pre_errors:
        print(f"Pre-submit errors: {pre_errors}")
    else:
        print("No pre-submit errors")

    # Check all field values
    print(f"\n[Field Values Before Submit]")
    field_values = eval_js("""
        (function() {
            return {
                p27: document.querySelector('input[name="p_27"]')?.value,
                p48: document.querySelector('input[name="p_48"]')?.value,
                p51: document.querySelector('input[name="p_51"]')?.value,
                p50: document.querySelector('input[name="p_50"]')?.value,
                p152: document.querySelector('textarea[name="p_152_other"]')?.value?.substring(0, 50),
                p49: document.querySelector('select[name="p_49"]')?.value,
                p57: document.querySelector('select[name="p_57"]')?.value
            };
        })()
    """)
    print(f"Field values: {field_values}")

    # Submit
    print(f"\n[Submit]")
    submit_result = eval_js("""
        (function() {
            const btn = document.querySelector('input[name="detail_subject_submit"]');
            if (btn) {
                btn.click();
                return 'submitted';
            }
            return 'not found';
        })()
    """)
    print(f"Submit result: {submit_result}")
    time.sleep(8)

    # Check page after submit
    print(f"\n[After Submit]")
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Check for errors AFTER submit
    print(f"\n[Errors After Submit]")
    post_errors = eval_js("""
        (function() {
            const errs = document.querySelectorAll('.error, .alert');
            return Array.from(errs).map(e => e.textContent.trim());
        })()
    """)
    if post_errors:
        print(f"Post-submit errors: {post_errors}")
    else:
        print("No post-submit errors")

    # Get page content
    print(f"\n[Page Content]")
    content = eval_js("document.body.innerText")
    if content:
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        for line in lines[:30]:
            print(f"  {line}")

    page_ws.close()
    print(f"\n{'='*60}")
    print("Done")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
