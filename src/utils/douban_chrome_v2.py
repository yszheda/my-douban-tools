#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆瓣音乐批量处理 - 使用 Chrome DevTools
控制已打开的豆瓣音乐页面进行自动化操作
"""

import json
import time
import sys
import re
import urllib.parse
import random
from pathlib import Path

# 强制使用 UTF-8 编码输出
sys.stdout.reconfigure(encoding='utf-8')

try:
    import websocket
    import requests
except ImportError:
    print("需要安装：pip install websocket-client requests")
    sys.exit(1)


# 随机延迟配置
MIN_DELAY = 2.0  # 最小延迟（秒）
MAX_DELAY = 5.0  # 最大延迟（秒）
SEARCH_DELAY = 8.0  # 搜索后延迟
MARK_DELAY = 5.0  # 标记后延迟


def fetch_discogs_release_url(barcode):
    """通过 barcode 获取 Discogs 上的真实专辑 URL

    Args:
        barcode: 专辑条形码（EAN/UPC）

    Returns:
        str: Discogs 专辑 URL，如果未找到则返回 None
    """
    if not barcode:
        return None

    # 清理 barcode 中的空格和连字符
    clean_barcode = re.sub(r'[\s-]', '', barcode)

    try:
        # 使用 Discogs 网页搜索（不需要 API 认证）
        search_url = f"https://www.discogs.com/search/?q={clean_barcode}&type=release&sort=year,desc"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html'
        }

        response = requests.get(search_url, headers=headers, timeout=10, allow_redirects=True)

        if response.status_code == 200:
            # 检查是否重定向到具体专辑页面
            if 'discogs.com/release/' in response.url:
                return response.url

            # 或者在搜索结果中查找第一个匹配的链接
            match = re.search(r'https://www\.discogs\.com/release/(\d+)', response.text)
            if match:
                release_id = match.group(1)
                return f"https://www.discogs.com/release/{release_id}"

        return None

    except Exception as e:
        print(f"  获取 Discogs URL 失败：{e}")
        return None


def fetch_musicbrainz_release_url(barcode):
    """通过 barcode 获取 MusicBrainz 上的真实专辑 URL

    Args:
        barcode: 专辑条形码（EAN/UPC）

    Returns:
        str: MusicBrainz 专辑 URL，如果未找到则返回 None
    """
    if not barcode:
        return None

    # 清理 barcode 中的空格和连字符
    clean_barcode = re.sub(r'[\s-]', '', barcode)

    try:
        # 使用 MusicBrainz API 搜索
        api_url = f"https://musicbrainz.org/ws/2/release?barcode={clean_barcode}&fmt=json&limit=1"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('releases') and len(data['releases']) > 0:
                release = data['releases'][0]
                release_id = release.get('id')

                if release_id:
                    return f"https://musicbrainz.org/release/{release_id}"

        return None

    except Exception as e:
        print(f"  获取 MusicBrainz URL 失败：{e}")
        return None


def random_delay(min_sec=MIN_DELAY, max_sec=MAX_DELAY):
    """随机延迟"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


