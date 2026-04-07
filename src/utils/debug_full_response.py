#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban - Check full response structure
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
    print("Debug Full Response Structure")
    print("="*60)

    # Get pages
    pages = requests.get(f"{debug_url}/json/list", timeout=5).json()
    douban_page = None
    for page in pages:
        if 'douban.com' in page.get('url', ''):
            douban_page = page
            break

    if not douban_page:
        print("No Douban page found")
        sys.exit(1)

    print(f"Found Douban page: {douban_page.get('id')}")

    # Connect to page
    page_ws = websocket.create_connection(douban_page.get('webSocketDebuggerUrl'), timeout=10)
    print("Connected!")

    # Enable domains
    page_ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
    page_ws.send(json.dumps({"id": 2, "method": "Runtime.enable"}))
    time.sleep(2)

    # Drain any pending events
    page_ws.settimeout(0.5)
    while True:
        try:
            msg = json.loads(page_ws.recv())
            print(f"Event: {msg.get('method', 'unknown')}")
        except:
            break

    # Execute JavaScript and print FULL response
    print("\n[Executing document.documentElement]")
    cmd = {
        "id": 3,
        "method": "Runtime.evaluate",
        "params": {
            "expression": "document.documentElement",
            "returnByValue": False  # Try without returnByValue
        }
    }
    page_ws.send(json.dumps(cmd))

    # Wait for response
    page_ws.settimeout(5)
    while True:
        try:
            resp = json.loads(page_ws.recv())
            print(f"\nFull response:")
            print(json.dumps(resp, indent=2, default=str)[:2000])

            if resp.get('id') == cmd['id']:
                break
        except websocket.WebSocketTimeoutException:
            print("Timeout")
            break
        except Exception as e:
            print(f"Error: {e}")
            break

    # Try with returnByValue=true for a simple string
    print("\n\n[Executing 'hello' string]")
    cmd2 = {
        "id": 4,
        "method": "Runtime.evaluate",
        "params": {
            "expression": "'hello world'",
            "returnByValue": True
        }
    }
    page_ws.send(json.dumps(cmd2))

    page_ws.settimeout(5)
    while True:
        try:
            resp = json.loads(page_ws.recv())
            print(f"\nFull response:")
            print(json.dumps(resp, indent=2, default=str))

            if resp.get('id') == cmd2['id']:
                break
        except:
            break

    # Try accessing the execution context
    print("\n\n[Trying with explicit contextId]")
    # First, get context info
    cmd3 = {
        "id": 5,
        "method": "Runtime.evaluate",
        "params": {
            "expression": "document.title",
            "returnByValue": True,
            "includeCommandLineAPI": True
        }
    }
    page_ws.send(json.dumps(cmd3))

    page_ws.settimeout(5)
    while True:
        try:
            resp = json.loads(page_ws.recv())
            print(f"\nResponse for document.title:")
            print(json.dumps(resp, indent=2, default=str)[:1500])

            if resp.get('id') == cmd3['id']:
                # Extract the value
                if 'result' in resp:
                    result = resp['result']
                    if 'value' in result:
                        print(f"\nValue: {result['value']}")
                    elif 'objectId' in result:
                        print(f"\nObjectId: {result['objectId']}")
                        # Try to get properties
                        cmd_props = {
                            "id": 6,
                            "method": "Runtime.getProperties",
                            "params": {
                                "objectId": result['objectId'],
                                "ownProperties": True
                            }
                        }
                        page_ws.send(json.dumps(cmd_props))
                        page_ws.settimeout(3)
                        while True:
                            try:
                                props_resp = json.loads(page_ws.recv())
                                print(f"\nProperties response:")
                                print(json.dumps(props_resp, indent=2, default=str)[:1000])
                                break
                            except:
                                break
                break
        except:
            break

    page_ws.close()
    print("\n" + "="*60)
    print("Done")
    print("="*60)


if __name__ == '__main__':
    main()
