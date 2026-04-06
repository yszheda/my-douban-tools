# 豆瓣音乐批量处理 - Chrome DevTools 方案

## 优势

使用 Chrome DevTools MCP/Protocol 可以：
- **复用你已登录的 Chrome 会话** - 不需要 Cookie、不会触发反爬虫
- **稳定可靠** - 直接使用浏览器原生 API
- **实时可见** - 可以看到操作过程，随时干预

---

## 方法一：使用 Chrome DevTools MCP（推荐）

### 步骤 1: 启动 Chrome 并开启调试端口

**Windows 命令行**：
```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=%TEMP%\chrome-douban https://music.douban.com
```

**或者使用脚本启动**：
```bash
python scripts/start_chrome.py
```

### 步骤 2: 在 Chrome 中登录豆瓣

在打开的浏览器中访问 https://music.douban.com 并登录你的账号

### 步骤 3: 使用 MCP 控制浏览器

如果你已配置好 Chrome DevTools MCP，可以直接对我说：

```
请使用 Chrome DevTools 帮我在豆瓣音乐上标记这些专辑为已听
```

我会使用 MCP 工具来控制你已登录的浏览器。

---

## 方法二：使用 Python 脚本（简单）

### 安装依赖

```bash
pip install websocket-client requests
```

### 启动 Chrome

同上，先启动带调试端口的 Chrome

### 运行脚本

```bash
# 测试前 5 个专辑
python scripts/douban_chrome_simple.py --limit 5

# 处理更多
python scripts/douban_chrome_simple.py --limit 50
```

---

## 方法三：半自动链接生成（最稳定）

完全手动操作，但脚本帮你生成所有搜索链接：

```bash
python scripts/generate_search_links.py
```

然后在浏览器中打开生成的 `search_links.html`，批量点击搜索。

---

## 常见问题

### Q: 如何确认 Chrome 已正确启动？

访问 http://127.0.0.1:9222/json/version 能看到浏览器信息

### Q: 多个 Chrome 窗口怎么办？

脚本会自动连接到包含豆瓣音乐的窗口

### Q: 触发了验证码怎么办？

Chrome DevTools 方案不会触发验证码，因为使用的是真实用户会话

---

## 脚本文件

| 文件 | 用途 |
|------|------|
| `douban_chrome_simple.py` | 简单 Python 脚本，直接控制 Chrome |
| `douban_chrome_mcp.py` | 完整的 MCP 方案 |
| `generate_search_links.py` | 生成半自动搜索链接页面 |
| `start_chrome.py` | Chrome 启动脚本 |

---

## 快速开始

1. 启动 Chrome: `python scripts/start_chrome.py`
2. 登录豆瓣音乐
3. 运行处理：`python scripts/douban_chrome_simple.py --limit 5`
