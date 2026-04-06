#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban Connection - Check if page is ready
"""

import json
import time
import sys
import requests
import websocket


class ConnectionDebugBot:
    def __init__(self, debug_port=9222):
        self.debug_url = f"http://127.0.0.1:{debug_port}"
        self.ws = None
        self.page_ws = None
        self.cmd_id = 1

    def connect(self):
        try:
            resp = requests.get(f"{self.debug_url}/json/version", timeout=5)
            browser_ws = resp.json().get("webSocketDebuggerUrl")
            if not browser_ws:
                return False
            self.ws = websocket.create_connection(browser_ws, timeout=10)
            return True
        except Exception as e:
            print(f"Connect error: {e}")
            return False

    def find_douban_page(self):
        try:
            pages = requests.get(f"{self.debug_url}/json/list", timeout=5).json()
            print(f"Found {len(pages)} pages")
            for i, page in enumerate(pages):
                print(f"  [{i}] {page.get('title', 'No title')[:50]}")
                print(f"      URL: {page.get('url', 'No URL')[:80]}")

            for page in pages:
                if 'douban.com' in page.get('url', ''):
                    self.page_id = page.get('id')
                    page_ws_url = page.get('webSocketDebuggerUrl')
                    print(f"\nConnecting to page {self.page_id}")
                    print(f"  WebSocket URL: {page_ws_url[:60]}...")
                    if page_ws_url:
                        self.page_ws = websocket.create_connection(page_ws_url, timeout=10)
                        print("  WebSocket connected!")
                        self._send_command("Page.enable")
                        self._send_command("Runtime.enable")
                        time.sleep(2)
                        return True
            return False
        except Exception as e:
            print(f"Find page error: {e}")
            return False

    def _send_command(self, method, params=None):
        if not self.page_ws:
            return None

        cmd = {
            "id": self.cmd_id,
            "method": method,
            "params": params or {}
        }
        self.cmd_id += 1

        print(f"  Sending: {method} (id={cmd['id']})")
        self.page_ws.send(json.dumps(cmd))

        # Wait for response with timeout
        start = time.time()
        while time.time() - start < 5:
            try:
                self.page_ws.settimeout(1)
                resp = json.loads(self.page_ws.recv())
                print(f"  Received: {resp.get('method', 'response')} id={resp.get('id', 'N/A')}")
                if resp.get('id') == cmd['id']:
                    return resp
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as e:
                print(f"  Recv error: {e}")
                return None
        print(f"  Timeout waiting for response")
        return None

    def evaluate(self, script, timeout=10):
        if not self.page_ws:
            return None

        print(f"  Evaluating script...")
        resp = self._send_command("Runtime.evaluate", {
            "expression": script,
            "returnByValue": True
        })

        if resp:
            if 'error' in resp:
                print(f"  JS Error: {resp['error']}")
                return None
            if 'result' in resp:
                value = resp['result'].get('value')
                print(f"  Result type: {type(value).__name__}")
                return value
        return None


def main():
    print("="*60)
    print("Debug Douban Connection")
    print("="*60)

    bot = ConnectionDebugBot(9222)

    if not bot.connect():
        print("Failed to connect to Chrome")
        sys.exit(1)

    print("\n[OK] Connected to browser")

    if not bot.find_douban_page():
        print("No Douban page found")
        sys.exit(1)

    print("\n[OK] Connected to Douban page")

    # Wait for page to fully load
    print("\n[Waiting 5 seconds for page to stabilize...]")
    time.sleep(5)

    # Try basic evaluation
    print("\n[Try 1] document.title:")
    title = bot.evaluate("document.title")
    print(f"  Title: {title}")

    print("\n[Try 2] location.href:")
    url = bot.evaluate("location.href")
    print(f"  URL: {url}")

    print("\n[Try 3] document.readyState:")
    ready = bot.evaluate("document.readyState")
    print(f"  Ready: {ready}")

    print("\n[Try 4] document.body exists:")
    has_body = bot.evaluate("!!document.body")
    print(f"  Has body: {has_body}")

    print("\n[Try 5] Search input check:")
    search_info = bot.evaluate("""
        (function() {
            const input = document.querySelector('input[name="q"], input[type="search"]');
            if (input) {
                return {
                    found: true,
                    tagName: input.tagName,
                    type: input.type,
                    name: input.name,
                    id: input.id,
                    class: input.className,
                    visible: input.offsetParent !== null
                };
            }
            return { found: false };
        })()
    """)
    print(f"  Search input: {search_info}")

    print("\n" + "="*60)
    print("Debug complete")
    print("="*60)


if __name__ == '__main__':
    main()
