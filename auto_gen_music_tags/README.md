# 豆瓣音乐标签自动生成工具

自动化为豆瓣音乐专辑添加标准化标签的工具包。支持 10 个外部数据源查询，包含 API 版和浏览器模拟版两种标签添加方式。

## 功能特点

- **10 个数据源聚合**：豆瓣、MusicBrainz、Presto Music、Discogs、Last.fm、iTunes、Deezer、Spotify、AllMusic、Wikipedia
- **标准化标签**：自动处理人名重音、格式统一
- **智能分类**：演奏家、作曲家、厂牌、风格/类型
- **两种添加方式**：
  - API 版 - 快速但不稳定
  - 浏览器模拟版 - 稳定可靠

## 安装

### 依赖

```bash
pip install requests beautifulsoup4
```

或使用 `requirements.txt`：

```bash
pip install -r requirements.txt
```

### 环境要求

- Python 3.8+
- Chrome 浏览器（浏览器模拟版需要）
- Chrome DevTools MCP（浏览器模拟版需要）

## 快速开始

### 1. 准备 Cookie

从豆瓣音乐页面获取 cookie，保存到 `cookie.txt`：

```
ck=abc123; other_cookie=value; ...
```

### 2. 生成标签

```python
from auto_gen_music_tags import DoubanMusicTagGenerator

# 创建生成器
tagger = DoubanMusicTagGenerator()

# 为专辑生成标签
result = tagger.generate_tags("35617623")

# 查看结果
print(f"标签列表：{result['tags_all']}")
print(f"标签摘要：{result['tags_summary']}")

# 保存到 JSON
tagger.save_results()
```

### 3. 添加标签

#### 方式 A：浏览器模拟版（推荐）

```python
from auto_gen_music_tags import DoubanBrowserTagAdder

adder = DoubanBrowserTagAdder()
tags = result['tags_all'][:10]  # 最多 10 个
add_result = adder.add_tags("35617623", tags)

if add_result['success']:
    print("标签添加成功!")
```

#### 方式 B：API 版

```python
from auto_gen_music_tags import DoubanApiTagAdder

adder = DoubanApiTagAdder()
result = adder.add_tags("35617623", tags, delay=1.5)
print(f"成功：{result['success']}, 失败：{result['failed']}")
```

## 使用演示脚本

```bash
python demo.py
```

演示脚本会：
1. 从 `tags_{subject_id}.json` 加载标签
2. 使用 API 版尝试添加
3. 如果 API 失败，切换到浏览器模拟版

## 配置

编辑 `config.py` 修改配置：

```python
# 超时设置（秒）
TIMEOUT_DOUBAN = 10
TIMEOUT_MUSICBRAINZ = 10

# 标签限制
TAGS_PER_ALBUM_LIMIT = 10  # 豆瓣每专辑最多 10 个

# 排除项
EXCLUDE_COUNTRY_NAMES = True  # 排除国家名
EXCLUDE_OPUS_NUMBERS = True   # 排除作品号
```

## 标签格式

### 输入示例

```python
{
    "title": "Chopin: Cello Sonata Op.65",
    "performers": ["Tatjana Vassiljeva", "Jean-Frederic Neuburger"],
    "composers": ["Frédéric Chopin"],
    "label": "Mirare"
}
```

### 输出标签

```
Alkan Chamber Chopin Classical FredericChopin 
JeanFredericNeuburger Mirare Piano Romantic 
TatjanaVassiljeva Vassiljeva
```

## 标签类别

1. **演奏家 (Performers)** - 姓氏 + 全名无空格
2. **作曲家 (Composers)** - 姓氏 + 全名无空格
3. **厂牌 (Label)** - 唱片公司名称
4. **风格/类型 (Style/Genre)** - 时期、类型、乐器

## 排除规则

以下类型的标签会被自动排除：

- **国家名称**：France, Russia, Polish, German 等
- **作品号**：Op65, Op47, KV384, BWV 等

## 数据源详情

| 数据源 | 类型 | 需要授权 | 超时 |
|--------|------|----------|------|
| 豆瓣音乐 | 网页抓取 | Cookie | 10s |
| MusicBrainz | API | 否 | 10s |
| Presto Music | 网页抓取 | 否 | 15s |
| Discogs | 网页抓取 | 否 | 15s |
| Last.fm | API | 否 | 10s |
| iTunes | API | 否 | 10s |
| Deezer | API | 否 | 10s |
| Spotify | 网页抓取 | 否 | 10s |
| AllMusic | 网页抓取 | 否 | 15s |
| Wikipedia | API | 否 | 10s |

## 运行测试

```bash
# 运行所有测试
python test_all.py

# 运行单个测试
python -m pytest test_tag_generator.py -v
```

## 重要规则

**编辑标签时只能增加新标签，不能删除旧标签或短评。**

浏览器模拟版实现方式：
1. 打开编辑对话框后，先读取输入框中现有的标签
2. 将新标签与旧标签合并（去重）
3. 填充完整标签列表到输入框
4. 保存

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

### 网络超时
- 部分国际 API 可能需要特殊网络环境
- 增加超时配置值

## 项目结构

```
auto_gen_music_tags/
├── __init__.py           # 包初始化
├── config.py             # 配置常量
├── requirements.txt      # 依赖
│
├── tag_generator.py      # 标签生成器
├── browser_adder.py      # 浏览器模拟版
├── api_adder.py          # API 版
├── demo.py               # 演示脚本
│
├── README.md             # 本文件
├── DESIGN.md             # 设计文档
├── API.md                # API 文档
├── CHANGELOG.md          # 版本历史
│
├── test_tag_generator.py # 单元测试
├── test_browser_adder.py # 集成测试
├── test_api_adder.py     # 单元测试
└── test_all.py           # 测试运行器
```

## 许可证

MIT License

## 作者

Galois
