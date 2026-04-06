# 豆瓣音乐 MCP 自动标签添加器 - 设计文档

**日期:** 2026-04-07  
**状态:** 用户批准，待实施  
**目标:** 为 6391 张豆瓣音乐专辑自动添加标签

---

## 1. 概述

### 1.1 目标

使用 Chrome DevTools MCP 工具自动化为豆瓣音乐用户的收藏列表（6391 张专辑）批量添加标签。

### 1.2 约束条件

- **执行方式:** 单批次顺序执行（索引 0 → 6390）
- **标签来源:** 10 个数据源（豆瓣、MusicBrainz、Presto Music、Discogs、Last.fm、iTunes、Deezer、Spotify、AllMusic、Wikipedia）
- **每专辑标签上限:** 10 个
- **标签合并规则:** 保留已有标签，新增生成标签（去重）
- **进度管理:** 每 5 张专辑保存一次进度，支持断点续传
- **预计时间:** 约 9 小时（6391 张 × 5 秒/张）

---

## 2. 架构设计

### 2.1 组件架构

```
┌─────────────────────────────────────────────────────────┐
│                   mcp_executor.py                        │
│  (主执行器 - 在 Claude Code 会话中运行)                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │ Album List   │    │   Progress   │    │   Result  │ │
│  │  JSON File   │    │   Manager    │    │   Logger  │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │           Per-Album Processing Loop                  ││
│  │  1. 读取专辑信息 → 2. 生成标签 → 3. 添加标签 → 4. 保存 ││
│  └─────────────────────────────────────────────────────┘│
│                            │                              │
└────────────────────────────┼──────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                              │
    ┌─────────▼─────────┐         ┌────────▼──────────┐
    │  tag_generator.py │         │ MCP Chrome        │
    │  (10 个数据源)      │         │ DevTools Tools    │
    │                   │         │                   │
    │ - Douban          │         │ - navigate_page   │
    │ - MusicBrainz     │         │ - take_snapshot   │
    │ - Presto Music    │         │ - click           │
    │ - Discogs         │         │ - fill            │
    │ - Last.fm         │         │                   │
    │ - iTunes/Deezer   │         │                   │
    │ - Spotify/etc     │         │                   │
    └───────────────────┘         └───────────────────┘
```

### 2.2 数据流

```
专辑列表 JSON
     │
     ▼
┌─────────────────┐
│ 读取专辑 (索引 i) │
└─────────────────┘
     │
     ▼
┌─────────────────┐     ┌──────────────────┐
│ 调用            │────▶│ 10 个数据源查询    │
│ tag_generator   │     │ (Discogs 等)      │
└─────────────────┘     └──────────────────┘
     │
     ▼
生成标签列表 (最多 10 个)
     │
     ▼
┌─────────────────┐
│ 合并已有标签     │ (如有)
└─────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│        MCP 浏览器操作流程                │
│                                         │
│  navigate_page(url)                     │
│       │                                 │
│       ▼                                 │
│  take_snapshot() → 找"修改"按钮         │
│       │                                 │
│       ▼                                 │
│  click(modify_uid)                      │
│       │                                 │
│       ▼                                 │
│  take_snapshot() → 找输入框             │
│       │                                 │
│       ▼                                 │
│  fill(input_uid, tags)                  │
│       │                                 │
│       ▼                                 │
│  take_snapshot() → 找"保存"按钮         │
│       │                                 │
│       ▼                                 │
│  click(save_uid)                        │
│                                         │
└─────────────────────────────────────────┘
     │
     ▼
┌─────────────────┐
│ 保存结果         │
└─────────────────┘
     │
     ▼
每 5 张保存进度到 mcp_executor_progress.json
```

---

## 3. 详细设计

### 3.1 主执行器 (`mcp_executor.py`)

**职责:**
- 加载专辑列表
- 加载/保存进度
- 调用标签生成器
- 调用 MCP 工具添加标签
- 记录结果和日志

**核心方法:**
```python
class McpExecutor:
    def __init__(self, cookie_file="cookie.txt", album_list_file="album_list_full.json"):
        self.tag_generator = DoubanMusicTagGenerator(cookie_file)
        self.albums = self._load_album_list()
        self.progress = self._load_progress()

    def _load_album_list(self) -> List[Dict]:
        """加载专辑列表"""

    def _load_progress(self) -> Dict:
        """加载进度文件"""

    def _save_progress(self):
        """保存进度到 mcp_executor_progress.json"""

    def generate_tags(self, subject_id: str, album_info: Dict) -> List[str]:
        """调用标签生成器"""

    def add_tags_via_mcp(self, subject_id: str, tags: List[str]) -> Dict:
        """使用 MCP 工具添加标签"""

    def process_album(self, album: Dict, index: int) -> Dict:
        """处理单张专辑"""

    def run(self, start_index: int = None, end_index: int = None):
        """主执行循环"""
```

### 3.2 标签生成流程

调用 `auto_gen_music_tags/tag_generator.py` 的 `DoubanMusicTagGenerator.generate_tags()` 方法：

```python
tagger = DoubanMusicTagGenerator(cookie_file)
result = tagger.generate_tags(subject_id, album_info, verbose=False)
tags = result.get('tags_all', [])[:10]  # 限制最多 10 个
```

