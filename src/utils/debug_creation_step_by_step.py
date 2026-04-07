#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban album creation - Step by step with detailed feedback
Target: "A Portrait of Giacomo Lauri-Volpi Vol. 1" barcode 8712177053346
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
    print("Debug Album Creation - Step by Step")
    print("Target: A Portrait of Giacomo Lauri-Volpi Vol. 1")
    print("Barcode: 8712177053346")
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
        'country': '荷兰'
    }

    # Step 1: Navigate to create page
    print("\n" + "="*60)
    print("Step 1: Navigate to create page")
    print("="*60)
    create_url = "https://music.douban.com/new_subject?cat=1003"
    eval_js(f"window.location.href = '{create_url}';")
    wait_for_load(15)
    time.sleep(3)

    print(f"Current URL: {eval_js('location.href')}")
    print(f"Page Title: {eval_js('document.title')}")

    # Step 2: Fill in search box with barcode
    print("\n" + "="*60)
    print("Step 2: Fill search box with barcode")
    print("="*60)
    search_result = eval_js(f"""
        (function() {{
            const searchInput = document.querySelector('input[name="search_text"], #inp-query');
            if (searchInput) {{
                searchInput.value = {json.dumps(album['barcode'])};
                searchInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return 'filled';
            }}
            return 'not found';
        }})()
    """)
    print(f"Search box fill: {search_result}")
    print(f"Search box value: {eval_js('document.querySelector(\"#inp-query\").value')}")
    time.sleep(2)

    # Step 3: Fill title and artist
    print("\n" + "="*60)
    print("Step 3: Fill title and artist")
    print("="*60)
    fill_result = eval_js(f"""
        (function() {{
            const result = {{}};

            const titleField = document.querySelector('input[name="p_title"], #p_title');
            if (titleField) {{
                titleField.value = {json.dumps(album['title'])};
                titleField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                result.title = 'filled';
            }} else {{
                result.title = 'not found';
            }}

            const artistField = document.querySelector('input[name="p_uid"], #uid');
            if (artistField) {{
                artistField.value = {json.dumps(album['artist'])};
                artistField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                result.artist = 'filled';
            }} else {{
                result.artist = 'not found';
            }}

            return result;
        }})()
    """)
    print(f"Fill result: {fill_result}")
    time.sleep(2)

    # Step 4: Check available buttons
    print("\n" + "="*60)
    print("Step 4: Check available buttons")
    print("="*60)
    buttons = eval_js("""
        (function() {
            const btns = document.querySelectorAll('input[type="submit"]');
            return Array.from(btns).map(b => ({
                name: b.name,
                value: b.value,
                visible: b.offsetParent !== null
            }));
        })()
    """)
    print(f"Buttons: {buttons}")
    time.sleep(2)

    # Step 5: Click "Next" button (subject_submit)
    print("\n" + "="*60)
    print("Step 5: Click 'Next' button")
    print("="*60)
    click_result = eval_js("""
        (function() {
            const nextBtn = document.querySelector('input[name="subject_submit"]');
            if (nextBtn) {
                nextBtn.click();
                return 'clicked_next';
            }
            return 'button not found';
        })()
    """)
    print(f"Click result: {click_result}")
    time.sleep(8)

    # Step 6: Check page state after click
    print("\n" + "="*60)
    print("Step 6: Check page state after click")
    print("="*60)
    print(f"Current URL: {eval_js('location.href')}")
    print(f"Page Title: {eval_js('document.title')}")

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
        print(f"Error message: {error}")
    else:
        print("No error messages")

    # Step 7: Check if detail form appeared
    print("\n" + "="*60)
    print("Step 7: Check for detail form fields")
    print("="*60)
    detail_fields = eval_js("""
        (function() {
            const fields = {
                has_p27: !!document.querySelector('input[name="p_27"]'),  // 唱片名
                has_p48: !!document.querySelector('input[name="p_48"]'),  // 表演者
                has_p51: !!document.querySelector('input[name="p_51"]'),  // 发行时间
                has_p50: !!document.querySelector('input[name="p_50"]'),  // 出版者
                has_p152: !!document.querySelector('textarea[name="p_152_other"]'),  // 参考资料
                has_detail_submit: !!document.querySelector('input[name="detail_subject_submit"]')  // 下一步按钮
            };
            return fields;
        })()
    """)
    print(f"Detail form fields: {detail_fields}")

    # If detail form exists, fill it
    if detail_fields and detail_fields.get('has_p27'):
        print("\n" + "="*60)
        print("Step 8: Fill detail form")
        print("="*60)

        fill_detail = eval_js(f"""
            (function() {{
                const result = {{}};

                // 唱片名 (p_27)
                const p27 = document.querySelector('input[name="p_27"]');
                if (p27) {{
                    p27.value = {json.dumps(album['title'])};
                    p27.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    result.p27 = 'filled';
                }}

                // 表演者 (p_48)
                const p48 = document.querySelector('input[name="p_48"]');
                if (p48) {{
                    p48.value = {json.dumps(album['artist'])};
                    p48.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    result.p48 = 'filled';
                }}

                // 发行时间 (p_51) - 必填
                const p51 = document.querySelector('input[name="p_51"]');
                if (p51) {{
                    p51.value = {json.dumps(album['year'])};
                    p51.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    result.p51 = 'filled';
                }}

                // 出版者 (p_50) - 必填
                const p50 = document.querySelector('input[name="p_50"]');
                if (p50) {{
                    p50.value = {json.dumps(album['label'])};
                    p50.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    result.p50 = 'filled';
                }}

                // 参考资料 (p_152_other) - 必填
                const p152 = document.querySelector('textarea[name="p_152_other"]');
                if (p152) {{
                    p152.value = 'Barcode: ' + {json.dumps(album['barcode'])};
                    p152.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    result.p152 = 'filled';
                }}

                return result;
            }})()
        """)
        print(f"Detail fill result: {fill_detail}")
        time.sleep(3)

        # Check for error messages before submit
        print("\n" + "="*60)
        print("Step 9: Check for validation errors")
        print("="*60)
        pre_error = eval_js("""
            (function() {
                const errs = document.querySelectorAll('.error, .alert');
                return Array.from(errs).map(e => e.textContent.trim());
            })()
        """)
        if pre_error:
            print(f"Pre-submit errors: {pre_error}")

        # Step 10: Submit detail form
        print("\n" + "="*60)
        print("Step 10: Submit detail form")
        print("="*60)
        submit_result = eval_js("""
            (function() {
                const submitBtn = document.querySelector('input[name="detail_subject_submit"]');
                if (submitBtn) {
                    submitBtn.click();
                    return 'clicked_submit';
                }
                return 'submit button not found';
            })()
        """)
        print(f"Submit result: {submit_result}")
        time.sleep(8)

        # Step 11: Check final result
        print("\n" + "="*60)
        print("Step 11: Check final result")
        print("="*60)
        final_url = eval_js("location.href")
        final_title = eval_js("document.title")
        print(f"Final URL: {final_url}")
        print(f"Final Title: {final_title}")

        if final_url and '/subject/' in final_url:
            print("SUCCESS! Album created!")
        else:
            post_error = eval_js("""
                (function() {
                    const errs = document.querySelectorAll('.error, .alert');
                    return Array.from(errs).map(e => e.textContent.trim());
                })()
            """)
            if post_error:
                print(f"Post-submit errors: {post_error}")

    page_ws.close()
    print("\n" + "="*60)
    print("Debug complete")
    print("="*60)

if __name__ == '__main__':
    main()