class DoubanChromeBot:
    def __init__(self, debug_port=9222):
        self.debug_url = f"http://127.0.0.1:{debug_port}"
        self.ws = None
        self.page_ws = None
        self.page_id = None
        self.cmd_id = 1

    def connect(self):
        """连接到 Chrome"""
        try:
            # 获取浏览器 WebSocket URL
            resp = requests.get(f"{self.debug_url}/json/version", timeout=5)
            browser_ws = resp.json().get("webSocketDebuggerUrl")
            if not browser_ws:
                print("无法获取浏览器 WebSocket URL")
                return False

            # 连接到浏览器
            self.ws = websocket.create_connection(browser_ws, timeout=10)
            return True
        except Exception as e:
            print(f"连接失败：{e}")
            return False

    def find_douban_page(self):
        """找到豆瓣音乐页面"""
        try:
            pages = requests.get(f"{self.debug_url}/json/list", timeout=5).json()
            for page in pages:
                if 'douban.com' in page.get('url', ''):
                    self.page_id = page.get('id')
                    page_ws_url = page.get('webSocketDebuggerUrl')
                    if page_ws_url:
                        self.page_ws = websocket.create_connection(page_ws_url, timeout=10)
                        # Enable necessary CDP domains
                        self._send_command("Page.enable")
                        self._send_command("Runtime.enable")
                        time.sleep(1)  # Wait for domains to initialize
                        return True
            return False
        except Exception as e:
            print(f"查找豆瓣页面失败：{e}")
            return False

    def _send_command(self, method, params=None, timeout=10, retries=2):
        """Send CDP command and get response with timeout and retry support"""
        if not self.page_ws:
            return None

        cmd = {
            "id": self.cmd_id,
            "method": method,
            "params": params or {}
        }
        self.cmd_id += 1

        for attempt in range(retries + 1):
            try:
                # Set WebSocket timeout
                self.page_ws.settimeout(timeout)
                self.page_ws.send(json.dumps(cmd))

                # Wait for response with matching id
                while True:
                    resp = json.loads(self.page_ws.recv())
                    # Skip events (no 'id' field) and wait for our response
                    if resp.get('id') == cmd['id']:
                        self.page_ws.settimeout(None)  # Reset to blocking mode
                        return resp
            except websocket.WebSocketTimeoutException:
                if attempt < retries:
                    print(f"  WebSocket 超时，重试 {attempt + 1}/{retries}...")
                    continue
                else:
                    print(f"  WebSocket 超时 {retries} 次，放弃")
                    raise
            except Exception as e:
                if attempt < retries:
                    print(f"  通信错误，重试 {attempt + 1}/{retries}: {e}")
                    continue
                else:
                    raise

    def evaluate(self, script):
        """执行 JavaScript"""
        if not self.page_ws:
            return None
        try:
            resp = self._send_command("Runtime.evaluate", {
                "expression": script,
                "returnByValue": True
            })
            # Response structure: {'id': X, 'result': {'result': {'type': '...', 'value': '...'}}}
            if resp and 'result' in resp:
                inner_result = resp['result'].get('result', {})
                if inner_result:
                    return inner_result.get('value')
            return None
        except Exception as e:
            print(f"执行脚本失败：{e}")
            return None

    def check_bot_detection(self):
        """检查是否触发反机器人检测"""
        page_title = self.evaluate("document.title")
        page_url = self.evaluate("location.href")
        page_text = self.evaluate("document.body.innerText")

        # 检查验证页面标题
        if page_title and ('安全' in page_title or '滑动验证' in page_title):
            print(f"  [BOT 检测] 页面标题包含敏感词：{page_title}")
            return True

        # 检查是否是验证页面（URL 包含 special/account 或标题包含 Galois 验证）
        if page_title and 'Galois' in page_title:
            print(f"  [BOT 检测] 页面标题包含 Galois：{page_title}")
            return True

        # 检查页面内容是否包含验证表单特征
        if page_text and ('滑动验证' in page_text or '安全验证' in page_text):
            print(f"  [BOT 检测] 页面内容包含验证表单")
            return True

        # 检查是否是错误/阻止页面
        if page_text and ('sorry' in page_text.lower() or '访问受限' in page_text):
            print(f"  [BOT 检测] 页面内容包含错误信息")
            return True

        return False

    def handle_bot_detection(self, wait_time=30):
        """处理反机器人检测 - 尝试刷新恢复"""
        if self.check_bot_detection():
            print("  检测到反机器人验证，尝试刷新恢复...")
            # 刷新页面
            self.evaluate("window.location.reload();")
            time.sleep(5)
            # 等待用户手动验证
            print(f"  请在浏览器中完成验证码验证，等待 {wait_time} 秒...")
            for _ in range(wait_time // 5):
                time.sleep(5)
                if not self.check_bot_detection():
                    print("  验证已完成，继续...")
                    return True
            print("  验证超时，但将继续尝试...")
            return not self.check_bot_detection()
        return True

    def navigate(self, url):
        """导航到 URL - 使用 JavaScript 而不是 CDP navigate"""
        if not self.page_ws:
            return None
        # 使用 JavaScript 进行导航，这样可以更好地处理重定向
        self._send_command("Runtime.evaluate", {
            "expression": f"window.location.href = '{url}';",
            "returnByValue": True
        })
        return self.wait_for_load()

    def wait_for_load(self, timeout=10):
        """等待页面加载完成"""
        if not self.page_ws:
            return False
        self.page_ws.settimeout(timeout)
        start = time.time()
        while time.time() - start < timeout:
            try:
                msg = json.loads(self.page_ws.recv())
                if msg.get('method') == 'Page.loadEventFired':
                    return True
            except websocket.WebSocketTimeoutException:
                continue
            except:
                break
        return False

    def wait_load(self, seconds=3):
        """简单等待指定秒数"""
        time.sleep(seconds)

    def wait_load(self, seconds=3):
        """等待加载"""
        time.sleep(seconds)

    def get_cookie(self, name):
        """获取 Cookie"""
        cookie = self.evaluate("document.cookie")
        if cookie:
            for item in cookie.split('; '):
                if '=' in item:
                    k, v = item.split('=', 1)
                    if k == name:
                        return v
        return None

    def check_login(self):
        """检查豆瓣登录"""
        dbcl2 = self.get_cookie("dbcl2")
        return dbcl2 is not None

    def search_album(self, artist, title, barcode=None, isrc=None):
        """搜索专辑 - 优先使用 barcode/ISRC 搜索"""

        # 优先使用 barcode 或 ISRC 搜索（更准确）
        search_query = None
        search_type = None

        if barcode:
            search_query = barcode
            search_type = "barcode"
        elif isrc:
            search_query = isrc
            search_type = "ISRC"
        elif artist and title:
            search_query = f"{artist} {title}".strip()
            search_type = "artist+title"
        else:
            print("  缺少搜索条件")
            return None

        print(f"  搜索 ({search_type})：{search_query}")

        # 随机延迟后开始搜索
        random_delay(1, 2)

        # 在页面上找到搜索框并输入
        search_result = self.evaluate("""
            (function() {
                // 寻找搜索输入框
                const searchInput = document.querySelector('input[name="search_text"], #inp-query');

                if (searchInput) {
                    // 清空并设置新值
                    searchInput.value = '';
                    searchInput.value = """ + json.dumps(search_query) + """;

                    // 触发事件
                    searchInput.dispatchEvent(new Event('input', { bubbles: true }));
                    searchInput.dispatchEvent(new Event('change', { bubbles: true }));

                    // 找到表单并提交
                    const form = searchInput.closest('form');
                    if (form) {
                        console.log('Form action: ' + form.action);
                        form.submit();
                        return 'submitted_via_form';
                    }

                    // 或者找到搜索按钮并点击
                    const searchBtn = document.querySelector('input[type="submit"], button[type="submit"]');
                    if (searchBtn) {
                        searchBtn.click();
                        return 'submitted_via_button';
                    }

                    // 模拟回车
                    const enterEvent = new KeyboardEvent('keydown', {
                        key: 'Enter',
                        code: 'Enter',
                        keyCode: 13,
                        bubbles: true
                    });
                    searchInput.dispatchEvent(enterEvent);
                    return 'submitted_via_enter';
                }

                return 'no_search_input';
            })()
        """)

        print(f"  搜索方式：{search_result}")

        # 等待搜索结果加载 - 使用随机延迟
        print("  等待搜索结果...")
        time.sleep(SEARCH_DELAY + random.uniform(0, 2))

        # 检查是否被反机器人检测
        page_title = self.evaluate("document.title")
        page_url = self.evaluate("location.href")

        # 处理反机器人检测
        if not self.handle_bot_detection(wait_time=20):
            print("  无法通过反机器人验证，跳过此专辑")
            return None

        if page_title and ('安全' in page_title or '验证' in page_title or 'sorry' in page_title.lower()):
            print(f"  检测到反机器人页面：{page_title}")
            return None

        print(f"  页面：{page_title[:50] if page_title else 'Unknown'}")

        # 获取搜索结果
        result = self.evaluate("""
            (function() {
                // 检查当前页面是否已经是专辑页面（非搜索结果页）
                const currentUrl = location.href;
                const isSubjectPage = /\/subject\/\d+/.test(currentUrl) &&
                                      !currentUrl.includes('/search') &&
                                      !currentUrl.includes('/subject_search');

                // 如果是专辑页面，直接返回
                if (isSubjectPage) {
                    return {
                        url: currentUrl,
                        title: document.title,
                        found: true,
                        total: 1,
                        isExactMatch: true
                    };
                }

                // 寻找所有可能的结果链接
                const allLinks = Array.from(document.querySelectorAll('a[href*="/subject/"]'));

                // 过滤掉导航链接，只保留结果链接
                const resultLinks = allLinks.filter(link => {
                    const href = link.href;
                    // 排除搜索相关的链接
                    if (href.includes('/search') || href.includes('/subject_search')) {
                        return false;
                    }
                    return true;
                });

                if (resultLinks.length > 0) {
                    const first = resultLinks[0];
                    return {
                        url: first.href,
                        title: first.textContent.trim().substring(0, 50),
                        found: true,
                        total: resultLinks.length
                    };
                }

                // 如果没有找到，返回页面信息
                return {
                    url: location.href,
                    title: document.title,
                    found: false,
                    bodyText: document.body.innerText.substring(0, 200)
                };
            })()
        """)

        if result and isinstance(result, dict):
            if result.get('found'):
                if result.get('isExactMatch'):
                    print(f"  Barcode 精确匹配到专辑页面")
                else:
                    print(f"  找到 {result.get('total', 1)} 个结果：{result.get('title', '')[:50]}")
                return result.get('url')
            else:
                print(f"  未找到结果 - URL: {result.get('url', '')[:50]}")
        return None

    def mark_as_listened(self, url):
        """标记为听过"""
        print(f"  访问专辑页面...")

        # 先导航到专辑页面
        self.navigate(url)
        time.sleep(MARK_DELAY + random.uniform(0, 2))

        # 检查是否被反机器人检测
        page_title = self.evaluate("document.title")
        if page_title and ('安全' in page_title or '验证' in page_title or 'sorry' in page_title.lower()):
            print(f"  检测到反机器人页面：{page_title}")
            return False

        # 获取 ck cookie
        ck = self.evaluate("document.cookie.split('; ').find(c => c.startsWith('ck='))?.split('=')[1]")

        if ck:
            # 构造收藏链接
            import re
            match = re.search(r'/subject/(\d+)', url)
            if match:
                subject_id = match.group(1)
                collect_url = f"https://music.douban.com/subject/{subject_id}/?interest=collect&ck={ck}"

                print(f"  标记为听过...")
                self.navigate(collect_url)
                time.sleep(3)

                # 检查是否成功
                result = self.evaluate("""
                    (function() {
                        const hasListened = document.body.innerText.includes('听过');
                        const isCollected = document.querySelector('.collected, [data-utility-key="collection"].active');
                        return {
                            hasListened: hasListened,
                            isCollected: !!isCollected,
                            title: document.title
                        };
                    })()
                """)

                print("  已标记为'听过'")
                return True
            else:
                print("  无法解析专辑 ID")
                return False
        else:
            print("  未找到 ck cookie，尝试点击方式...")

            # 尝试点击页面上的收藏按钮
            result = self.evaluate("""
                (function() {
                    const collectBtn = document.querySelector('a[href*="interest=collect"], .collect_btn');
                    if (collectBtn && collectBtn.href) {
                        window.location.href = collectBtn.href;
                        return 'clicked';
                    }
                    return 'not_found';
                })()
            """)

            if result == 'clicked':
                time.sleep(3)
                print("  已标记为'听过'")
                return True
            else:
                print("  未找到标记按钮")
                return False

    def add_tags(self, tags, retry_count=0):
        """添加标签"""
        if not tags:
            return

        tags = [t for t in tags if t]  # 移除空标签
        if not tags:
            return

        # 防止无限递归
        if retry_count > 1:
            print(f"  标签添加超时，放弃")
            return False

        # 豆瓣的标签输入通常在页面加载后动态显示
        result = self.evaluate(f"""
            (function() {{
                const tags = {json.dumps(tags[:5])};

                // 标签输入框的多种选择器
                const selectors = [
                    '.tag-input',
                    '#tags-input',
                    'input[name="tags"]',
                    '.tag-editor input',
                    '[placeholder*="标签"]',
                    '[placeholder*="tag"]',
                    '.resource-input-tag',
                    '.tag-area',
                    '.tags-more-wraper input',
                    '#my-tags'
                ];

                let input = null;
                for (const sel of selectors) {{
                    input = document.querySelector(sel);
                    if (input) break;
                }}

                if (!input) {{
                    // 尝试找到"添加标签"或类似的链接并点击它
                    const tagLink = document.querySelector('a[href*="tag"], .tags-more, .add-tag');
                    if (tagLink) {{
                        tagLink.click();
                        return 'clicked_tag_link';
                    }}
                    return 'not_found';
                }}

                let added = 0;
                for (const tag of tags) {{
                    input.value = tag.trim();
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));

                    const enterEvent = new KeyboardEvent('keydown', {{
                        key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true
                    }});
                    input.dispatchEvent(enterEvent);
                    added++;
                }}

                input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                return `added ${{added}} tags`;
            }})()
        """)

        if result and 'added' in result:
            print(f"  添加标签：{', '.join(tags)}")
            random_delay(1, 2)
            return True
        elif result == 'clicked_tag_link':
            print(f"  点击标签链接，等待加载...")
            time.sleep(3)
            return self.add_tags(tags, retry_count + 1)
        else:
            print(f"  标签添加状态：{result}")
            return False

    def upload_cover_image(self, image_path):
        """上传封面图片"""
        print(f"  上传封面图片：{image_path}")

        # 检查文件是否存在
        if not Path(image_path).exists():
            print(f"  封面图片文件不存在：{image_path}")
            return False

        # 获取文件绝对路径 - 使用正斜杠格式（CDP 要求）
        abs_path = str(Path(image_path).resolve()).replace('\\', '/')
        print(f"  文件绝对路径：{abs_path}")

        # 使用 Chrome DevTools Protocol 直接设置文件输入
        try:
            # 检查页面当前状态
            page_info = self.evaluate("""
                (function() {
                    const fileInput = document.querySelector('input[type="file"]');
                    const uploadArea = document.querySelector('.upload-area, .upload-btn, input[type="file"] + label, label[for*="upload"]');
                    const anyUpload = document.querySelector('input[type="file"]');
                    return {
                        hasFileInput: !!fileInput,
                        hasUploadArea: !!uploadArea,
                        fileInputVisible: fileInput ? fileInput.offsetParent !== null : false,
                        fileInputDisabled: fileInput ? fileInput.disabled : false
                    };
                })()
            """)
            print(f"  页面上传区域信息：{page_info}")

            # 如果文件输入框存在但不可见，先点击上传按钮
            if page_info.get('hasFileInput') and not page_info.get('fileInputVisible'):
                print(f"  文件输入框不可见，尝试点击上传区域...")
                click_result = self.evaluate("""
                    (function() {
                        const uploadArea = document.querySelector('.upload-area, .upload-btn, label[for*="upload"], button:contains("上传"), a:contains("上传")');
                        if (uploadArea) {
                            uploadArea.click();
                            return 'clicked';
                        }
                        const allElements = Array.from(document.querySelectorAll('a, button, label, div'));
                        for (const el of allElements) {
                            if (el.textContent.includes('上传') || el.textContent.toLowerCase().includes('upload')) {
                                el.click();
                                return 'clicked';
                            }
                        }
                        return 'not_found';
                    })()
                """)
                print(f"  点击上传区域结果：{click_result}")
                time.sleep(3)

            # 再次检查文件输入框
            has_file_input = self.evaluate("""
                (function() {
                    const fileInput = document.querySelector('input[type="file"]');
                    if (fileInput) {
                        fileInput.style.display = 'block';
                        fileInput.style.visibility = 'visible';
                        fileInput.style.opacity = '1';
                        return true;
                    }
                    return false;
                })()
            """)
            print(f"  文件输入框已显示：{has_file_input}")

            if not has_file_input:
                print(f"  未找到文件输入框")
                return False

            # 使用 JavaScript 直接设置文件 (通过 DataTransfer)
            print(f"  尝试通过 JavaScript 设置文件...")
            js_result = self.evaluate(f"""
                (function() {{
                    const fileInput = document.querySelector('input[type="file"]');
                    if (!fileInput) return {{ success: false, reason: 'no input' }};

                    // 尝试通过 DataTransfer 设置文件
                    try {{
                        const dataTransfer = new DataTransfer();
                        // 注意：这里不能直接设置远程文件，需要通过 CDP
                        return {{ success: 'ready', message: 'input ready' }};
                    }} catch(e) {{
                        return {{ success: false, error: e.message }};
                    }}
                }})()
            """)
            print(f"  JavaScript 检查结果：{js_result}")

            # 发送 CDP 命令来获取元素
            cmd = {
                "id": self.cmd_id,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": "document.querySelector('input[type=\"file\"]')",
                    "returnByValue": False
                }
            }
            self.cmd_id += 1
            self.page_ws.send(json.dumps(cmd))

            # 获取元素 objectId
            self.page_ws.settimeout(5)
            resp = json.loads(self.page_ws.recv())
            self.page_ws.settimeout(None)

            if 'result' not in resp or 'result' not in resp['result']:
                print(f"  无法获取文件输入元素")
                return False

            object_id = resp['result']['result']['objectId']
            print(f"  获取到 objectId: {object_id}")

            # 使用 CDP 设置文件 - 使用正确的 nodeId 查找方式
            # 通过 JavaScript 获取文件的 backendNodeId
            cmd = {
                "id": self.cmd_id,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": """(function() {
                        const input = document.querySelector('input[type="file"]');
                        if (!input) return null;
                        // 返回一个可以被 querySelector 使用的标识
                        return 'found';
                    })()""",
                    "returnByValue": True
                }
            }
            self.cmd_id += 1
            self.page_ws.send(json.dumps(cmd))

            self.page_ws.settimeout(5)
            resp = json.loads(self.page_ws.recv())
            # 跳过可能的 DOM 事件
            while resp.get('method', '').startswith('DOM.'):
                resp = json.loads(self.page_ws.recv())
            self.page_ws.settimeout(None)

            # 使用 Runtime.callFunctionOn 来直接操作文件输入
            # 先获取文件输入元素的远程对象引用
            cmd = {
                "id": self.cmd_id,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": "document.querySelector('input[type=\"file\"]')",
                    "returnByValue": False,
                    "userGesture": True
                }
            }
            self.cmd_id += 1
            self.page_ws.send(json.dumps(cmd))

            self.page_ws.settimeout(5)
            resp = json.loads(self.page_ws.recv())
            while resp.get('method', '').startswith('DOM.') or resp.get('method', '').startswith('Runtime.'):
                try:
                    resp = json.loads(self.page_ws.recv())
                except:
                    break
            self.page_ws.settimeout(None)

            if 'result' not in resp or 'result' not in resp.get('result', {}):
                print(f"  无法获取文件输入元素，响应：{resp}")
                return False

            object_id = resp['result']['result']['objectId']
            print(f"  获取到 objectId: {object_id}")

            # 使用 Runtime.callFunctionOn 来设置文件
            # 注意：由于安全限制，JavaScript 不能直接设置文件
            # 必须使用 DOM.setFileInputFiles

            # 先获取 nodeId 通过 DOM.requestNode
            cmd = {
                "id": self.cmd_id,
                "method": "DOM.requestNode",
                "params": {
                    "objectId": object_id
                }
            }
            self.cmd_id += 1
            self.page_ws.send(json.dumps(cmd))

            self.page_ws.settimeout(5)
            resp = json.loads(self.page_ws.recv())
            while resp.get('method', '').startswith('DOM.'):
                try:
                    resp = json.loads(self.page_ws.recv())
                except:
                    break
            self.page_ws.settimeout(None)

            node_id = None
            if 'result' in resp and 'nodeId' in resp['result'] and resp['result']['nodeId'] != 0:
                node_id = resp['result']['nodeId']
                print(f"  获取到 nodeId: {node_id}")
            else:
                print(f"  无法获取 nodeId，响应：{resp}")

            # 如果 nodeId 是 0，尝试使用 DOM.getDocument + querySelector
            if not node_id or node_id == 0:
                print(f"  nodeId 无效，尝试使用 querySelector...")

                # 获取文档
                cmd = {
                    "id": self.cmd_id,
                    "method": "DOM.getDocument",
                    "params": {}
                }
                self.cmd_id += 1
                self.page_ws.send(json.dumps(cmd))

                self.page_ws.settimeout(5)
                resp = json.loads(self.page_ws.recv())
                while resp.get('method', '').startswith('DOM.'):
                    try:
                        resp = json.loads(self.page_ws.recv())
                    except:
                        break
                self.page_ws.settimeout(None)

                if 'result' in resp and 'root' in resp['result']:
                    root_id = resp['result']['root']['nodeId']

                    # querySelector
                    cmd = {
                        "id": self.cmd_id,
                        "method": "DOM.querySelector",
                        "params": {
                            "nodeId": root_id,
                            "selector": "input[type=\"file\"]"
                        }
                    }
                    self.cmd_id += 1
                    self.page_ws.send(json.dumps(cmd))

                    self.page_ws.settimeout(5)
                    resp = json.loads(self.page_ws.recv())
                    while resp.get('method', '').startswith('DOM.'):
                        try:
                            resp = json.loads(self.page_ws.recv())
                        except:
                            break
                    self.page_ws.settimeout(None)

                    if 'result' in resp and 'nodeId' in resp['result'] and resp['result']['nodeId'] != 0:
                        node_id = resp['result']['nodeId']
                        print(f"  通过 querySelector 找到 nodeId: {node_id}")
                    else:
                        print(f"  querySelector 失败，响应：{resp}")

            # 使用 DOM.setFileInputFiles
            if node_id and node_id != 0:
                # 先尝试获取 backendNodeId
                backend_node_id = None

                # 尝试使用 backendNodeId 而不是 nodeId
                cmd = {
                    "id": self.cmd_id,
                    "method": "DOM.setFileInputFiles",
                    "params": {
                        "nodeId": node_id,
                        "files": [abs_path]
                    }
                }
                self.cmd_id += 1
                self.page_ws.send(json.dumps(cmd))

                self.page_ws.settimeout(5)
                resp = json.loads(self.page_ws.recv())
                while resp.get('method', '').startswith('DOM.'):
                    try:
                        resp = json.loads(self.page_ws.recv())
                    except:
                        break
                self.page_ws.settimeout(None)

                print(f"  CDP 设置文件结果：{resp}")

                # 检查文件输入框的 files 属性
                files_info = self.evaluate("""
                    (function() {
                        const fileInput = document.querySelector('input[type="file"]');
                        if (!fileInput) return { error: 'no input' };
                        return {
                            filesLength: fileInput.files.length,
                            files: Array.from(fileInput.files).map(f => ({ name: f.name, size: f.size, type: f.type }))
                        };
                    })()
                """)
                print(f"  文件输入框 files 信息：{files_info}")

                # 如果文件已设置，触发 input 事件和 change 事件
                if files_info.get('filesLength', 0) > 0:
                    print(f"  文件已设置，触发 input 和 change 事件...")

                    # 触发 input 事件（有些网站监听 input 事件来启动上传）
                    input_result = self.evaluate("""
                        (function() {
                            const fileInput = document.querySelector('input[type="file"]');
                            if (fileInput) {
                                fileInput.dispatchEvent(new Event('input', { bubbles: true }));
                                return 'input_dispatched';
                            }
                            return 'no_input';
                        })()
                    """)
                    print(f"  Input 事件结果：{input_result}")

                    # 等待一小段时间让网站处理文件
                    time.sleep(2)

                    # 触发 change 事件
                    change_result = self.evaluate("""
                        (function() {
                            const fileInput = document.querySelector('input[type="file"]');
                            if (fileInput && fileInput.files.length > 0) {
                                fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                                return 'changed';
                            }
                            return 'no_files';
                        })()
                    """)
                    print(f"  Change 事件结果：{change_result}")

                    # 等待上传完成
                    print(f"  等待上传完成...")
                    time.sleep(10)

                    # 检查是否有上传成功的标志
                    upload_status = self.evaluate("""
                        (function() {
                            // 检查是否有图片预览
                            const preview = document.querySelector('img[src*="subject"], img[src*="img"]');
                            if (preview) return { hasPreview: true, src: preview.src };

                            // 检查是否有进度条
                            const progress = document.querySelector('.progress, .upload-progress');
                            if (progress) return { hasProgress: true };

                            // 检查是否有成功消息
                            const successMsg = document.querySelector('.success, .notice');
                            if (successMsg && successMsg.textContent.includes('成功')) return { hasSuccess: true };

                            // 检查表单是否还在
                            const form = document.querySelector('form');
                            return { formExists: !!form };
                        })()
                    """)
                    print(f"  上传状态：{upload_status}")

                    # 获取页面完整 HTML 用于调试
                    page_html = self.evaluate("document.body.innerHTML")
                    print(f"  页面 HTML 长度：{len(page_html) if page_html else 0}")
                    if page_html and len(page_html) < 5000:
                        print(f"  页面 HTML: {page_html[:2000]}")

                    # 如果没有预览，检查是否有其他上传机制
                    if not upload_status.get('hasPreview'):
                        print(f"  未检测到封面预览，检查页面结构...")
                        page_structure = self.evaluate("""
                            (function() {
                                const form = document.querySelector('form');
                                const inputs = form ? Array.from(form.querySelectorAll('input')).map(i => ({
                                    type: i.type,
                                    name: i.name,
                                    id: i.id,
                                    value: i.value ? i.value.substring(0, 50) : null
                                })) : [];
                                const images = Array.from(document.querySelectorAll('img')).map(img => ({
                                    src: img.src,
                                    alt: img.alt
                                }));
                                return { formInputs: inputs, images: images.slice(0, 5) };
                            })()
                        """)
                        print(f"  页面结构：{page_structure}")

                # 检查响应中是否有 error
                if 'error' in resp:
                    print(f"  CDP 命令错误：{resp['error']}")
                    # 尝试使用 backendNodeId
                    if backend_node_id:
                        print(f"  尝试使用 backendNodeId: {backend_node_id}")
                        cmd = {
                            "id": self.cmd_id,
                            "method": "DOM.setFileInputFiles",
                            "params": {
                                "backendNodeId": backend_node_id,
                                "files": [abs_path]
                            }
                        }
                        self.cmd_id += 1
                        self.page_ws.send(json.dumps(cmd))

                        self.page_ws.settimeout(5)
                        resp = json.loads(self.page_ws.recv())
                        self.page_ws.settimeout(None)
                        print(f"  CDP 设置文件结果 (backendNodeId): {resp}")
            else:
                print(f"  未找到有效的 nodeId")
                return False

            # 触发 change 事件
            change_result = self.evaluate("""
                (function() {
                    const fileInput = document.querySelector('input[type="file"]');
                    if (fileInput && fileInput.files.length > 0) {
                        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                        return 'changed';
                    }
                    return 'no_files';
                })()
            """)
            print(f"  Change 事件结果：{change_result}")

            # 等待上传完成
            print(f"  等待上传完成...")
            time.sleep(8)

            # 检查上传是否成功（通过检查是否有预览图片）
            has_preview = self.evaluate("""
                (function() {
                    const preview = document.querySelector('img[src*="subject"]');
                    return !!preview;
                })()
            """)
            print(f"  封面预览：{has_preview}")

            # 如果没有预览，说明需要点击"上传图片"按钮来提交
            if not has_preview:
                print(f"  未检测到封面预览，尝试点击'上传图片'按钮...")

                # 寻找并提交"上传图片"按钮 - 必须是上传表单中的提交按钮
                submit_upload = self.evaluate("""
                    (function() {
                        // 首先尝试找到上传表单
                        const uploadForm = document.querySelector('form[method="post"][enctype*="multipart"]') ||
                                           document.querySelector('form[action*="upload"]') ||
                                           document.querySelector('form:has(input[type="file"])');

                        // 在上传表单中查找提交按钮
                        if (uploadForm) {
                            const submitBtn = uploadForm.querySelector('input[type="submit"], button[type="submit"]');
                            if (submitBtn) {
                                const btnText = submitBtn.value || submitBtn.textContent || '';
                                // 确认是上传按钮而不是其他按钮
                                if (btnText.includes('上传') || btnText.toLowerCase().includes('upload') || btnText === '提交') {
                                    submitBtn.click();
                                    return 'clicked_form_submit: ' + btnText.trim();
                                }
                            }
                        }

                        // 遍历所有提交按钮，检查是否在包含 file input 的表单中
                        const allSubmitBtns = document.querySelectorAll('input[type="submit"], button[type="submit"]');
                        for (const btn of allSubmitBtns) {
                            const form = btn.closest('form');
                            if (form && form.querySelector('input[type="file"]')) {
                                const btnText = btn.value || btn.textContent || '';
                                btn.click();
                                return 'clicked_file_form_submit: ' + btnText.trim();
                            }
                        }

                        // 最后尝试：查找包含"上传"文字的任何按钮
                        const allBtns = document.querySelectorAll('input, button');
                        for (const btn of allBtns) {
                            const text = btn.value || btn.textContent || '';
                            if (text.includes('上传') || text.toLowerCase().includes('upload')) {
                                // 确保这个按钮在包含 file input 的表单中
                                const form = btn.closest('form');
                                if (form && form.querySelector('input[type="file"]')) {
                                    btn.click();
                                    return 'clicked_upload: ' + text.trim();
                                }
                            }
                        }

                        return 'not_found';
                    })()
                """)
                print(f"  点击上传图片按钮结果：{submit_upload}")
                time.sleep(5)

                # 再次检查是否有预览
                has_preview = self.evaluate("""
                    (function() {
                        const preview = document.querySelector('img[src*="subject"]');
                        return !!preview;
                    })()
                """)
                print(f"  封面预览（点击后）：{has_preview}")

            # 不再点击提交按钮，由后续跳转处理
            return True

        except Exception as e:
            print(f"  封面上传失败：{e}")
            return False

    def create_new_album(self, album_info):
        """在豆瓣音乐创建新专辑条目 - 完整流程包括上传封面"""
        print("  创建新专辑条目...")

        # 步骤 0: 先获取真实权威 URL（Discogs, MusicBrainz）
        discogs_url = None
        musicbrainz_url = None

        if album_info.get('barcode'):
            print(f"  获取 Discogs 真实 URL (barcode: {album_info['barcode']})...")
            discogs_url = fetch_discogs_release_url(album_info['barcode'])
            if discogs_url:
                print(f"  找到 Discogs URL: {discogs_url}")
            else:
                print(f"  未找到 Discogs 专辑页面")

            print(f"  获取 MusicBrainz 真实 URL...")
            musicbrainz_url = fetch_musicbrainz_release_url(album_info['barcode'])
            if musicbrainz_url:
                print(f"  找到 MusicBrainz URL: {musicbrainz_url}")
            else:
                print(f"  未找到 MusicBrainz 专辑页面")

        # 将真实 URL 添加到 album_info 中
        if discogs_url:
            album_info['discogs_url'] = discogs_url
        if musicbrainz_url:
            album_info['musicbrainz_url'] = musicbrainz_url

        # 步骤 1: 导航到创建页面
        create_url = "https://music.douban.com/new_subject?cat=1003"
        print(f"  导航到创建页面...")
        self.navigate(create_url)
        time.sleep(5)  # 增加等待时间，确保页面完全加载

        # 检查页面是否真的加载完成
        page_check = self.evaluate("""
            (function() {
                return {
                    hasTitleField: !!document.querySelector('input[name="p_title"]'),
                    hasArtistField: !!document.querySelector('input[name="p_uid"]'),
                    url: location.href,
                    title: document.title
                };
            })()
        """)
        print(f"  页面检查：{page_check}")

        if not page_check or not page_check.get('hasTitleField'):
            print("  页面未正确加载，等待更长时间...")
            time.sleep(5)
            page_check = self.evaluate("""
                (function() {
                    return {
                        hasTitleField: !!document.querySelector('input[name="p_title"]'),
                        hasArtistField: !!document.querySelector('input[name="p_uid"]'),
                        url: location.href,
                        title: document.title
                    };
                })()
            """)
            print(f"  页面检查（第二次）：{page_check}")

            if not page_check or not page_check.get('hasTitleField'):
                print("  页面仍未准备好，放弃创建")
                return None

        # 检查并处理反机器人检测
        if not self.handle_bot_detection(wait_time=20):
            print("  无法通过反机器人验证，无法创建")
            return None

        # 步骤 2: 填写标题和艺术家
        print(f"  填写标题和艺术家...")
        result = self.evaluate(f"""
            (function() {{
                const info = {json.dumps(album_info, ensure_ascii=False)};
                const found = {{}};

                // 填写标题 (p_title)
                const titleField = document.querySelector('input[name="p_title"], #p_title');
                if (titleField && info.title) {{
                    titleField.value = info.title;
                    titleField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    found.title = true;
                }}

                // 填写艺术家 (uid)
                const artistField = document.querySelector('input[name="p_uid"], #uid');
                if (artistField && info.artist) {{
                    artistField.value = info.artist;
                    artistField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    found.artist = true;
                }}

                return {{
                    found: true,
                    filled: found
                }};
            }})()
        """)

        if result:
            print(f"  表单填写状态：标题={result.get('filled', {}).get('title')}, 艺术家={result.get('filled', {}).get('artist')}")

        # 步骤 3: 点击"添加无条形码的唱片"（因为条形码会触发校验错误）
        print(f"  点击'添加无条形码的唱片'...")
        submit_result = self.evaluate("""
            (function() {
                const btn = document.querySelector('input[name="no_uid_submit"]');
                if (btn) {
                    btn.click();
                    return 'clicked';
                }
                return 'not found';
            })()
        """)
        print(f"  提交结果：{submit_result}")
        time.sleep(5)

        # 步骤 4: 填写详情表单
        print(f"  填写详情表单...")
        fill_detail = self.evaluate(f"""
            (function() {{
                const info = {json.dumps(album_info, ensure_ascii=False)};
                const result = {{}};
                console.log('album_info:', info);

                // 唱片名 p_27 (必填)
                const p27 = document.querySelector('input[name="p_27"]');
                console.log('p27 field:', p27 ? 'found' : 'not found');
                if (p27 && info.title) {{
                    p27.value = info.title;
                    p27.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    result.p27 = 'ok';
                }}

                // 表演者 p_48 (必填)
                const p48 = document.querySelector('input[name="p_48"]');
                console.log('p48 field:', p48 ? 'found' : 'not found');
                if (p48 && info.artist) {{
                    p48.value = info.artist;
                    p48.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    result.p48 = 'ok';
                }}

                // 发行时间 p_51 (必填) - 格式：YYYY-MM-DD
                const p51 = document.querySelector('input[name="p_51"]');
                console.log('p51 field:', p51 ? 'found' : 'not found');
                if (p51) {{
                    const year = info.year || '1902';
                    const dateStr = year + '-01-01';
                    p51.value = dateStr;
                    p51.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    result.p51 = 'ok';
                }}

                // 出版者 p_50 (必填)
                const p50 = document.querySelector('input[name="p_50"]');
                console.log('p50 field:', p50 ? 'found' : 'not found');
                if (p50 && info.label) {{
                    p50.value = info.label;
                    p50.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    result.p50 = 'ok';
                }}

                // 流派 p_116 - 选择 Classical 古典 (值为 2)
                // 注意：豆瓣使用自定义 dropdown UI，直接设置 hidden input 并触发事件
                const p116_input = document.querySelector('input[name="p_116"]');
                const p116_selector = document.querySelector('.item .selector.single.wider-bg label.selected');
                console.log('p116 field (genre): input=', p116_input ? 'found' : 'not found', 'selector=', p116_selector ? 'found' : 'not found');
                if (p116_input) {{
                    p116_input.value = '2';
                    // 更新 UI 显示
                    if (p116_selector) {{
                        p116_selector.textContent = 'Classical 古典';
                        p116_selector.classList.add('has-value');
                    }}
                    p116_input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    result.p116 = 'ok';
                }}

                // 介质 p_49 - 选择 CD (值为 11)
                // 豆瓣的 UI 是先点击 selector 显示选项，然后点击对应选项
                const p49_input = document.querySelector('input[name="p_49"]');
                const p49_selector = p49_input?.closest('.selector')?.querySelector('label.selected');
                console.log('p49 field (media): input=', p49_input ? 'found' : 'not found', 'selector=', p49_selector ? 'found' : 'not found');
                if (p49_input && p49_selector) {{
                    // 先点击选择器显示选项
                    p49_selector.click();
                    setTimeout(() => {{
                        // 找到 CD 选项并点击
                        const optsGroup = p49_input.closest('.opts-group');
                        const cdOption = optsGroup?.querySelector('ul.options li label.sub:first-child');
                        if (cdOption && cdOption.textContent.trim() === 'CD') {{
                            cdOption.click();
                        }}
                    }}, 100);
                    p49_input.value = '11';
                    p49_input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    result.p49 = 'ok';
                }} else if (p49_input) {{
                    // 备用方案：直接设置值
                    p49_input.value = '11';
                    p49_input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    result.p49 = 'ok';
                }}

                // 专辑类型 p_57 - 选择专辑 (值为 1)
                const p57_input = document.querySelector('input[name="p_57"]');
                const p57_selector = document.querySelectorAll('.item .selector.single label.selected')[1];
                console.log('p57 field (type): input=', p57_input ? 'found' : 'not found', 'selector=', p57_selector ? 'found' : 'not found');
                if (p57_input) {{
                    p57_input.value = '1';
                    // 更新 UI 显示
                    if (p57_selector) {{
                        p57_selector.textContent = '专辑';
                        p57_selector.classList.add('has-value');
                    }}
                    p57_input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    result.p57 = 'ok';
                }}

                // 简介 p_28_other (必填) - 作曲家/作品简介
                const p28_other = document.querySelector('textarea[name="p_28_other"]');
                console.log('p28_other field (intro):', p28_other ? 'found' : 'not found');
                console.log('info.description length:', info.description ? info.description.length : 'empty');
                if (p28_other && info.description) {{
                    p28_other.value = info.description;
                    p28_other.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    p28_other.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    result.p28_other = 'ok';
                }} else {{
                    console.log('p28_other missing or no description');
                }}

                // 曲目列表 p_52_other (必填)
                const p52_other = document.querySelector('textarea[name="p_52_other"]');
                console.log('p52_other field (tracks):', p52_other ? 'found' : 'not found');
                console.log('info.tracks length:', info.tracks ? info.tracks.length : 'empty');
                if (p52_other && info.tracks) {{
                    p52_other.value = info.tracks;
                    p52_other.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    p52_other.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    result.p52_other = 'ok';
                }} else {{
                    console.log('p52_other missing or no tracks');
                }}

                // 参考资料 p_152_other (必填) - 需要包含真实权威链接
                const p152_other = document.querySelector('textarea[name="p_152_other"]');
                console.log('p152_other field:', p152_other ? 'found' : 'not found');
                if (p152_other) {{
                    let refText = '';

                    const title = info.title || '';
                    const artist = info.artist || '';
                    const barcode = info.barcode || '';
                    const catalogNumber = info.catalog_number || '';
                    const label = info.label || '';

                    // 使用传入的真实 URL（优先）
                    const discogsUrl = info.discogs_url || null;
                    const musicbrainzUrl = info.musicbrainz_url || null;

                    // Discogs 链接 - 优先使用真实 URL
                    if (discogsUrl) {{
                        refText += 'Discogs: ' + discogsUrl + '\\n';
                    }} else {{
                        // 如果没有真实 URL，使用搜索链接
                        const searchQuery = encodeURIComponent((title + ' ' + artist).replace(/[^a-zA-Z0-9\\s-]/g, '').trim());
                        if (barcode) {{
                            const cleanBarcode = barcode.replace(/[\\s-]/g, '');
                            refText += 'Discogs (barcode search): https://www.discogs.com/search/?q=' + cleanBarcode + '&type=release&sort=year,desc\\n';
                        }}
                        refText += 'Discogs (title search): https://www.discogs.com/search/?q=' + searchQuery + '&type=release&sort=year,desc\\n';
                    }}

                    // MusicBrainz 链接 - 优先使用真实 URL
                    if (musicbrainzUrl) {{
                        refText += 'MusicBrainz: ' + musicbrainzUrl + '\\n';
                    }} else {{
                        // 如果没有真实 URL，使用搜索链接
                        const searchQuery = encodeURIComponent((title + ' ' + artist).replace(/[^a-zA-Z0-9\\s-]/g, '').trim());
                        if (barcode) {{
                            const cleanBarcode = barcode.replace(/[\\s-]/g, '');
                            refText += 'MusicBrainz (barcode): https://musicbrainz.org/search?query=' + cleanBarcode + '&type=release&method=indexed\\n';
                        }}
                        refText += 'MusicBrainz (title): https://musicbrainz.org/search?query=' + searchQuery + '&type=release&method=indexed\\n';
                    }}

                    // Presto Music 链接 - 古典音乐专业网站（搜索链接）
                    const searchQuery = encodeURIComponent((title + ' ' + artist).replace(/[^a-zA-Z0-9\\s-]/g, '').trim());
                    refText += 'Presto Music: https://www.prestomusic.com/classical/search?keyword=' + searchQuery + '\\n';

                    // Last.fm 链接（搜索链接）
                    refText += 'Last.fm: https://www.last.fm/search?q=' + searchQuery + '\\n';

                    // 如果有 catalog number，添加唱片公司目录信息
                    if (catalogNumber && label) {{
                        refText += '\\nCatalog Number: ' + catalogNumber + ' (' + label + ')\\n';
                    }}
                    if (barcode) {{
                        refText += 'Barcode: ' + barcode + '\\n';
                    }}

                    p152_other.value = refText;
                    p152_other.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    p152_other.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    result.p152_other = 'ok';
                }}

                // 碟片数 p_55
                const p55 = document.querySelector('input[name="p_55"]');
                console.log('p55 field (discs):', p55 ? 'found' : 'not found');
                if (p55) {{
                    p55.value = info.discs || '1';
                    p55.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    result.p55 = 'ok';
                }}

                console.log('result:', result);
                return result;
            }})()
        """)
        print(f"  详情填写结果：{fill_detail}")
        time.sleep(3)

        # 步骤 5: 提交详情表单
        print(f"  表单填写完成，等待 30 秒让用户确认...")
        print(f"  请在浏览器中检查填写的信息是否正确")

        # 等待 30 秒让用户检查
        for i in range(30, 0, -1):
            print(f"  剩余 {i} 秒...", end='\r')
            time.sleep(1)
        print()

        print(f"  提交详情表单...")
        submit_detail = self.evaluate("""
            (function() {
                const btn = document.querySelector('input[name="detail_subject_submit"]');
                if (btn) {
                    btn.click();
                    return 'submitted';
                }
                return 'not found';
            })()
        """)
        print(f"  提交结果：{submit_detail}")
        time.sleep(8)

        # 步骤 6: 检查是否到达封面上传页面或直接成功页面
        page_title = self.evaluate("document.title")
        current_url = self.evaluate("location.href")
        print(f"  当前页面：{page_title}")
        print(f"  当前 URL: {current_url}")

        # 检查页面是否有错误信息
        error_messages = self.evaluate("""
            (function() {
                const errors = document.querySelectorAll('.error, .alert, .field-error');
                return Array.from(errors).map(e => e.textContent.trim()).slice(0, 5);
            })()
        """)
        if error_messages and len(error_messages) > 0:
            print(f"  页面错误信息：{error_messages}")

        # 检查是否直接显示"信息已成功提交"（跳过封面上传的情况）
        if page_title and ('信息已成功提交' in page_title or '等待审核' in page_title):
            # 从 URL 中获取 nuid
            nuid_match = re.search(r'nuid=(\d+)', current_url)
            if nuid_match:
                nuid = nuid_match.group(1)
                print(f"  创建成功，已提交审核（nuid={nuid}）")
                return f"https://music.douban.com/subject/{nuid}/"
            print(f"  创建成功，但未找到 nuid")
            return current_url

        if page_title and '上传唱片封套' in page_title:
            print(f"  到达封面上传页面，准备处理...")

            # 步骤 7: 获取 nuid 并上传封面
            nuid = self.evaluate("""
                (function() {
                    const nuidInput = document.querySelector('input[name="nuid"]');
                    if (nuidInput) {
                        return nuidInput.value;
                    }
                    return null;
                })()
            """)

            if nuid:
                print(f"  专辑 ID (nuid): {nuid}")

                # 检查是否有文件输入框
                has_file_input = self.evaluate("""
                    (function() {
                        return !!document.querySelector('input[type="file"]');
                    })()
                """)
                print(f"  页面有文件输入框：{has_file_input}")

                # 尝试上传封面图片（如果存在）
                if album_info.get('cover_path') and has_file_input:
                    print(f"  上传封面图片：{album_info['cover_path']}")
                    upload_result = self.upload_cover_image(album_info['cover_path'])
                    print(f"  封面上传结果：{upload_result}")

                    # 上传成功后等待页面自动跳转，不再手动跳转
                    if upload_result:
                        print(f"  封面已上传，等待页面自动处理...")
                        time.sleep(10)  # 等待上传处理和页面跳转

                        # 检查是否已跳转到成功页面
                        check_status = self.evaluate("""
                            (function() {
                                return {
                                    title: document.title,
                                    url: location.href,
                                    isSuccess: document.body.innerText.includes('信息已成功提交') || document.body.innerText.includes('等待审核')
                                };
                            })()
                        """)
                        print(f"  上传后页面状态：{check_status}")

                        if check_status.get('isSuccess') or ('信息已成功提交' in check_status.get('title', '') or '等待审核' in check_status.get('title', '')):
                            print(f"  已到达成功页面")
                            # 从 URL 中获取 nuid
                            nuid_match = re.search(r'nuid=(\d+)', check_status.get('url', ''))
                            if nuid_match:
                                nuid = nuid_match.group(1)
                                print(f"  创建成功，已提交审核（nuid={nuid}）")
                                return f"https://music.douban.com/subject/{nuid}/"
                        else:
                            # 如果还没有跳转，尝试点击"上传图片"按钮
                            print(f"  尝试点击'上传图片'按钮提交...")
                            submit_result = self.evaluate("""
                                (function() {
                                    const allBtns = document.querySelectorAll('input, button');
                                    for (const btn of allBtns) {
                                        const text = btn.value || btn.textContent || '';
                                        if (text.includes('上传') || text.toLowerCase().includes('upload')) {
                                            btn.click();
                                            return 'clicked: ' + text.trim();
                                        }
                                    }
                                    // 也尝试所有 submit 按钮
                                    const submitBtn = document.querySelector('input[type="submit"], button[type="submit"]');
                                    if (submitBtn) {
                                        submitBtn.click();
                                        return 'clicked_submit';
                                    }
                                    return 'not_found';
                                })()
                            """)
                            print(f"  点击提交结果：{submit_result}")
                            time.sleep(10)  # 等待提交和跳转

                            # 再次检查是否成功
                            final_url = self.evaluate("location.href")
                            final_title = self.evaluate("document.title")
                            print(f"  最终页面：{final_title}")
                            print(f"  最终 URL: {final_url}")

                            if final_title and ('信息已成功提交' in final_title or '等待审核' in final_title):
                                nuid_match = re.search(r'nuid=(\d+)', final_url)
                                if nuid_match:
                                    nuid = nuid_match.group(1)
                                    print(f"  创建成功，已提交审核（nuid={nuid}）")
                                    return f"https://music.douban.com/subject/{nuid}/"
                            elif final_url and f'nuid={nuid}' in final_url:
                                print(f"  创建成功，已提交审核（nuid={nuid}）")
                                return f"https://music.douban.com/subject/{nuid}/"

                elif not album_info.get('cover_path'):
                    print(f"  无封面图片，跳过上传")
                else:
                    print(f"  页面无文件输入框，跳过上传")

                # 只有在不成功时才跳转到跳过 URL
                skip_url = f"https://music.douban.com/new_subject?mine&nuid={nuid}"
                print(f"  跳转到：{skip_url}")
                self.navigate(skip_url)  # 使用 navigate 方法确保页面加载完成

                # 等待页面加载并验证
                time.sleep(5)

                # 验证页面是否正确加载
                for retry in range(3):
                    final_url = self.evaluate("location.href")
                    final_title = self.evaluate("document.title")
                    print(f"  验证页面 (尝试 {retry+1}/3): {final_title}")
                    print(f"  最终 URL: {final_url}")

                    # 检查是否成功提交（等待审核）
                    if final_title and ('信息已成功提交' in final_title or '等待审核' in final_title):
                        print(f"  创建成功，已提交审核（nuid={nuid}）")
                        return f"https://music.douban.com/subject/{nuid}/"

                    # 检查是否在正确的页面
                    if final_url and f'nuid={nuid}' in final_url:
                        if final_title and ('上传唱片封套' not in final_title):
                            print(f"  创建成功，已提交审核（nuid={nuid}）")
                            return f"https://music.douban.com/subject/{nuid}/"
                        break  # 页面正确，继续检查

                    # 如果 URL 不对，等待后重试
                    if not final_url or '/subject_search' in final_url:
                        print(f"  页面跳转被干扰，等待重试...")
                        time.sleep(3)
                        self.navigate(skip_url)
                        continue

                # 最终检查
                final_url = self.evaluate("location.href")
                final_title = self.evaluate("document.title")

                if final_title and ('信息已成功提交' in final_title or '等待审核' in final_title):
                    print(f"  创建成功，已提交审核（nuid={nuid}）")
                    return f"https://music.douban.com/subject/{nuid}/"

                if final_url and f'nuid={nuid}' in final_url:
                    print(f"  创建成功，已提交审核（nuid={nuid}）")
                    return f"https://music.douban.com/subject/{nuid}/"

                print(f"  创建失败：页面验证未通过")
                return None

        # 页面标题不是预期的，尝试从 URL 中提取 nuid
        print(f"  页面标题不符合预期，尝试从 URL 中提取 nuid...")
        nuid_match = re.search(r'nuid=(\d+)', current_url)
        if nuid_match:
            nuid = nuid_match.group(1)
            print(f"  找到 nuid: {nuid}，尝试跳转...")
            skip_url = f"https://music.douban.com/new_subject?mine&nuid={nuid}"
            self.navigate(skip_url)
            time.sleep(5)

            final_url = self.evaluate("location.href")
            final_title = self.evaluate("document.title")
            print(f"  跳转后页面：{final_title}")
            print(f"  跳转后 URL: {final_url}")

            if final_title and ('信息已成功提交' in final_title or '等待审核' in final_title):
                print(f"  创建成功，已提交审核（nuid={nuid}）")
                return f"https://music.douban.com/subject/{nuid}/"

        # 检查是否直接跳转到专辑页面
        if current_url and '/subject/' in current_url:
            print(f"  创建成功：{current_url}")
            return current_url

        print("  创建失败，需要手动操作")
        return None


def parse_album_file(directory):
    """解析专辑信息"""
    file_path = Path(directory) / "专辑基本信息.md"
    if not file_path.exists():
        return None

    try:
        # 尝试多种编码读取文件
        content = None
        for enc in ['utf-8', 'utf-8-sig', 'gbk', 'cp936']:
            try:
                content = file_path.read_text(encoding=enc)
                # 验证是否成功读取：检查是否包含有效中文字符
                # 中文字符 Unicode 范围：\u4e00-\u9fff
                has_chinese = bool(re.search(r'[\u4e00-\u9fff]', content))
                if has_chinese and '\ufffd' not in content:
                    break
            except:
                continue

        # 如果所有编码都失败，用 utf-8 忽略错误
        if not content or '\ufffd' in content:
            content = file_path.read_text(encoding='utf-8', errors='ignore')

        title = ""
        artist = ""
        label = ""
        barcode = ""
        isrc = ""
        composers = []

        # 方法 1: ## 专辑名称
        title_match = re.search(r'##\s*专辑名称\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()

        # 方法 2: - **专辑名称**：XXX 或 - **专辑名**：XXX
        if not title:
            title_match2 = re.search(r'-\s*\*\*专辑名(?:称)?\*\*\s*[:：]\s*(.+?)(?:\n|$)', content)
            if title_match2:
                title = title_match2.group(1).strip()
                if '（' in title:
                    title = title.split('（')[0].strip()

        # 方法 2b: **专辑名**: 格式（冒号在**内）
        if not title:
            title_match3 = re.search(r'\*\*专辑名[:：]\s*\*\*\s*(.+?)(?:\n|$)', content)
            if title_match3:
                title = title_match3.group(1).strip()
                if '（' in title:
                    title = title.split('（')[0].strip()

        # 方法 2c: **专辑名**: 格式（冒号在**内，无后**）
        if not title:
            title_match4 = re.search(r'\*\*专辑名[:：]\s*(.+?)(?:\n|$)', content)
            if title_match4:
                title = title_match4.group(1).strip()
                # 清理星号
                title = title.lstrip('*').strip()
                if '（' in title:
                    title = title.split('（')[0].strip()

        # 方法 3: 在## 基础信息章节中查找 **专辑名称**
        if not title:
            base_info = re.search(r'##\s*基础信息\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
            if base_info:
                section = base_info.group(1)
                title_match3 = re.search(r'\*\*专辑名称\*\*\s*[:：]\s*(.+?)(?:\n|$)', section)
                if title_match3:
                    title = title_match3.group(1).strip()
                    if '（' in title:
                        title = title.split('（')[0].strip()

        # 方法 1: ## 艺术家
        artist_match = re.search(r'##\s*艺术家\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
        if artist_match:
            artist_text = artist_match.group(1).strip()
            # 提取第一个**名字**
            name_match = re.search(r'\*\*(.+?)\*\*', artist_text)
            if name_match:
                artist = name_match.group(1).strip()
                # 清理艺术家名字 - 移除括号、冒号等
                if '(' in artist:
                    artist = artist.split('(')[0].strip()
                if ':' in artist:
                    artist = artist.split(':')[0].strip()
                if '：' in artist:
                    artist = artist.split('：')[0].strip()
                # 如果是"多位艺术家"，重置
                if '多位' in artist or 'Various' in artist:
                    artist = ""

        # 方法 1b: ## 演奏家 (用于古典音乐专辑)
        if not artist:
            performer_match = re.search(r'##\s*演奏家\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
            if performer_match:
                section = performer_match.group(1)
                # 提取第一行的艺术家名字
                first_line = section.strip().split('\n')[0]
                western_match = re.search(r'\*\*(.+?)\*\*', first_line)
                if western_match:
                    artist = western_match.group(1).strip()
                    if '(' in artist:
                        artist = artist.split('(')[0].strip()

        # 方法 1c: ## 演奏者 (用于古典音乐专辑)
        if not artist:
            performer_match2 = re.search(r'-\s*\*\*演奏者\*\*\s*[:：]\s*(.+?)(?:\n|$)', content)
            if performer_match2:
                performer_text = performer_match2.group(1).strip()
                # 提取第一个西方名字（括号前的英文）
                if '(' in performer_text:
                    artist = performer_text.split('(')[0].strip()
                else:
                    artist = performer_text.split(' -')[0].strip()

        # 方法 1d: **演奏者**: 格式（冒号在**内）
        if not artist:
            performer_match3 = re.search(r'\*\*演奏者[:：]\s*\*\*\s*(.+?)(?:\n|$)', content)
            if performer_match3:
                performer_text = performer_match3.group(1).strip()
                if '(' in performer_text:
                    artist = performer_text.split('(')[0].strip()
                else:
                    artist = performer_text.split(' -')[0].strip()

        # 方法 1e: **演奏者**: 格式（冒号在**内，无后**）
        if not artist:
            performer_match4 = re.search(r'\*\*演奏者[:：]\s*(.+?)(?:\n|$)', content)
            if performer_match4:
                performer_text = performer_match4.group(1).strip()
                # 清理星号
                performer_text = performer_text.lstrip('*').strip()
                if '(' in performer_text:
                    artist = performer_text.split('(')[0].strip()
                else:
                    artist = performer_text.split(' -')[0].strip()

        # 方法 1f: ## 完整演出阵容 (用于合辑)
        if not artist:
            lineup_match = re.search(r'##\s+完整演出*阵容\s*\n(.*?)(?=##)', content, re.DOTALL)
            if lineup_match:
                lineup = lineup_match.group(1).strip()
                # 提取第一个名字 (英文或中文)
                # 英文名字：第一个逗号前的内容
                if ',' in lineup:
                    artist = lineup.split(',')[0].strip()
                else:
                    # 中文名字：第一个顿号或'和'前的内容
                    artist = re.split(r'[、和]', lineup)[0].strip()

        # 方法 1g: ## 参与艺术家 (用于合辑，如 Great Voices at Teatro Regio)
        if not artist:
            participants_match = re.search(r'##\s+参与艺术家\s*\n(.*?)(?=##)', content, re.DOTALL)
            if participants_match:
                participants = participants_match.group(1).strip()
                # 提取第一行的第一个名字
                # 格式可能是 "完整阵容 (共 22 位歌唱家):\n- **Francesco Tamagno** - tenor"
                # 找第一个**-** 格式的名字
                name_match = re.search(r'\*\*(.+?)\*\*', participants)
                if name_match:
                    artist = name_match.group(1).strip()
                    # 清理括号内容
                    if '(' in artist:
                        artist = artist.split('(')[0].strip()

        # 方法 2: 从艺术家章节中提取西方名字
        if not artist:
            artist_section = re.search(r'\*\*艺术家\*\*[:：]\s*\n(.*?)(?=-\s*\*\*)', content, re.DOTALL)
            if artist_section:
                section_text = artist_section.group(1)
                # Find Western names (FirstName LastName pattern)
                western_names = re.findall(r'[:：]([A-Za-z]+ [A-Za-z]+)', section_text)
                if western_names:
                    artist = western_names[0]

        # 方法 3: - **艺术家**：XXX
        if not artist:
            artist_match2 = re.search(r'-\s*\*\*艺术家\*\*\s*[:：]\s*(.+?)(?:\n|$)', content)
            if artist_match2:
                artist = artist_match2.group(1).strip()
                if '(' in artist:
                    artist = artist.split('(')[0].strip()

        # 方法 4: 从列表中提取艺术家（如 - 钢琴：XXX）
        if not artist:
            artist_lines = re.findall(r'-\s*(?:钢琴 | 小提琴 | 指挥 | 演奏)[：:]\s*([^(]+)', content)
            if artist_lines:
                artist = artist_lines[0].strip()

        # 方法 5: 在## 基础信息章节中查找 **艺术家**
        if not artist:
            base_info = re.search(r'##\s*基础信息\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
            if base_info:
                section = base_info.group(1)
                # Find Western names from artist section
                artist_section = re.search(r'\*\*艺术家\*\*\s*[:：]\s*\n(.*?)(?=-\s*\*\*)', section, re.DOTALL)
                if artist_section:
                    section_text = artist_section.group(1)
                    western_names = re.findall(r'[:：]([A-Za-z]+ [A-Za-z]+)', section_text)
                    if western_names:
                        artist = western_names[0]

        # 提取厂牌/发行方 - 支持多种格式（注意：有些文件冒号在**里面，如**厂牌*:)
        label_match = re.search(r'\*\*厂牌\*\*[:：]\s*(.+?)(?:\n|$)', content)
        if not label_match:
            label_match = re.search(r'\*\*厂牌\*[:：]\s*(.+?)(?:\n|$)', content)  # 冒号在**内
        if not label_match:
            label_match = re.search(r'\*\*厂牌[:：]\s*(.+?)(?:\n|$)', content)  # 无后**
        if not label_match:
            label_match = re.search(r'-\s*\*\*发行方\*\*\s*[:：]\s*(.+?)(?:\n|$)', content)
        if label_match:
            label = label_match.group(1).strip()
            # 清理括号内容和星号
            label = label.lstrip('*').strip()
            if '(' in label:
                label = label.split('(')[0].strip()
            if '（' in label:
                label = label.split('（')[0].strip()

        # 提取发行年份 - 支持多种格式（注意：有些文件冒号在**中间，如**发行年份*:)
        year = ""
        # 顺序：从具体到通用
        year_patterns = [
            r'-\s*\*\*录音年代\*\*\s*[:：]\s*(\d{4})[-–]\s*(\d{4})',  # - **录音年代**: 1902-1929（取第一个年份）
            r'-\s*\*\*发行年份\*\*\s*[:：]\s*(\d{4})',  # - **发行年份**: 1988
            r'\*\*发行年份\*\*\s*[:：]\s*(\d{4})',  # **发行年份**: 1988
            r'\*\*发行年份\*[:：]\s*(\d{4})',  # **发行年份*: 1988（冒号在**内）
            r'\*\*发行年份[:：]\s*(\d{4})',  # **发行年份：1988（无后**）
            r'\*\*[^*:]+[:：]\*\*\s*(\d{4})',  # **xxx**: 通用格式（冒号在**内）
            r'\*\*[^*:]+[:：]\*\s*(\d{4})',  # **xxx*: 通用格式
            r'-\s*\*\*年份\*\*\s*[:：]\s*(\d{4})',
            r'\*\*年份\*\*\s*[:：]\s*(\d{4})',
            r'\*\*年份\*[:：]\s*(\d{4})',
            r'\*\*年份[:：]\s*(\d{4})',
            r'-\s*\*\*出版时间\*\*\s*[:：]\s*(\d{4})',  # - **出版时间**: 1998
            r'\*\*出版时间\*\*\s*[:：]\s*(\d{4})',  # **出版时间**: 1998
            r'发行年份.*?[:：]\s*(\d{4})',  # 最灵活匹配
        ]
        for p in year_patterns:
            year_match = re.search(p, content)
            if year_match:
                # 如果是录音年代范围（如 1902-1929），取第一个年份
                if year_match.lastindex == 2:
                    year = year_match.group(1)
                else:
                    year = year_match.group(1)
                break

        # 提取目录编号 - 支持多种格式（注意：有些文件冒号在**里面，如**目录编号*:)
        catalog_number = ""
        catalog_match = re.search(r'-\s*\*\*目录编号\*\*\s*[:：]\s*(.+?)(?:\n|$)', content)
        if not catalog_match:
            catalog_match = re.search(r'\*\*目录编号\*\*[:：]\s*(.+?)(?:\n|$)', content)  # 冒号在**后
        if not catalog_match:
            catalog_match = re.search(r'\*\*目录编号\*[:：]\s*(.+?)(?:\n|$)', content)  # 冒号在**内
        if not catalog_match:
            catalog_match = re.search(r'\*\*目录编号[:：]\s*(.+?)(?:\n|$)', content)  # 无后**
        if not catalog_match:
            catalog_match = re.search(r'-\s*\*\*产品编号\*\*\s*[:：]\s*(.+?)(?:\n|$)', content)  # - **产品编号**: 格式
        if not catalog_match:
            catalog_match = re.search(r'\*\*产品编号\*\*[:：]\s*(.+?)(?:\n|$)', content)  # **产品编号**: 格式
        if catalog_match:
            catalog_number = catalog_match.group(1).strip()
            # 清理星号
            catalog_number = catalog_number.lstrip('*').strip()

        # 提取条码/ISRC - 支持多种格式
        barcode = ""
        barcode_patterns = [
            r'-\s*\*\*EAN.+?\*\*\s*[:：]\s*([0-9 -]+)',  # - **EAN 条形码**: 8-010984-050986
            r'\*\*EAN.+?\*\*\s*[:：]\s*([0-9 -]+)',  # **EAN 条形码**: 格式
            r'\*\*条形码\*\*\s*[:：]\s*([0-9 ]+)',
            r'\*\*条码.*?\*\*\s*[:：]\s*([A-Za-z0-9-]+)',  # **条码（Barcode）**格式
            r'\*\*条形码\s*\([^)]*\):\*\*\s*([0-9 -]+)',  # **条形码 (Barcode):** 格式
            r'条码.*?[:：\s]+([0-9]+)',  # 简单匹配：条码后跟数字
            r'(?:条码 | 条形码|Barcode|barcode|BARCODE)[:：\s]*([A-Za-z0-9-]+)',
            r'\*\*(?:EAN|UPC)\*\*[:：]?\s*([0-9]+)',  # **EAN**: 格式
            r'(?:EAN|UPC)[:：\s*]+([0-9]{13})',  # EAN 后跟 13 位数字（最简单模式）
        ]
        for pattern in barcode_patterns:
            barcode_match = re.search(pattern, content)
            if barcode_match:
                # 移除空格和连字符，只保留连续数字
                barcode = re.sub(r'[\s-]', '', barcode_match.group(1).strip())
                break

        # 提取 ISRC
        isrc = ""
        isrc_match = re.search(r'(?:ISRC|isrc)[:：\s]*([A-Za-z]{2}-?[A-Z0-9]{3}-?[0-9]{2}-?[0-9]{5})', content, re.IGNORECASE)
        if isrc_match:
            isrc = isrc_match.group(1).strip().upper()

        # 提取作曲家（带生卒年份的）
        composers = []
        composer_matches = re.findall(r'\*\*(.+?)\s*\(\d{4}[-–]\d{4}\)\*\*', content)
        composers = list(set(c.strip() for c in composer_matches[:3]))

        # 从标题中提取常见作曲家名字
        common_composers = ['Bach', 'Mozart', 'Beethoven', 'Debussy', 'Chopin',
                           'Schubert', 'Brahms', 'Tchaikovsky', 'Mahler', 'Wagner']
        for name in common_composers:
            if name in title and name not in composers:
                composers.append(name)

        # 提取曲目列表
        tracks = ""
        # 使用更灵活的正则表达式匹配曲目列表部分（支持"完整曲目列表"等变体）
        track_section = re.search(r'##\s*(?:完整)?曲目列表\s*\n(.*?)(?=\n##\s|\n---|\Z)', content, re.DOTALL)
        if track_section:
            track_content = track_section.group(1).strip()
            # 解析表格格式的曲目
            track_lines = []
            for line in track_content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                # 检测是否是表格行
                if '|' in line:
                    # 跳过表格分隔线
                    if '|---' in line:
                        continue
                    # 跳过表头
                    if '曲号' in line or '序号' in line or '作品' in line and '时长' not in line:
                        continue
                    # 提取曲目信息
                    parts = [p.strip() for p in line.split('|')]
                    # 过滤空的部分和表头
                    parts = [p for p in parts if p and p.strip() and '曲号' not in p and '序号' not in p]
                    if len(parts) >= 2:
                        track_num = parts[0].strip()
                        track_work = parts[1].strip() if len(parts) > 1 else ''
                        track_detail = parts[2].strip() if len(parts) > 2 else ''
                        track_time = parts[3].strip() if len(parts) > 3 else ''
                        # 只保留主要轨（整数轨号）
                        if track_num.isdigit():
                            track_text = f"{track_num}. {track_work}"
                            if track_detail:
                                track_text += f" {track_detail}"
                            if track_time:
                                track_text += f" ({track_time})"
                            track_lines.append(track_text.strip())

            if track_lines:
                tracks = '\n'.join(track_lines)
            elif track_content:
                # 如果没有解析出曲目，使用原始内容（清理表格格式）
                tracks = re.sub(r'\|', '', track_content)

        # 如果专辑基本信息中没有有效曲目，尝试从 Booklet 文件解析
        if not tracks or '[Track listing' in tracks or 'original file' in tracks:
            booklet_files = list(Path(directory).glob('Booklet*.md')) + list(Path(directory).glob('booklet*.md'))
            for booklet_file in booklet_files:
                try:
                    booklet_content = booklet_file.read_text(encoding='utf-8')
                    track_lines = []

                    # 解析 CD 分段
                    cd_sections = re.findall(r'##\s*(CD\s*\d+)\s*\n(.*?)(?=##\s*CD|\Z)', booklet_content, re.DOTALL)
                    for cd_name, cd_content in cd_sections:
                        # 匹配曲目行：数字。曲目名称 .... 时长
                        track_matches = re.findall(r'^(\d+)\.\s+([^.]+?)\s*\.+\s*(\d+:\d+)', cd_content, re.MULTILINE)
                        for track_num, track_name, track_time in track_matches:
                            track_name = track_name.strip()
                            # 清理曲目名称中的 markdown 格式
                            track_name = re.sub(r'\*\*(.+?)\*\*', r'\1', track_name)
                            track_lines.append(f"{track_num}. {track_name} ({track_time})")

                    if track_lines:
                        tracks = '\n'.join(track_lines)
                        print(f"  从 Booklet 文件解析到 {len(track_lines)} 首曲目")
                        break
                except Exception as e:
                    print(f"  解析 Booklet 文件失败：{e}")
                    continue

        # 提取简介/作曲家简介
        description = ""
        desc_sections = ['作曲家简介', '作品简介', '作曲家与作品简介', '专辑简介']
        for desc_name in desc_sections:
            desc_match = re.search(rf'##\s*{desc_name}\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
            if desc_match:
                desc_text = desc_match.group(1).strip()
                # 清理 markdown 格式
                desc_text = re.sub(r'\*\*(.+?)\*\*', r'\1', desc_text)  # 移除粗体
                desc_text = re.sub(r'###\s*', '', desc_text)  # 移除小标题
                # 取前 1000 字符
                description = desc_text[:1000]
                break

        # 如果没有简介，使用基础信息
        if not description:
            base_info = re.search(r'##\s*基础信息\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
            if base_info:
                base_text = base_info.group(1).strip()
                base_text = re.sub(r'\*\*(.+?)\*\*', r'\1', base_text)
                description = base_text[:500]

        return {
            'title': title,
            'artist': artist,
            'label': label,
            'barcode': barcode,
            'isrc': isrc,
            'year': year,
            'catalog_number': catalog_number,
            'tracks': tracks,
            'description': description,
            'composers': composers,
            'discs': 1  # 默认 1 碟
        }
    except Exception as e:
        print(f"  解析失败：{e}")
        return None


def extract_artist_from_dirname(dir_name):
    """从目录名中提取艺术家信息

    Args:
        dir_name: 专辑目录名

    Returns:
        str: 提取的艺术家名称
    """
    # 移除常见后缀
    clean_name = re.sub(r'\s*\([^)]*\)\s*$', '', dir_name)  # 移除 (XXX) 格式
    clean_name = re.sub(r'\s*CD\d+\s*$', '', clean_name, flags=re.IGNORECASE)  # 移除 CD1, CD2 等
    clean_name = re.sub(r'\s*\d+CD\s*$', '', clean_name, flags=re.IGNORECASE)  # 移除 2CD, 3CD 等
    clean_name = re.sub(r'\s*-\s*Live.*$', '', clean_name, flags=re.IGNORECASE)  # 移除 - Live 等

    # 尝试提取 "艺术家 - 专辑" 格式
    if ' - ' in clean_name:
        parts = clean_name.split(' - ')
        if len(parts) > 1:
            return parts[0].strip()

    # 尝试提取 "艺术家：专辑" 格式
    if ':' in clean_name:
        parts = clean_name.split(':')
        if len(parts) > 1:
            return parts[0].strip()

    # 如果目录名以人名开头（包含空格和西文字符）
    match = re.match(r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s*,?\s*[A-Z][a-z]+)?)', clean_name)
    if match:
        return match.group(1).strip()

    return clean_name[:50]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', '-p', default='.')
    parser.add_argument('--port', type=int, default=9222)
    parser.add_argument('--limit', '-l', type=int, default=0,
                        help='限制处理数量（默认不限制）')
    parser.add_argument('--skip-processed', '-s', action='store_true', default=False,
                        help='只处理未处理的目录（跳过已处理记录中的目录）')

    args = parser.parse_args()

    print("="*60)
    print("豆瓣音乐批量处理 - Chrome DevTools")
    print("="*60)
    print()
    print("注意：脚本会自动添加随机延迟以避免豆瓣的反机器人检测")
    print("如果检测到反机器人页面，脚本会自动跳过该专辑")
    print()

    bot = DoubanChromeBot(args.port)
    if not bot.connect():
        print("连接 Chrome 失败，请确保 Chrome 已启动并带有 --remote-debugging-port=9222")
        sys.exit(1)

    if not bot.find_douban_page():
        print("未找到豆瓣音乐页面，请先在 Chrome 中访问 https://music.douban.com")
        sys.exit(1)

    print("已连接到豆瓣音乐页面")

    # 导航到豆瓣音乐主页
    print("导航到豆瓣音乐主页...")
    bot.navigate("https://music.douban.com/")
    time.sleep(5)

    # 检查并等待反机器人验证清除
    print("检查反机器人状态...")
    if bot.check_bot_detection():
        print("=" * 60)
        print("检测到反机器人验证！")
        print("请在浏览器中完成验证码，然后脚本将自动继续...")
        print("=" * 60)
        for _ in range(24):  # 等待最多 2 分钟
            time.sleep(5)
            if not bot.check_bot_detection():
                print("验证已完成，继续处理...")
                break
        else:
            print("等待验证超时，但将继续尝试...")

    if not bot.check_login():
        print("未检测到登录状态，等待用户登录...")
        for _ in range(15):
            time.sleep(2)
            if bot.check_login():
                break
        else:
            print("仍未检测到登录，但将继续尝试...")

    print("已登录豆瓣")

    # 加载已处理的 barcode 记录（持久化去重）
    processed_file = Path(__file__).parent / "processed_barcodes.txt"
    processed_barcodes = set()
    if processed_file.exists():
        with open(processed_file, 'r', encoding='utf-8') as f:
            processed_barcodes = set(line.strip() for line in f if line.strip())
        print(f"\n已加载 {len(processed_barcodes)} 个已处理的 barcode 记录\n")

    # 加载已处理的目录记录（防止无 barcode 专辑重复处理）
    processed_dirs_file = Path(__file__).parent / "processed_dirs.log"
    processed_dirs = set()
    if processed_dirs_file.exists():
        with open(processed_dirs_file, 'r', encoding='utf-8') as f:
            processed_dirs = set(line.strip() for line in f if line.strip())
        print(f"已加载 {len(processed_dirs)} 个已处理的目录记录\n")

    # 获取专辑
    base = Path(args.path)

    # 检查是否直接指定了专辑目录（包含专辑基本信息.md）
    if (base / "专辑基本信息.md").exists():
        dirs = [base]
    else:
        all_dirs = sorted([d for d in base.iterdir() if d.is_dir() and not d.name.startswith('.') and d.name != 'scripts'])

        # 如果指定了 --skip-processed，只保留未处理的目录
        if args.skip_processed:
            # 过滤掉已处理的目录和 barcode 已处理的目录
            filtered_dirs = []
            skipped_barcodes = 0
            skipped_dirs = 0
            for d in all_dirs:
                album = parse_album_file(str(d))
                if not album or (not album.get('title') and not album.get('artist')):
                    continue  # 跳过无有效信息的目录

                barcode = album.get('barcode', '')
                dir_name = d.name

                # 检查是否已处理
                if dir_name in processed_dirs:
                    skipped_dirs += 1
                    continue
                if barcode and barcode in processed_barcodes:
                    skipped_barcodes += 1
                    continue

                filtered_dirs.append(d)

            remaining = len(filtered_dirs)
            dirs = filtered_dirs
            print(f"总目录数：{len(all_dirs)}, 已处理 (目录): {len(processed_dirs)}, 已处理 (barcode): {skipped_barcodes}, 待处理：{remaining}")
            print(f"\n将处理 {remaining} 个未处理的专辑\n")
        else:
            dirs = all_dirs

        # 只有当用户明确指定了 limit 参数时才限制数量
        if args.limit and args.limit > 0 and args.limit != 5:
            dirs = dirs[:args.limit]

    print(f"\n将处理 {len(dirs)} 个专辑\n")

    # 跟踪本次运行已处理的记录和目录
    run_processed_barcodes = set()
    run_processed_titles = set()
    run_processed_dirs = set()

    # 跟踪有问题的专辑（记录到文件）
    failed_albums = []
    failed_albums_file = Path(__file__).parent / "failed_albums.log"

    # 处理每个专辑
    success_count = 0
    skip_count = 0
    fail_count = 0
    for i, directory in enumerate(dirs, 1):
        try:
            album = parse_album_file(str(directory))
        except Exception as e:
            print(f"[{i}/{len(dirs)}] 跳过（解析失败：{e}）")
            failed_albums.append({
                'dir_name': directory.name,
                'title': 'N/A',
                'reason': f'专辑信息文件解析失败：{e}'
            })
            fail_count += 1
            continue

        if not album or (not album['title'] and not album['artist']):
            print(f"[{i}/{len(dirs)}] 跳过（无有效信息）")
            failed_albums.append({
                'dir_name': directory.name,
                'title': 'N/A',
                'reason': '专辑信息文件缺失或无有效信息'
            })
            fail_count += 1
            continue

        # 生成目录名作为唯一标识
        dir_name = directory.name

        # 检查 barcode 是否已处理
        barcode = album.get('barcode', '')
        title_key = (album.get('title', '') or '')[:50].lower().strip()

        # 检查持久化去重（barcode 或目录名）
        if barcode and barcode in processed_barcodes:
            print(f"[{i}/{len(dirs)}] 跳过（barcode {barcode} 已处理）")
            skip_count += 1
            continue

        if dir_name in processed_dirs:
            print(f"[{i}/{len(dirs)}] 跳过（目录 {dir_name} 已处理）")
            skip_count += 1
            continue

        # 检查本次运行是否已处理
        if barcode and barcode in run_processed_barcodes:
            print(f"[{i}/{len(dirs)}] 跳过（barcode {barcode} 本次已处理）")
            skip_count += 1
            continue

        if title_key and title_key in run_processed_titles:
            print(f"[{i}/{len(dirs)}] 跳过（专辑已处理）")
            skip_count += 1
            continue

        if dir_name in run_processed_dirs:
            print(f"[{i}/{len(dirs)}] 跳过（目录 {dir_name} 本次已处理）")
            skip_count += 1
            continue

        safe_title = (album['title'] or 'Unknown')[:40]
        print(f"[{i}/{len(dirs)}] {safe_title}...")

        # 如果没有艺术家，尝试从目录名中提取
        if not album.get('artist'):
            extracted_artist = extract_artist_from_dirname(dir_name)
            album['artist'] = extracted_artist
            print(f"  从目录名提取艺术家：{extracted_artist}")

        # 标记为已处理
        if barcode:
            run_processed_barcodes.add(barcode)
        if title_key:
            run_processed_titles.add(title_key)
        run_processed_dirs.add(dir_name)

        # 检查反机器人状态
        if bot.check_bot_detection():
            print("  检测到反机器人验证，请先在浏览器中完成验证...")
            if not bot.handle_bot_detection(wait_time=30):
                print("  验证未通过，跳过此专辑")
                failed_albums.append({
                    'dir_name': dir_name,
                    'title': safe_title,
                    'reason': '反机器人验证未通过'
                })
                fail_count += 1
                random_delay(3, 5)
                continue

        # 搜索 - 优先使用 barcode/ISRC
        result_url = bot.search_album(
            album.get('artist'),
            album.get('title'),
            barcode=album.get('barcode'),
            isrc=album.get('isrc')
        )

        if not result_url:
            print("  未找到搜索结果，尝试创建新条目...")

            # 查找封面图片
            cover_path = None
            for cover_name in ['cover.jpg', 'cover.png', 'front.jpg', 'front.png', 'folder.jpg']:
                cover_candidate = Path(directory) / cover_name
                if cover_candidate.exists():
                    cover_path = str(cover_candidate)
                    break

            # 创建新条目
            # 查找封面图片
            cover_path = None
            album_dir = directory
            for cover_name in ['front.jpg', 'cover.jpg', 'folder.jpg', 'front.png', 'cover.png', 'folder.png']:
                cover_candidate = Path(album_dir) / cover_name
                if cover_candidate.exists():
                    cover_path = str(cover_candidate)
                    break

            # 如果没有找到封面，查找 scans 目录中的第一张图片
            if not cover_path:
                scans_dir = Path(album_dir) / 'scans'
                if scans_dir.exists():
                    for img_file in sorted(scans_dir.glob('*.jpg')):
                        cover_path = str(img_file)
                        break
                # 如果 scans 目录也没有，查找 booklet 图片
                if not cover_path:
                    for img_name in ['booklet.jpg', 'booklet.png']:
                        img_candidate = Path(album_dir) / img_name
                        if img_candidate.exists():
                            cover_path = str(img_candidate)
                            break

            try:
                result_url = bot.create_new_album({
                    'title': album.get('title', ''),
                    'artist': album.get('artist', ''),
                    'label': album.get('label', ''),
                    'barcode': album.get('barcode', ''),
                    'year': album.get('year', ''),
                    'catalog_number': album.get('catalog_number', ''),
                    'tracks': album.get('tracks', ''),
                    'description': album.get('description', ''),
                    'discs': album.get('discs', 1),
                    'cover_path': cover_path
                })
            except Exception as e:
                print(f"  创建新条目时出错：{e}")
                failed_albums.append({
                    'dir_name': dir_name,
                    'title': safe_title,
                    'reason': f'创建新条目异常：{str(e)[:100]}'
                })
                fail_count += 1
                random_delay(3, 5)
                continue

            if not result_url:
                print("  创建失败，需要手动操作")
                failed_albums.append({
                    'dir_name': dir_name,
                    'title': safe_title,
                    'reason': '创建新条目失败'
                })
                fail_count += 1
                random_delay(3, 5)
                continue
            else:
                print(f"  已创建新条目：{result_url}")

        # 标记为听过和添加标签
        try:
            bot.mark_as_listened(result_url)

            # 添加标签
            tags = []
            if album['artist']:
                tags.append(album['artist'])
            if album['composers']:
                tags.extend(album['composers'][:2])
            if album['label']:
                tags.append(album['label'])

            # 从标题中提取可能的作曲家
            if album['title']:
                for name in ['Bach', 'Mozart', 'Beethoven', 'Debussy', 'Chopin',
                            'Schubert', 'Brahms', 'Tchaikovsky', 'Mahler', 'Wagner']:
                    if name in album['title'] and name not in tags:
                        tags.append(name)

            if tags:
                bot.add_tags(tags[:5])  # 最多 5 个标签

            success_count += 1
            # 成功处理后，记录目录名到持久化文件
            run_processed_dirs.add(dir_name)
        except Exception as e:
            print(f"  标记听过或添加标签时出错：{e}，但专辑已创建")
            # 即使标记失败，专辑已创建也算部分成功
            run_processed_dirs.add(dir_name)

        # 专辑间延迟 - 更重要
        print(f"  等待 {random.randint(5, 10)} 秒后处理下一个专辑...")
        random_delay(5, 10)

    # 保存已处理的 barcode 记录（持久化）
    if run_processed_barcodes:
        processed_barcodes.update(run_processed_barcodes)
        with open(processed_file, 'w', encoding='utf-8') as f:
            for barcode in sorted(processed_barcodes):
                f.write(f"{barcode}\n")
        print(f"\n已保存 {len(run_processed_barcodes)} 个新处理的 barcode 记录到 {processed_file}")

    # 保存已处理的目录记录（持久化，防止无 barcode 专辑重复处理）
    if run_processed_dirs:
        processed_dirs.update(run_processed_dirs)
        with open(processed_dirs_file, 'w', encoding='utf-8') as f:
            for dir_name in sorted(processed_dirs):
                f.write(f"{dir_name}\n")
        print(f"已保存 {len(run_processed_dirs)} 个新处理的目录记录到 {processed_dirs_file}")

    # 保存有问题的专辑记录
    if failed_albums:
        with open(failed_albums_file, 'a', encoding='utf-8') as f:
            for item in failed_albums:
                f.write(f"{item['dir_name']}\t{item['reason']}\t{item['title']}\n")
        print(f"\n有问题的专辑已记录到：{failed_albums_file}")

    print("\n" + "="*60)
    print("处理完成!")
    print("="*60)
    print(f"成功：{success_count} 专辑")
    print(f"跳过：{skip_count} 专辑")
    print(f"失败：{fail_count} 专辑")


if __name__ == '__main__':
    main()