### 3.3 MCP 浏览器操作流程

```python
def add_tags_via_mcp(self, subject_id: str, tags: List[str]) -> Dict:
    url = f"https://music.douban.com/subject/{subject_id}/"
    
    # Step 1: 导航
    mcp__chrome-devtools__navigate_page(url=url, type="url")
    time.sleep(2)
    
    # Step 2: 找"修改"按钮
    snapshot = mcp__chrome-devtools__take_snapshot()
    modify_uid = self._find_modify_button(snapshot)
    
    # Step 3: 点击修改
    mcp__chrome-devtools__click(uid=modify_uid)
    time.sleep(1)
    
    # Step 4: 找输入框并读取已有标签
    snapshot = mcp__chrome-devtools__take_snapshot()
    input_uid = self._find_tag_input(snapshot)
    existing_tags = self._extract_existing_tags(snapshot)
    
    # Step 5: 合并标签
    all_tags = list(set(existing_tags + tags))[:10]
    
    # Step 6: 填充标签
    mcp__chrome-devtools__fill(uid=input_uid, value=' '.join(all_tags))
    time.sleep(0.5)
    
    # Step 7: 找保存按钮
    snapshot = mcp__chrome-devtools__take_snapshot()
    save_uid = self._find_save_button(snapshot)
    
    # Step 8: 点击保存
    mcp__chrome-devtools__click(uid=save_uid)
    time.sleep(1.5)
    
    return {'success': True, 'tags': all_tags}
```

### 3.4 进度管理

**进度文件:** `mcp_executor_progress.json`

**结构:**
```json
{
  "started_at": "2026-04-07T10:00:00",
  "last_updated": "2026-04-07T18:00:00",
  "current_index": 1234,
  "processed_count": 1234,
  "success_count": 1200,
  "failed_count": 34,
  "results": [
    {
      "index": 0,
      "subject_id": "26637659",
      "title": "Early North American Orchestra...",
      "tags": ["Classical", "Mozart", "..."],
      "success": true,
      "processed_at": "2026-04-07T10:00:05"
    }
  ],
  "failed": [
    {
      "index": 123,
      "subject_id": "xxx",
      "reason": "未找到修改按钮"
    }
  ]
}
```

**保存频率:** 每处理 5 张专辑保存一次

---

## 4. 错误处理

### 4.1 预期错误类型

| 错误类型 | 处理方式 |
|----------|----------|
| 标签生成失败 | 记录到 failed 列表，继续下一张 |
| 未找到"修改"按钮 | 记录到 failed 列表，继续下一张 |
| 未找到输入框 | 记录到 failed 列表，继续下一张 |
| 未找到"保存"按钮 | 记录到 failed 列表，继续下一张 |
| Cookie 过期 | 暂停，等待用户更新 Cookie 后手动恢复 |
| 网络超时 | 重试 3 次，失败则记录到 failed 列表 |

### 4.2 恢复机制

- **自动恢复:** 从 `mcp_executor_progress.json` 读取 `current_index`，从该索引继续
- **手动恢复:** 运行 `python mcp_executor.py --resume`

---

## 5. 输出文件

| 文件 | 说明 |
|------|------|
| `mcp_executor_progress.json` | 实时进度文件（每 5 张更新） |
| `mcp_executor_result.json` | 最终结果（完成后生成） |
| `mcp_executor_tags.json` | 所有标签汇总（完成后生成） |

---

## 6. 成功标准

- **成功率:** ≥ 90% (至少 5750 张专辑成功添加标签)
- **旧标签保留:** 编辑时正确合并已有标签
- **进度可恢复:** 中断后可从断点继续

---

## 7. 监控方式

**日志输出格式:**
```
[1/6391] 处理：26637659 - Early North American Orchestra...
  [Step 1] 生成标签... 生成 8 个标签
  [Step 2] 导航到专辑页面...
  [Step 3] 查找修改按钮... uid=1_91
  [Step 4] 点击修改按钮...
  [Step 5] 查找标签输入框... uid=2_18
  [Step 6] 填充标签...
  [Step 7] 查找保存按钮... uid=2_66
  [Step 8] 点击保存按钮...
  [OK] 完成!
[DELAY] 等待 5 秒...

[CHECKPOINT] 已处理 5 张，保存进度...
```

---

## 8. 时间估算

| 阶段 | 时间 |
|------|------|
| 每专辑标签生成 | ~2 秒 |
| 每专辑浏览器操作 | ~3 秒 |
| 每专辑总计 | ~5 秒 |
| 6391 张专辑总计 | ~8.9 小时 |
| 加上延迟和错误处理 | ~10-12 小时 |

---

## 9. 文件清单

**新建文件:**
- `mcp_executor.py` - 主执行器

**修改文件:**
- 无（复用现有 `tag_generator.py` 和 MCP 工具）

**依赖文件:**
- `album_list_full.json` - 专辑列表
- `cookie.txt` - 豆瓣 Cookie

---

## 10. 执行命令

```bash
# 首次运行（从头开始）
python mcp_executor.py

# 从断点恢复
python mcp_executor.py --resume

# 指定范围
python mcp_executor.py --start 0 --end 100
```
