#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete flow: Create album and capture cover upload page HTML
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
    print("Complete Flow - Create Album")
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

    # Album info
    album = {
        'title': 'A Portrait of Giacomo Lauri-Volpi Vol. 1',
        'artist': 'Giacomo Lauri-Volpi',
        'barcode': '8712177053346',
        'year': '2013',
        'label': 'Gala'
    }

    # Step 1: Navigate to create page
    print("\n[Step 1] Navigate to create page")
    create_url = "https://music.douban.com/new_subject?cat=1003"
    eval_js(f"window.location.href = '{create_url}';")
    wait_for_load(15)
    time.sleep(3)

    # Step 2: Fill title and artist
    print("[Step 2] Fill title and artist")
    eval_js(f"""
        (function() {{
            const title = document.querySelector('input[name="p_title"]');
            const artist = document.querySelector('input[name="p_uid"]');
            if (title) {{
                title.value = {json.dumps(album['title'])};
                title.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
            if (artist) {{
                artist.value = {json.dumps(album['artist'])};
                artist.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }})()
    """)
    time.sleep(2)

    # Step 3: Click "add without barcode"
    print("[Step 3] Click 'add without barcode'")
    eval_js("""
        (function() {
            const btn = document.querySelector('input[name="no_uid_submit"]');
            if (btn) btn.click();
        })()
    """)
    time.sleep(5)

    # Step 4: Fill detail form
    print("[Step 4] Fill detail form")
    eval_js(f"""
        (function() {{
            const p27 = document.querySelector('input[name="p_27"]');
            const p48 = document.querySelector('input[name="p_48"]');
            const p51 = document.querySelector('input[name="p_51"]');
            const p50 = document.querySelector('input[name="p_50"]');
            const p152 = document.querySelector('textarea[name="p_152_other"]');
            const p55 = document.querySelector('input[name="p_55"]');

            if (p27) p27.value = {json.dumps(album['title'])};
            if (p48) p48.value = {json.dumps(album['artist'])};
            if (p51) p51.value = '2013-01-01';
            if (p50) p50.value = {json.dumps(album['label'])};
            if (p152) p152.value = 'Barcode: 8712177053346\\nRef: https://www.discogs.com/release/2912345';
            if (p55) p55.value = '1';

            // Select CD for medium (p_49)
            const p49 = document.querySelector('select[name="p_49"]');
            if (p49) p49.value = '11';

            // Select '专辑' for type (p_57)
            const p57 = document.querySelector('select[name="p_57"]');
            if (p57) p57.value = '1';
        }})()
    """)
    time.sleep(2)

    # Step 5: Submit detail form
    print("[Step 5] Submit detail form")
    eval_js("""
        (function() {
            const btn = document.querySelector('input[name="detail_subject_submit"]');
            if (btn) btn.click();
        })()
    """)
    time.sleep(8)

    # Step 6: Capture cover upload page
    print("\n[Step 6] Capture cover upload page")
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Find cover upload form
    print("\n[Cover Upload Form]")
    form_info = eval_js("""
        (function() {
            const forms = document.querySelectorAll('form');
            const result = [];
            forms.forEach((f, i) => {
                const inputs = Array.from(f.querySelectorAll('input')).map(inp => ({
                    name: inp.name,
                    type: inp.type,
                    value: inp.value
                }));
                if (inputs.some(i => i.name === 'picfile' || i.name === 'img_submit')) {
                    result.push({
                        index: i,
                        action: f.action,
                        method: f.method,
                        id: f.id,
                        class: f.className,
                        inputs: inputs
                    });
                }
            });
            return result;
        })()
    """)

    if form_info and len(form_info) > 0:
        print(f"Found {len(form_info)} cover upload form(s):")
        for form in form_info:
            print(f"\n--- Form {form['index']} ---")
            print(f"Action: {form['action']}")
            print(f"Method: {form['method']}")
            print("Inputs:")
            for inp in form['inputs']:
                print(f"  {inp['type']}: name={inp['name']}, value={inp['value']}")
    else:
        print("No cover upload form found")

    # Save HTML
    print("\n[Save HTML]")
    html = eval_js("document.documentElement.outerHTML")
    if html:
        with open('debug_cover_upload_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Saved HTML to debug_cover_upload_page.html ({len(html)} bytes)")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)

if __name__ == '__main__':
    main()
