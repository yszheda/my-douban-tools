# 豆瓣音乐标签自动添加工具

两个版本的标签添加脚本，用于自动为豆瓣音乐专辑添加标签。

## 脚本清单

| 脚本 | 说明 | 使用场景 |
|------|------|----------|
| `add_tags_auto.py` | API 版本，尝试通过 HTTP 请求直接添加 | 快速批量处理，但可能被反机器人机制阻止 |
| `douban_tagger_batch.py` | 浏览器模拟版，调用 Chrome DevTools MCP | 稳定可靠，模拟人工操作，绕过反爬 |

## 版本 1: API 版 (`add_tags_auto.py`)

### 原理
通过 HTTP POST 请求直接调用豆瓣标签 API，不依赖浏览器。

### 使用方法
```bash
python add_tags_auto.py
```

### 配置
编辑脚本中的配置：
```python
SUBJECT_ID = "37133003"  # 专辑 ID
TAGS = ['Mozart', 'JosefKrips', ...]  # 标签列表
```

### 优点
- 执行快速
- 不依赖浏览器

### 缺点
- 可能被豆瓣反机器人机制阻止
- API endpoint 可能变化

---

## 版本 2: 浏览器模拟版 (`douban_tagger_batch.py`)

### 原理
通过 Chrome DevTools MCP 工具模拟人工操作：
1. 导航到专辑页面
2. 点击"修改"按钮
3. 在标签输入框填入标签
4. 点击"保存"

### 使用方法
在 Claude Code 中运行：
```bash
python douban_tagger_batch.py
```

### 配置
```python
SUBJECT_ID = "37133003"  # 专辑 ID
TAGS = ['Mozart', 'JosefKrips', ...]  # 标签列表
```

### 优点
- 稳定可靠
- 绕过反机器人机制
- 可直观看到执行结果

### 缺点
- 需要 Chrome 浏览器
- 需要 Claude Code + MCP 环境

---

## 标签数据来源

标签数据从 `tag_result.json` 读取，该文件由 `classical_tagger.py` 生成。

### 生成标签数据
```bash
python classical_tagger.py
```

这会查询以下数据源：
- Discogs
- MusicBrainz
- Deezer
- iTunes
- Last.fm
- AllMusic

---

## 批量处理

### 获取收藏列表
用户的豆瓣音乐收藏：
- 听过：https://music.douban.com/people/63343218/collect
- 在听：https://music.douban.com/people/63343218/do
- 想听：https://music.douban.com/people/63343218/wish

### 批量处理示例
```python
from douban_tagger_batch import DoubanTaggerBatch

tagger = DoubanTaggerBatch()

# 批量处理
subject_ids = ["37133003", "12345678", ...]
tagger.batch_add(subject_ids, delay=3.0)

# 保存结果
tagger.save_results("results.json")
```

---

## Cookie 配置

脚本需要豆瓣的 cookie 进行认证。

### 获取 cookie
1. 登录豆瓣音乐
2. 打开浏览器开发者工具
3. 复制 cookie 字符串

### 保存 cookie
创建 `cookie.txt` 文件，内容格式：
```
ck=abc123; other_cookie=value; ...
```

---

## 输出结果

执行结果保存到 `tag_add_results.json`：
```json
{
  "processed_at": "2026-04-05T12:00:00",
  "total": 1,
  "success": 1,
  "failed": 0,
  "results": [
    {
      "subject_id": "37133003",
      "tags": ["Mozart", "JosefKrips", ...],
      "success": true,
      "error": ""
    }
  ]
}
```

---

## 注意事项

1. **反机器人机制**: 批量处理时请设置适当的延迟（建议 3 秒以上）
2. **Cookie 有效期**: ck 值会过期，如失败请重新获取
3. **标签数量**: 豆瓣对标签数量有限制，建议不超过 10 个
4. **网络环境**: 部分 API 可能需要特殊网络环境

---

## 故障排除

### API 版本返回 404
- API endpoint 可能已变更
- 改用浏览器模拟版

### 浏览器版本找不到元素
- 页面结构可能已变更
- 重新获取快照检查元素 uid

### 标签未保存成功
- 检查 cookie 是否有效
- 检查 ck 值是否正确
- 尝试手动操作确认流程正常
