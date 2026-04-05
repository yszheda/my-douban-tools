# 豆瓣音乐标签生成器 - 设计文档

## 项目概述

豆瓣音乐标签自动生成工具，为豆瓣音乐专辑添加标准化的古典音乐标签。支持 10 个外部数据源查询，包含 API 版和浏览器模拟版两种标签添加方式。

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    用户/调用方                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
         ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │   demo   │ │  手动调用 │ │ 批量处理  │
   │  .py     │ │          │ │          │
   └────┬─────┘ └────┬─────┘ └────┬─────┘
        │            │            │
        └────────────┼────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌──────────────────┐    ┌──────────────────┐
│  TagGenerator    │    │   Browser/       │
│  (标签生成)      │    │   ApiAdder       │
│                  │    │   (标签添加)     │
└──────────────────┘    └──────────────────┘
        │                         │
        ▼                         ▼
┌──────────────────┐    ┌──────────────────┐
│  10 个数据源查询    │    │   豆瓣页面        │
│  聚合标签数据     │    │   操作模拟        │
└──────────────────┘    └──────────────────┘
```

## 核心模块

### 1. tag_generator.py - 标签生成器

**职责：** 从 10 个数据源聚合标签数据，生成标准化标签列表

**核心类：**
- `DoubanMusicTagGenerator` - 主生成器类
- `AlbumInfo` - 专辑信息数据类
- `normalize_name()` - 人名标准化工具函数

**数据源：**
1. 豆瓣音乐页面 - 基础信息（标题、演奏者、作曲家、厂牌）
2. MusicBrainz API - 作品和演奏家信息
3. Presto Music - 古典音乐专门商店
4. Discogs - 唱片数据库
5. Last.fm - 标签系统
6. iTunes API - 商业音乐数据库
7. Deezer API - 流媒体数据库
8. Spotify - 流媒体平台
9. AllMusic - 音乐评论数据库
10. Wikipedia - 作曲家传记信息

**标签类别：**
- 演奏家 (Performers) - 姓氏 + 全名无空格
- 作曲家 (Composers) - 姓氏 + 全名无空格
- 厂牌 (Label)
- 风格/类型 (Style/Genre) - 时期、类型、乐器

**排除规则：**
- 国家名称（France, Russia 等）
- 作品号（Op65, KV384, BWV 等）

### 2. browser_adder.py - 浏览器模拟版标签添加

**职责：** 使用 Chrome DevTools MCP 工具模拟人工操作添加标签

**执行流程：**
```
1. navigate_page(url) → 导航到专辑页面
2. take_snapshot() → 查找"修改"按钮 uid
3. click(uid) → 打开修改对话框
4. take_snapshot() → 查找标签输入框 uid
5. 读取现有标签 → 保留旧标签
6. fill(uid, "tag1 tag2 ...") → 填入合并后的标签
7. take_snapshot() → 查找"保存"按钮 uid
8. click(uid) → 保存
9. take_snapshot() → 验证结果
```

**重要规则：**
- 编辑标签时只能增加新标签，不能删除旧标签或短评
- 打开编辑对话框后，先读取输入框中现有的标签
- 将新标签与旧标签合并（去重）后再保存

### 3. api_adder.py - API 版标签添加

**职责：** 通过 HTTP POST 请求直接调用豆瓣标签 API

**特点：**
- 快速但不稳定，可能被豆瓣反爬机制阻止
- 需要有效的 cookie 和 ck 值进行认证

## 数据流

```
subject_id → TagGenerator.generate_tags()
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
_douban    _musicbrainz   _presto
    │            │            │
    ▼            ▼            ▼
_discogs   _lastfm      _itunes
    │            │            │
    ▼            ▼            ▼
_deezer    _spotify     _allmusic
    │            │
    ▼            ▼
_wikipedia → _generate_standardized_tags()
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
_performers  _composers   _label
    │
    ▼
_style → _clean_and_filter_tags() → tags_all[]
```

## 标签标准化规则

### 人名处理
```
输入："Frédéric Chopin"
     ↓ normalize_name()
输出："FredericChopin"
```

### 演奏家标签格式
```
输入：["Tatjana Vassiljeva", "Jean-Frederic Neuburger"]

输出：
- 姓氏：Vassiljeva, Neuburger
- 全名无空格：TatjanaVassiljeva, JeanFredericNeuburger
- 标准化全名：TatjanaVassiljeva, JeanFredericNeuburger
```

### 作曲家标签格式
```
输入：["Frédéric Chopin", "Charles-Valentin Alkan"]

输出：
- 姓氏：Chopin, Alkan
- 标准化全名：FredericChopin, CharlesValentinAlkan
```

### 风格/类型标签
固定添加的标签：
- Classical (古典音乐)
- Chamber (室内乐)
- Romantic (浪漫主义)
- Sonata (奏鸣曲)

根据乐器关键词检测：
- Cello, Piano, Violin, Viola, Flute, etc.

## 配置管理 (config.py)

```python
# 超时设置（秒）
TIMEOUT_MUSICBRAINZ = 10
TIMEOUT_PRESTO = 15
TIMEOUT_DISCOGS = 15
...

# 标签限制
TAG_MIN_LENGTH = 2
TAG_MAX_LENGTH = 50
TAGS_PER_ALBUM_LIMIT = 10

# 排除项
EXCLUDE_COUNTRY_NAMES = True
EXCLUDE_OPUS_NUMBERS = True
```

## 输出格式

```json
{
  "generated_at": "2026-04-06T00:26:08.998459",
  "subject_id": "10479791",
  "album_title": "Transfigured Tchaikovsky",
  "album_info": {
    "performers": ["Tatjana Vassiljeva", "Jean-Frederic Neuburger"],
    "composers": ["Frédéric Chopin", "Charles-Valentin Alkan"],
    "label": "Hänssler Classic"
  },
  "tags_by_category": {
    "performers": ["Vassiljeva", "TatjanaVassiljeva", ...],
    "composers": ["Chopin", "FredericChopin", ...],
    "label": ["HansslerClassic"],
    "style": ["Classical", "Chamber", "Romantic", "Sonata"]
  },
  "tags_all": ["Alkan", "Chamber", "Chopin", ...],
  "tags_summary": "Alkan Chamber Chopin Classical..."
}
```

## 版本历史

- v1.0.0 - 初始版本，整合 10 个数据源，包含 API 版和浏览器模拟版
