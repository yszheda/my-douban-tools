#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Douban Search - Navigate and inspect results page
"""

import json
import time
import sys
import urllib.parse
import requests
import websocket


class SearchDebugBot:
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
        except:
            return False

    def find_douban_page(self):
        try:
            pages = requests.get(f"{self.debug_url}/json/list", timeout=5).json()
            for page in pages:
                if 'douban.com' in page.get('url', ''):
                    self.page_id = page.get('id')
                    page_ws_url = page.get('webSocketDebuggerUrl')
                    if page_ws_url:
                        self.page_ws = websocket.create_connection(page_ws_url, timeout=10)
                        self._send_command("Page.enable")
                        self._send_command("Runtime.enable")
                        time.sleep(1)
                        return True
            return False
        except:
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

        self.page_ws.send(json.dumps(cmd))

        while True:
            try:
                resp = json.loads(self.page_ws.recv())
                if resp.get('id') == cmd['id']:
                    return resp
            except:
                return None

    def evaluate(self, script):
        if not self.page_ws:
            return None
        try:
            resp = self._send_command("Runtime.evaluate", {
                "expression": script,
                "returnByValue": True
            })
            if resp and 'result' in resp:
                return resp['result'].get('value')
            return None
        except:
            return None

    def navigate(self, url):
        if not self.page_ws:
            return
        return self._send_command("Page.navigate", {"url": url})

    def wait_load(self, seconds=3):
        time.sleep(seconds)


def main():
    print("="*60)
    print("Debug Douban Search Results")
    print("="*60)

    bot = SearchDebugBot(9222)
    if not bot.connect():
        print("Failed to connect to Chrome")
        sys.exit(1)

    if not bot.find_douban_page():
        print("No Douban page found")
        sys.exit(1)

    print("Connected to Douban page")

    # Check initial state
    print("\n[1] Initial page state:")
    initial = bot.evaluate("({url: location.href, title: document.title})")
    print(f"  URL: {initial.get('url', '')[:80]}")
    print(f"  Title: {initial.get('title', '')[:50]}")

    # Navigate to search results
    test_query = "Giacomo Lauri-Volpi"
    search_url = f"https://music.douban.com/search?query={urllib.parse.quote(test_query)}&type=1"
    print(f"\n[2] Navigating to search: {test_query}")
    bot.navigate(search_url)
    bot.wait_load(5)

    # Check post-navigation state
    print("\n[3] After navigation:")
    after_nav = bot.evaluate("({url: location.href, title: document.title})")
    print(f"  URL: {after_nav.get('url', '')[:80]}")
    print(f"  Title: {after_nav.get('title', '')[:50]}")

    # Get page HTML info
    print("\n[4] Page structure:")
    page_info = bot.evaluate("""
        (function() {
            return {
                url: location.href,
                title: document.title,
                bodyClass: document.body.className,
                bodyId: document.body.id,
                childCount: document.body.childElementCount,
                allClasses: Array.from(document.querySelectorAll('[class]'))
                    .map(el => el.className)
                    .filter(c => c)
                    .flatMap(c => c.split(' '))
                    .filter((v, i, a) => a.indexOf(v) === i)
                    .slice(0, 50)
            };
        })()
    """)
    if page_info:
        print(f"  Body class: {page_info.get('bodyClass', '')[:100]}")
        print(f"  Body id: {page_info.get('bodyId', '')}")
        print(f"  Child count: {page_info.get('childCount', 0)}")
        print(f"  Some classes: {page_info.get('allClasses', [])[:20]}")

    # Look for ANY links that look like album results
    print("\n[5] Looking for album links:")
    links = bot.evaluate("""
        (function() {
            const allLinks = Array.from(document.querySelectorAll('a[href]'));
            const albumLinks = allLinks.filter(a => {
                const href = a.href;
                return href.includes('/subject/') &&
                       (href.includes('/music/') || href.includes('douban.com'));
            });
            return albumLinks.slice(0, 10).map(a => ({
                href: a.href,
                text: a.textContent.trim().substring(0, 50),
                class: a.className
            }));
        })()
    """)
    if links and len(links) > 0:
        for link in links[:5]:
            print(f"  - {link['href'][:60]}...")
            print(f"    Text: {link['text']}")
            print(f"    Class: {link['class']}")
    else:
        print("  No album links found!")

    # Look for result containers
    print("\n[6] Looking for result containers:")
    containers = bot.evaluate("""
        (function() {
            const selectors = [
                '.result-list', '.result', '.card', '.item',
                '.search-result', '.music-item', '.card-wrap',
                'article', '.album-item', '.subject-item'
            ];
            const results = [];
            for (const sel of selectors) {
                const items = document.querySelectorAll(sel);
                if (items.length > 0) {
                    results.push({
                        selector: sel,
                        count: items.length,
                        firstClass: items[0].className,
                        firstId: items[0].id
                    });
                }
            }
            return results;
        })()
    """)
    if containers and len(containers) > 0:
        for c in containers:
            print(f"  - {c['selector']}: {c['count']} items")
            print(f"    Class: {c['firstClass'][:50]}")
            print(f"    ID: {c['firstId']}")
    else:
        print("  No result containers found!")

    # Check if we're still on the search page or got redirected
    print("\n[7] Cookie check:")
    cookies = bot.evaluate("document.cookie")
    if cookies:
        print(f"  Cookie length: {len(cookies)}")
        has_dbcl2 = 'dbcl2' in cookies
        print(f"  Has dbcl2: {has_dbcl2}")
    else:
        print("  No cookies found!")

    # Take snapshot of full HTML (first 2000 chars)
    print("\n[8] HTML snapshot (first 2000 chars):")
    html = bot.evaluate("document.documentElement.outerHTML")
    if html:
        print(f"  HTML length: {len(html)}")
        # Look for meaningful content
        if 'result' in html.lower():
            print("  Contains 'result' keyword")
        if 'subject' in html.lower():
            print("  Contains 'subject' keyword")
        if 'search' in html.lower():
            print("  Contains 'search' keyword")

    print("\n" + "="*60)
    print("Debug complete")
    print("="*60)


if __name__ == '__main__':
    main()
