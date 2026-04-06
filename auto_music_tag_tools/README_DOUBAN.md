# 豆瓣音乐自动化脚本使用指南

## ⚠️ 重要提示

豆瓣音乐**没有官方 API**，此脚本使用浏览器自动化技术。使用时请注意：

1. **遵守豆瓣服务条款** - 仅用于个人数据管理
2. **避免高频访问** - 脚本已添加延迟，不要修改
3. **可能触发验证码** - 如遇到验证码，需要手动完成

## 安装步骤

### 1. 安装 Python 依赖

```bash
# 安装 playwright
pip install playwright

# 安装浏览器 (Chromium)
playwright install chromium
```

### 2. 获取豆瓣 Cookie

**方法一：使用浏览器开发者工具**

1. 打开浏览器 (Chrome/Edge)
2. 访问 https://music.douban.com 并登录你的账号
3. 按 `F12` 打开开发者工具
4. 切换到 **Application** (或 **存储**) 标签
5. 展开 **Cookies** -> 选择 `https://music.douban.com`
6. 找到以下 Cookie 值：
   - `dbcl2` (最重要)
   - `gr`
   - `ck`
   - `douban-fav-remind`
7. 复制这些值，格式如下：
   ```
   dbcl2=你的值; gr=你的值; ck=你的值; douban-fav-remind=你的值
   ```

**方法二：使用 JavaScript 快速获取**

在豆瓣音乐页面打开控制台 (F12 -> Console)，粘贴以下代码并回车：

```javascript
console.log('dbcl2=' + document.cookie.split('dbcl2=')[1]?.split(';')[0] + '; ' +
            'gr=' + document.cookie.split('gr=')[1]?.split(';')[0] + '; ' +
            'ck=' + document.cookie.split('ck=')[1]?.split(';')[0]);
```

复制输出结果。

### 3. 保存 Cookie

将获取的 Cookie 保存到文件：

```bash
# 在脚本同目录下创建 douban_cookie.txt
# 将 Cookie 粘贴进去并保存
```

## 使用方法

### 基本用法

```bash
# 处理当前目录下所有专辑
python scripts/douban_automation.py

# 处理指定目录
python scripts/douban_automation.py --path "C:/Users/xxx/Music"

# 使用 Cookie 文件
python scripts/douban_automation.py --cookie-file douban_cookie.txt

# 无头模式 (不显示浏览器)
python scripts/douban_automation.py --headless

# 仅标记已存在的条目，不创建新条目
python scripts/douban_automation.py --no-create

# 限制处理数量 (测试用)
python scripts/douban_automation.py --limit 10

# 指定输出文件
python scripts/douban_automation.py -o results.json
```

### 完整参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--path, -p` | 专辑目录路径 | 当前目录 |
| `--cookie, -c` | Cookie 字符串 | 从文件读取 |
| `--cookie-file` | Cookie 文件路径 | douban_cookie.txt |
| `--headless` | 无头模式 | 显示浏览器 |
| `--no-create` | 不创建新条目 | 创建 |
| `--output, -o` | 结果输出文件 | douban_results.json |
| `--limit, -l` | 限制处理数量 | 全部 |

## 输出结果

脚本会生成 `douban_results.json` 文件，包含每个专辑的处理结果：

```json
[
  {
    "directory": "专辑目录名",
    "title": "专辑标题",
    "artist": "艺术家",
    "status": "marked|created|not_found",
    "url": "豆瓣条目 URL",
    "message": "处理信息"
  }
]
```

### 状态说明

| 状态 | 说明 |
|------|------|
| `marked` | 已找到并标记为"已听" |
| `created` | 已创建新条目 (需要豆瓣管理员审核) |
| `not_found` | 未找到匹配，需要手动创建 |

## 工作流程

对于每个专辑目录：

1. **读取信息** - 从 `专辑基本信息.md` 提取标题、艺术家、厂牌等
2. **搜索豆瓣** - 使用艺术家 + 标题搜索
3. **匹配验证** - 计算匹配度，避免误标记
4. **标记已听** - 点击"听过"按钮
5. **添加标签** - 添加艺术家、厂牌、作曲家等标签
6. **创建条目** - 如未找到，尝试创建 (目前豆瓣限制较多，建议手动)

## 注意事项

### 1. 匹配算法

脚本会计算搜索结果的匹配度：
- 标题包含或完全匹配：+0.5
- 艺术家包含或完全匹配：+0.5
- 部分单词匹配：+0.3

匹配度低于 0.3 的结果会被跳过。

### 2. 反爬虫延迟

- 每个专辑处理间隔：3 秒
- 搜索超时：30 秒
- 操作超时：30 秒

### 3. 常见问题

**Q: 提示 Cookie 无效**
A: Cookie 可能已过期，请重新获取。豆瓣 Cookie 有效期一般为几天。

**Q: 触发验证码**
A: 暂停脚本，在浏览器中手动完成验证码，等待一段时间后再继续。

**Q: 标记失败**
A: 豆瓣页面结构可能已更新，需要更新脚本中的选择器。

**Q: 创建条目失败**
A: 豆瓣音乐目前不支持用户直接创建条目，需要提交至：https://music.douban.com/new_subject

## 标签规则

脚本会自动生成以下标签：

1. **艺术家名** - 从专辑信息提取
2. **厂牌名** - 如 "DG", "Philips", "ECM" 等
3. **作曲家名** - 从曲目列表提取，最多 3 个

你可以根据需要修改 `parse_album_file` 方法中的标签生成逻辑。

## 手动处理未找到的专辑

对于未找到的专辑，建议手动在豆瓣创建：

1. 访问 https://music.douban.com/new_subject
2. 填写专辑信息：
   - 专辑名
   - 艺术家
   - 厂牌
   - 发行日期
   - 曲目列表
3. 上传封面图片
4. 提交等待审核

## 批量处理建议

由于有 370+ 个专辑，建议：

1. **先测试** - 使用 `--limit 5` 测试几个专辑
2. **分段处理** - 按字母顺序分批处理
3. **监控状态** - 定期检查是否有验证码
4. **保存进度** - 结果文件会记录处理状态

### 分批处理示例

```bash
# 处理 A 开头的专辑
python scripts/douban_automation.py --path "C:/.../classical-music-db" --limit 50

# 查看结果
cat douban_results.json | python -c "import json,sys; data=json.load(sys.stdin); print(f'已处理：{len(data)}')"
```

## 故障排除

### 启用调试模式

```bash
# 修改脚本，在 process_album 方法中添加：
print(f"DEBUG: 搜索词={query}")
print(f"DEBUG: 页面 URL={self.page.url}")
```

### 查看浏览器日志

不使用 `--headless` 参数，可以观察浏览器操作过程。

### 检查 Python 版本

```bash
python --version  # 需要 Python 3.7+
```

### 重新安装 Playwright

```bash
pip uninstall playwright
pip install playwright
playwright install chromium
```

## 扩展功能

如需添加功能，可以修改 `douban_automation.py`：

- **添加评分** - 在 `process_album` 中添加评分逻辑
- **添加评论** - 自动或手动添加评论
- **导出歌单** - 生成 Spotify/Apple Music 歌单
- **同步其他平台** - 扩展至 Last.fm、MusicBrainz 等

## 相关资源

- [Playwright 文档](https://playwright.dev/python/)
- [豆瓣音乐 API 讨论](https://github.com/zaxlct/douban_music_api) (非官方)
- [豆瓣 Cookie 登录](https://www.douban.com/about)
