#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Debug Douban - Basic connection test
"""

import json
import time
import sys

try:
    import websocket
    import requests
except ImportError:
    print("Need to install: pip install websocket-client requests")
    sys.exit(1)


def main():
    debug_port = 9222
    debug_url = f"http://127.0.0.1:{debug_port}"

    print("="*60)
    print("Simple Douban Debug")
    print("="*60)

    # Step 1: Get browser WebSocket URL
    print("\n[1] Getting browser WebSocket URL...")
    try:
        resp = requests.get(f"{debug_url}/json/version", timeout=5)
        data = resp.json()
        print(f"  Browser: {data.get('Browser', '')[:50]}")
        browser_ws = data.get("webSocketDebuggerUrl")
        print(f"  WebSocket URL: {browser_ws[:80] if browser_ws else 'None'}...")
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    # Step 2: Connect to browser
    print("\n[2] Connecting to browser WebSocket...")
    try:
        ws = websocket.create_connection(browser_ws, timeout=10)
        print("  Connected!")
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    # Step 3: Get list of pages
    print("\n[3] Getting page list...")
    try:
        pages_resp = requests.get(f"{debug_url}/json/list", timeout=5)
        pages = pages_resp.json()
        print(f"  Found {len(pages)} pages")

        douban_page = None
        for page in pages:
            url = page.get('url', '')
            if 'douban.com' in url:
                douban_page = page
                print(f"  Found Douban page:")
                print(f"    ID: {page.get('id')}")
                print(f"    Title: {page.get('title', '')[:50]}")
                print(f"    URL: {url[:80]}")
                break

        if not douban_page:
            print("  No Douban page found!")
            ws.close()
            return

        page_ws_url = douban_page.get('webSocketDebuggerUrl')
        if not page_ws_url:
            print("  No WebSocket URL for this page!")
            ws.close()
            return

    except Exception as e:
        print(f"  ERROR: {e}")
        ws.close()
        return

    # Step 4: Connect to page
    print("\n[4] Connecting to page WebSocket...")
    try:
        page_ws = websocket.create_connection(page_ws_url, timeout=10)
        print("  Connected to page!")
    except Exception as e:
        print(f"  ERROR: {e}")
        ws.close()
        return

    # Step 5: Enable Runtime domain
    print("\n[5] Enabling Runtime domain...")
    try:
        page_ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.enable"
        }))
        resp = json.loads(page_ws.recv())
        print(f"  Response: {resp}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Step 6: Execute simple JavaScript
    print("\n[6] Executing simple JavaScript...")
    try:
        page_ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "document.title",
                "returnByValue": True
            }
        }))
        resp = json.loads(page_ws.recv())
        print(f"  Raw response: {resp}")

        if 'result' in resp:
            title = resp['result'].get('value')
            print(f"  Page title: {title[:80] if title else 'None'}")
        else:
            print("  No result in response!")

    except Exception as e:
        print(f"  ERROR: {e}")

    # Step 7: Check URL
    print("\n[7] Checking current URL...")
    try:
        page_ws.send(json.dumps({
            "id": 3,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "location.href",
                "returnByValue": True
            }
        }))
        resp = json.loads(page_ws.recv())
        if 'result' in resp:
            url = resp['result'].get('value')
            print(f"  Current URL: {url[:80] if url else 'None'}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Step 8: Check for search input
    print("\n[8] Looking for search input...")
    try:
        page_ws.send(json.dumps({
            "id": 4,
            "method": "Runtime.evaluate",
            "params": {
                "expression": """
                    (function() {
                        const input = document.querySelector('input[name="q"], input[type="search"]');
                        return input ? {
                            found: true,
                            type: input.type,
                            name: input.name,
                            placeholder: input.placeholder
                        } : { found: false };
                    })()
                """,
                "returnByValue": True
            }
        }))
        resp = json.loads(page_ws.recv())
        print(f"  Raw response: {resp}")

        if 'result' in resp:
            search_info = resp['result'].get('value')
            if search_info:
                if search_info.get('found'):
                    print(f"  Found search input!")
                    print(f"    Type: {search_info.get('type')}")
                    print(f"    Name: {search_info.get('name')}")
                    print(f"    Placeholder: {search_info.get('placeholder')}")
                else:
                    print("  Search input not found!")
        else:
            print("  No result in response!")

    except Exception as e:
        print(f"  ERROR: {e}")

    # Cleanup
    page_ws.close()
    ws.close()

    print("\n" + "="*60)
    print("Debug complete")
    print("="*60)


if __name__ == '__main__':
    main()
