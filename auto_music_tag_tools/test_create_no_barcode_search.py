#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Try creating album WITHOUT entering barcode in search box
Just fill the detail form directly using 'add without barcode' button
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
    print("Create Album WITHOUT barcode in search box")
    print("Target: A Portrait of Giacomo Lauri-Volpi Vol. 1")
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
        'label': 'Gala',
        'country': 'Netherlands'
    }

    # Step 1: Navigate to create page
    print("\n[Step 1] Navigate to create page")
    create_url = "https://music.douban.com/new_subject?cat=1003"
    eval_js(f"window.location.href = '{create_url}';")
    wait_for_load(15)
    time.sleep(3)
    print(f"URL: {eval_js('location.href')}")

    # Step 2: ONLY fill title and artist, DO NOT touch search box
    print("\n[Step 2] Fill title and artist only")
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

    # Step 3: Click "add without barcode" button directly
    print("\n[Step 3] Click 'add without barcode' button")
    click_result = eval_js("""
        (function() {
            const btn = document.querySelector('input[name="no_uid_submit"]');
            if (btn) {
                btn.click();
                return 'clicked';
            }
            return 'not found';
        })()
    """)
    print(f"Click: {click_result}")
    time.sleep(5)

    # Step 4: Check if detail form appeared
    print("\n[Step 4] Check detail form")
    detail_fields = eval_js("""
        (function() {
            return {
                has_p27: !!document.querySelector('input[name="p_27"]'),
                has_p48: !!document.querySelector('input[name="p_48"]'),
                has_p51: !!document.querySelector('input[name="p_51"]'),
                has_p50: !!document.querySelector('input[name="p_50"]'),
                has_p152: !!document.querySelector('textarea[name="p_152_other"]')
            };
        })()
    """)
    print(f"Detail fields: {detail_fields}")

    if detail_fields and detail_fields.get('has_p27'):
        print("\n[Step 5] Fill detail form")

        # Fill all required fields
        fill_result = eval_js(f"""
            (function() {{
                const result = {{}};

                // 唱片名 p_27
                const p27 = document.querySelector('input[name="p_27"]');
                if (p27) {{
                    p27.value = {json.dumps(album['title'])};
                    result.p27 = 'ok';
                }}

                // 表演者 p_48
                const p48 = document.querySelector('input[name="p_48"]');
                if (p48) {{
                    p48.value = {json.dumps(album['artist'])};
                    result.p48 = 'ok';
                }}

                // 发行时间 p_51 (必填) - 格式：YYYY-MM-DD
                const p51 = document.querySelector('input[name="p_51"]');
                if (p51) {{
                    p51.value = '2013-01-01';
                    result.p51 = 'ok';
                }}

                // 出版者 p_50 (必填)
                const p50 = document.querySelector('input[name="p_50"]');
                if (p50) {{
                    p50.value = {json.dumps(album['label'])};
                    result.p50 = 'ok';
                }}

                // 参考资料 p_152_other (必填) - 需要包含参考链接
                const p152 = document.querySelector('textarea[name="p_152_other"]');
                if (p152) {{
                    p152.value = 'Barcode: 8712177053346\\nReference: https://www.discogs.com/release/2912345\\nThis album does not exist in Douban yet.';
                    result.p152 = 'ok';
                }}

                // 介质 p_49 - 选择 CD
                const p49 = document.querySelector('select[name="p_49"]');
                if (p49) {{
                    p49.value = '11';  // CD option value
                    result.p49 = 'ok';
                }}

                // 专辑类型 p_57 - 选择专辑
                const p57 = document.querySelector('select[name="p_57"]');
                if (p57) {{
                    p57.value = '1';  // 专辑 option value
                    result.p57 = 'ok';
                }}

                // 碟片数 p_55
                const p55 = document.querySelector('input[name="p_55"]');
                if (p55) {{
                    p55.value = '1';
                    result.p55 = 'ok';
                }}

                // ISRC p_54 (optional)
                // const p54 = document.querySelector('input[name="p_54"]');
                // if (p54) {{
                //     p54.value = '';
                //     result.p54 = 'ok';
                // }}

                return result;
            }})()
        """)
        print(f"Fill detail: {fill_result}")
        time.sleep(2)

        # Check for errors before submit
        print("\n[Step 6] Check for errors before submit")
        pre_errors = eval_js("""
            (function() {
                const errs = document.querySelectorAll('.error, .alert');
                return Array.from(errs).map(e => e.textContent.trim());
            })()
        """)
        if pre_errors:
            print(f"Pre-submit errors: {pre_errors}")

        # Step 7: Submit
        print("\n[Step 7] Submit detail form")
        submit = eval_js("""
            (function() {
                const btn = document.querySelector('input[name="detail_subject_submit"]');
                if (btn) {
                    btn.click();
                    return 'submitted';
                }
                return 'no submit button';
            })()
        """)
        print(f"Submit: {submit}")
        time.sleep(8)

        # Step 8: Check result
        print("\n[Step 8] Check final result")
        final_url = eval_js("location.href")
        final_title = eval_js("document.title")
        print(f"URL: {final_url}")
        print(f"Title: {final_title}")

        if final_url and '/subject/' in final_url:
            print("SUCCESS! Album created!")
        else:
            post_errors = eval_js("""
                (function() {
                    const errs = document.querySelectorAll('.error, .alert');
                    return Array.from(errs).map(e => e.textContent.trim());
                })()
            """)
            if post_errors:
                print(f"Errors: {post_errors}")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)

if __name__ == '__main__':
    main()
