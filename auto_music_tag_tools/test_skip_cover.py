#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Try to complete album creation without uploading cover
or find the created album URL
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
    print("Complete Album Creation - Skip Cover Upload")
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

    # Get current page info
    print("\n[Current Page]")
    url = eval_js("location.href")
    title = eval_js("document.title")
    print(f"URL: {url}")
    print(f"Title: {title}")

    # Get nuid value (created album ID)
    nuid = eval_js("""
        (function() {
            const nuidInput = document.querySelector('input[name="nuid"]');
            if (nuidInput) {
                return nuidInput.value;
            }
            return null;
        })()
    """)
    print(f"NUID (Album ID): {nuid}")

    # If we have the album ID, navigate to it
    if nuid:
        album_url = f"https://music.douban.com/subject/{nuid}/"
        print(f"\n[Navigate to Album Page]")
        print(f"Album URL: {album_url}")
        eval_js(f"window.location.href = '{album_url}';")
        wait_for_load(15)
        time.sleep(3)

        # Check if we're on the album page
        new_url = eval_js("location.href")
        new_title = eval_js("document.title")
        print(f"New URL: {new_url}")
        print(f"New Title: {new_title}")

        if f"/subject/{nuid}/" in new_url:
            print(f"\nSUCCESS! Album created: {new_url}")
        else:
            print("May need to complete cover upload first")

    # Check for skip option
    print("\n[Check for Skip Option]")
    skip_options = eval_js("""
        (function() {
            const links = document.querySelectorAll('a[href]');
            const buttons = document.querySelectorAll('input[type="submit"], button');
            const result = [];

            links.forEach(l => {
                const text = l.textContent?.trim();
                if (text && (text.includes('跳过') || text.includes('skip') || text.includes('下一步'))) {
                    result.push({
                        type: 'link',
                        text: text,
                        href: l.href
                    });
                }
            });

            buttons.forEach(b => {
                const text = (b.value || b.textContent)?.trim();
                if (text && (text.includes('跳过') || text.includes('skip') || text.includes('下一步'))) {
                    result.push({
                        type: 'button',
                        text: text,
                        value: b.value
                    });
                }
            });

            return result;
        })()
    """)
    print(f"Skip options: {skip_options}")

    # Get full page HTML for analysis
    print("\n[Page HTML Sample]")
    html_sample = eval_js("document.body.innerHTML.substring(0, 2000)")
    if html_sample:
        print(f"  {html_sample[:500]}...")

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)

if __name__ == '__main__':
    main()
