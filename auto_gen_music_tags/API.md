# API 文档

## 模块导出

```python
from auto_gen_music_tags import (
    DoubanMusicTagGenerator,
    DoubanBrowserTagAdder,
    DoubanApiTagAdder,
    normalize_name,
    AlbumInfo
)
```

## 标签生成器

### DoubanMusicTagGenerator

#### 初始化

```python
tagger = DoubanMusicTagGenerator(cookie_file: str = "cookie.txt")
```

**参数：**
- `cookie_file` - Cookie 文件路径，用于豆瓣认证

#### 生成标签

```python
result = tagger.generate_tags(
    subject_id: str,
    album_info: Dict = None,
    verbose: bool = True
) -> Dict
```

**参数：**
- `subject_id` - 豆瓣音乐专辑 ID（如 "35617623"）
- `album_info` - 可选的额外专辑信息
- `verbose` - 是否输出详细信息

**返回值：**
```python
{
    'subject_id': str,
    'album_title': str,
    'sources': Dict,         # 各数据源查询结果
    'tags_by_category': Dict,  # 按分类的标签
    'tags_all': List[str],     # 完整标签列表
    'tags_summary': str        # 空格分隔的标签字符串
}
```

**示例：**
```python
from auto_gen_music_tags import DoubanMusicTagGenerator

tagger = DoubanMusicTagGenerator()
result = tagger.generate_tags("35617623")
print(result['tags_all'])
# ['Alkan', 'Chamber', 'Chopin', 'Classical', ...]
```

#### 保存结果

```python
tagger.save_results(output_file: str = None) -> Dict
```

**参数：**
- `output_file` - 输出文件路径，默认为 `tags_{subject_id}.json`

#### AlbumInfo 数据类

```python
@dataclass
class AlbumInfo:
    subject_id: str
    title: str = ""
    performers: List[str] = None
    composers: List[str] = None
    label: str = ""
    year: str = ""
    barcode: str = ""
```

#### normalize_name 工具函数

```python
normalize_name(name: str) -> str
```

**功能：** 移除人名中的重音符号，转换为 ASCII

**示例：**
```python
normalize_name("Frédéric Chopin")  # "FredericChopin"
normalize_name("Tatjana Vassiljeva")  # "TatjanaVassiljeva"
```

## 标签添加器

### DoubanBrowserTagAdder

浏览器模拟版标签添加器，使用 Chrome DevTools MCP 工具。

#### 初始化

```python
adder = DoubanBrowserTagAdder()
```

#### 添加标签

```python
result = adder.add_tags(
    subject_id: str,
    tags: List[str]
) -> Dict
```

**参数：**
- `subject_id` - 豆瓣音乐专辑 ID
- `tags` - 标签列表

**返回值：**
```python
{
    'success': bool,
    'message': str,
    'subject_id': str
}
```

**示例：**
```python
from auto_gen_music_tags import DoubanBrowserTagAdder

adder = DoubanBrowserTagAdder()
tags = ['Chopin', 'Classical', 'Cello', 'Piano']
result = adder.add_tags("35617623", tags)

if result['success']:
    print("标签添加成功")
else:
    print(f"失败：{result['message']}")
```

### DoubanApiTagAdder

API 版标签添加器，通过 HTTP POST 请求直接调用豆瓣 API。

#### 初始化

```python
adder = DoubanApiTagAdder(cookie_file: str = "cookie.txt")
```

#### 添加单个标签

```python
success = adder.add_tag(subject_id: str, tag: str) -> bool
```

#### 批量添加标签

```python
result = adder.add_tags(
    subject_id: str,
    tags: List[str],
    delay: float = 1.0
) -> Dict
```

**参数：**
- `delay` - 标签之间的延迟（秒）

**返回值：**
```python
{
    'success': List[str],   # 成功的标签
    'failed': List[str]     # 失败的标签
}
```

## 配置模块

```python
from auto_gen_music_tags.config import (
    TAGS_PER_ALBUM_LIMIT,    # = 10
    TAG_MIN_LENGTH,          # = 2
    TAG_MAX_LENGTH,          # = 50
    TIMEOUT_DOUBAN,          # = 10
    TIMEOUT_MUSICBRAINZ,     # = 10
    # ...
)
```

## 完整示例

### 生成并添加标签

```python
from auto_gen_music_tags import (
    DoubanMusicTagGenerator,
    DoubanBrowserTagAdder
)

# Step 1: 生成标签
tagger = DoubanMusicTagGenerator()
result = tagger.generate_tags("35617623")

# Step 2: 保存结果到 JSON
tagger.save_results()

# Step 3: 添加标签到豆瓣
adder = DoubanBrowserTagAdder()
tags_to_add = result['tags_all'][:10]  # 豆瓣限制最多 10 个
add_result = adder.add_tags("35617623", tags_to_add)

if add_result['success']:
    print("标签添加成功!")
else:
    print(f"失败：{add_result['message']}")
```

### 自定义专辑信息

```python
from auto_gen_music_tags import DoubanMusicTagGenerator

tagger = DoubanMusicTagGenerator()

album_info = {
    'title': 'Chopin: Cello Sonata Op.65',
    'performers': ['Tatjana Vassiljeva', 'Jean-Frederic Neuburger'],
    'composers': ['Frédéric Chopin'],
    'label': 'Mirare',
    'year': '2016'
}

result = tagger.generate_tags(
    "35617623",
    album_info=album_info
)
```

## 错误处理

```python
from auto_gen_music_tags import DoubanMusicTagGenerator

tagger = DoubanMusicTagGenerator()

try:
    result = tagger.generate_tags("35617623")
    if not result['tags_all']:
        print("未生成任何标签")
except Exception as e:
    print(f"生成失败：{e}")
```

## 注意事项

1. **标签数量限制：** 豆瓣每专辑最多 10 个标签
2. **Cookie 有效期：** ck 值会过期，失败请重新获取
3. **网络超时：** 国际 API 可能需要特殊网络环境
4. **标签编辑规则：** 只能增加标签，不能删除旧标签或短评
