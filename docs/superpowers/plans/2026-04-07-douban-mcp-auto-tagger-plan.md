# 豆瓣音乐 MCP 自动标签添加器实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 6391 张豆瓣音乐专辑自动添加标签，使用 MCP Chrome DevTools 工具浏览器自动化

**Architecture:** 单批次顺序执行，每 5 张专辑保存一次进度，支持断点续传；标签生成复用现有 tag_generator.py，标签添加通过 MCP 工具调用浏览器操作

**Tech Stack:** Python 3.8+, MCP Chrome DevTools, requests, BeautifulSoup4

---

## 文件结构

**新建文件:**
- `mcp_executor.py` - 主执行器（约 200 行）

**复用文件:**
- `auto_gen_music_tags/tag_generator.py` - 标签生成器（10 个数据源）
- `album_list_full.json` - 专辑列表（6391 条）
- `cookie.txt` - 豆瓣 Cookie

**输出文件:**
- `mcp_executor_progress.json` - 进度文件
- `mcp_executor_result.json` - 最终结果

---

### Task 1: 创建 MCP 执行器框架

**Files:**
- Create: `mcp_executor.py`

- [ ] **Step 1: 创建执行器类和初始化方法**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣音乐 MCP 自动标签添加器

使用方法:
    python mcp_executor.py              # 从头开始
    python mcp_executor.py --resume     # 从断点恢复
    python mcp_executor.py --start 0 --end 100  # 指定范围

前提：需要在 Claude Code 环境中运行，使用 MCP Chrome DevTools 工具
"""

import json
import time
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 导入标签生成器
sys.path.insert(0, str(Path(__file__).parent))
from auto_gen_music_tags.tag_generator import DoubanMusicTagGenerator


# ========== 配置常量 ==========
MAX_TAGS_PER_ALBUM = 10  # 每专辑最多标签数
DELAY_BETWEEN_ALBUMS = 5  # 专辑间延迟（秒）
SAVE_INTERVAL = 5  # 每处理 N 张专辑保存一次进度


class McpExecutor:
    """MCP 自动标签添加执行器"""

    def __init__(
        self,
        cookie_file: str = "cookie.txt",
        album_list_file: str = "album_list_full.json",
        progress_file: str = "mcp_executor_progress.json",
        result_file: str = "mcp_executor_result.json"
    ):
        self.cookie_file = cookie_file
        self.album_list_file = album_list_file
        self.progress_file = progress_file
        self.result_file = result_file

        # 初始化标签生成器
        self.tag_generator = DoubanMusicTagGenerator(cookie_file)

        # 加载专辑列表
        self.albums: List[Dict] = []
        self._load_album_list()

        # 进度管理
        self.current_index = 0
        self.success_count = 0
        self.failed_count = 0
        self.results: List[Dict] = []
        self.failed: List[Dict] = []

        # MCP 函数引用（由外部注入）
        self.mcp_navigate = None
        self.mcp_snapshot = None
        self.mcp_click = None
        self.mcp_fill = None
```

- [ ] **Step 2: 添加专辑列表加载和进度管理方法**

```python
    def _load_album_list(self):
        """加载专辑列表"""
        if not Path(self.album_list_file).exists():
            print(f"[ERROR] 专辑列表文件不存在：{self.album_list_file}")
            return

        try:
            with open(self.album_list_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 处理嵌套结构：{collections: {collect: [...]}}
            if isinstance(data, dict) and 'collections' in data:
                self.albums = data['collections'].get('collect', [])
            elif isinstance(data, list):
                self.albums = data
            else:
                self.albums = []

            print(f"[INFO] 加载专辑列表：{len(self.albums)} 条记录")
        except Exception as e:
            print(f"[ERROR] 加载专辑列表失败：{e}")

    def _load_progress(self) -> bool:
        """加载进度"""
        if not Path(self.progress_file).exists():
            print(f"[INFO] 进度文件不存在，从头开始")
            return False

        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.current_index = data.get('current_index', 0)
            self.success_count = data.get('success_count', 0)
            self.failed_count = data.get('failed_count', 0)
            self.results = data.get('results', [])
            self.failed = data.get('failed', [])

            print(f"[INFO] 进度已加载：索引={self.current_index}, 成功={self.success_count}, 失败={self.failed_count}")
            return True
        except Exception as e:
            print(f"[ERROR] 加载进度失败：{e}")
            return False

    def _save_progress(self):
        """保存进度"""
        data = {
            'started_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'current_index': self.current_index,
            'processed_count': self.success_count + self.failed_count,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'results': self.results,
            'failed': self.failed
        }

        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[INFO] 进度已保存：{self.progress_file}")
        except Exception as e:
            print(f"[ERROR] 保存进度失败：{e}")
```

- [ ] **Step 3: 添加标签生成方法**

```python
    def generate_tags(self, subject_id: str, album_info: Dict = None) -> List[str]:
        """为专辑生成标签"""
        try:
            result = self.tag_generator.generate_tags(
                subject_id,
                album_info,
                verbose=False
            )
            tags = result.get('tags_all', [])
            return tags[:MAX_TAGS_PER_ALBUM]
        except Exception as e:
            print(f"[ERROR] 生成标签失败：{e}")
            return []
```

- [ ] **Step 4: 添加 MCP 浏览器操作方法（框架，待注入实际函数）"""

```python
    def _navigate_to_album(self, subject_id: str):
        """导航到专辑页面"""
        url = f"https://music.douban.com/subject/{subject_id}/"
        print(f"[MCP] 导航：{url}")
        if self.mcp_navigate:
            self.mcp_navigate(url=url, type="url")
        time.sleep(2)

    def _take_snapshot(self) -> Dict:
        """获取页面快照"""
        print("[MCP] 获取页面快照...")
        if self.mcp_snapshot:
            return self.mcp_snapshot()
        return {}

    def _click_element(self, uid: str):
        """点击元素"""
        print(f"[MCP] 点击 uid={uid}")
        if self.mcp_click:
            self.mcp_click(uid=uid)

    def _fill_input(self, uid: str, value: str):
        """填充输入框"""
        print(f"[MCP] 填充 uid={uid}, value={value}")
        if self.mcp_fill:
            self.mcp_fill(uid=uid, value=value)
```

- [ ] **Step 5: 添加元素查找方法"""

```python
    def _find_modify_button(self, snapshot_text: str) -> Optional[str]:
        """查找修改按钮"""
        for line in snapshot_text.split('\n'):
            if '修改' in line and 'link' in line:
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        return None

    def _find_tag_input(self, snapshot_text: str) -> Optional[str]:
        """查找标签输入框"""
        lines = snapshot_text.split('\n')
        for i, line in enumerate(lines):
            if 'textbox' in line:
                # 优先查找对话框中的输入框 (uid=2_)
                if 'uid=2_' in line:
                    match = re.search(r'uid=(2_\d+)', line)
                    if match:
                        return match.group(1)
                # 其次查找任意 textbox
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        return None

    def _find_save_button(self, snapshot_text: str) -> Optional[str]:
        """查找保存按钮"""
        for line in snapshot_text.split('\n'):
            if '保存' in line and 'button' in line:
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        return None

    def _extract_existing_tags(self, snapshot_text: str) -> List[str]:
        """从快照中提取已有标签"""
        tags = []
        lines = snapshot_text.split('\n')
        in_tags_section = False
        
        for line in lines:
            if '我的标签' in line or '标签:' in line:
                in_tags_section = True
                continue
            if in_tags_section:
                # 查找标签文本（StaticText 元素）
                if 'StaticText' in line and 'uid=2_' in line:
                    match = re.search(r'StaticText "([^"]+)"', line)
                    if match and match.group(1).strip():
                        tags.append(match.group(1).strip())
                # 遇到输入框后停止
                if 'textbox' in line:
                    break
        return tags
```

- [ ] **Step 6: 提交框架代码**

```bash
git add mcp_executor.py
git commit -m "feat: 创建 MCP 执行器框架"
```

---

### Task 2: 实现标签添加核心逻辑

**Files:**
- Modify: `mcp_executor.py` (添加 add_tags_via_mcp 和 process_album 方法)

- [ ] **Step 1: 添加 MCP 标签添加方法"""

```python
    def add_tags_via_mcp(self, subject_id: str, tags: List[str]) -> Dict:
        """
        使用 MCP Chrome DevTools 工具添加标签

        Returns:
            dict: {'success': bool, 'message': str, 'tags': list}
        """
        result = {'success': False, 'message': '', 'tags': []}

        print(f"\n[MCP] 开始添加标签 - subject={subject_id}")
        print(f"[MCP] 新标签：{' '.join(tags)}")
        print("=" * 60)

        try:
            # Step 1: 导航到专辑页面
            self._navigate_to_album(subject_id)

            # Step 2: 获取快照，找修改按钮
            snapshot = self._take_snapshot()
            snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2)
            
            modify_uid = self._find_modify_button(snapshot_text)
            if not modify_uid:
                result['message'] = '未找到修改按钮'
                print(f"[ERROR] {result['message']}")
                return result
            print(f"[OK] 修改按钮 uid={modify_uid}")

            # Step 3: 点击修改
            self._click_element(modify_uid)
            time.sleep(1)

            # Step 4: 获取快照，找输入框并读取已有标签
            snapshot = self._take_snapshot()
            snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2)
            
            input_uid = self._find_tag_input(snapshot_text)
            if not input_uid:
                result['message'] = '未找到标签输入框'
                print(f"[ERROR] {result['message']}")
                return result
            print(f"[OK] 输入框 uid={input_uid}")

            # 读取已有标签
            existing_tags = self._extract_existing_tags(snapshot_text)
            if existing_tags:
                print(f"[INFO] 已有标签：{' '.join(existing_tags[:5])}...")

            # Step 5: 合并标签（去重）
            all_tags = list(set(existing_tags + tags))[:MAX_TAGS_PER_ALBUM]
            print(f"[INFO] 合并后标签：{' '.join(all_tags)}")

            # Step 6: 填充标签
            tags_str = ' '.join(all_tags)
            self._fill_input(input_uid, tags_str)
            time.sleep(0.5)

            # Step 7: 获取快照，找保存按钮
            snapshot = self._take_snapshot()
            snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2)
            
            save_uid = self._find_save_button(snapshot_text)
            if not save_uid:
                result['message'] = '未找到保存按钮'
                print(f"[ERROR] {result['message']}")
                return result
            print(f"[OK] 保存按钮 uid={save_uid}")

            # Step 8: 点击保存
            self._click_element(save_uid)
            time.sleep(1.5)

            # 成功
            result['success'] = True
            result['message'] = '标签添加成功'
            result['tags'] = all_tags
            print("[OK] 完成!")

            return result

        except Exception as e:
            result['message'] = f'添加标签失败：{e}'
            print(f"[ERROR] {result['message']}")
            return result
```

- [ ] **Step 2: 添加单张专辑处理方法"""

```python
    def process_album(self, album: Dict, index: int) -> Dict:
        """
        处理单张专辑

        Args:
            album: 专辑信息字典
            index: 当前索引

        Returns:
            dict: 处理结果
        """
        subject_id = album.get('subject_id', '')
        title = album.get('title', 'Unknown')

        # 清理标题中的特殊字符
        safe_title = title.encode('utf-8', errors='ignore').decode('utf-8')
        safe_title = safe_title.encode('gbk', errors='ignore').decode('gbk')

        print(f"\n[{index}/{len(self.albums)}] Processing: {safe_title}")
        print(f"            subject={subject_id}")

        result = {
            'index': index,
            'subject_id': subject_id,
            'title': title,
            'success': False,
            'message': '',
            'tags': []
        }

        # Step 1: 生成标签
        print("[Step 1] 生成标签...")
        tags = self.generate_tags(subject_id, album)
        
        if not tags:
            result['message'] = '未生成标签'
            print(f"         [ERROR] {result['message']}")
            return result

        print(f"         生成 {len(tags)} 个标签：{' '.join(tags[:5])}...")

        # Step 2: 添加标签（MCP 浏览器版）
        print("[Step 2] 添加标签...")
        add_result = self.add_tags_via_mcp(subject_id, tags)

        if add_result.get('success', False):
            result['success'] = True
            result['message'] = add_result.get('message', '未知错误')
            result['tags'] = add_result.get('tags', [])
            print(f"         [OK] {result['message']}")
        else:
            result['message'] = add_result.get('message', '未知错误')
            print(f"         [ERROR] {result['message']}")

        return result
```

- [ ] **Step 3: 提交代码"""

```bash
git add mcp_executor.py
git commit -m "feat: 实现标签添加核心逻辑"
```

---

### Task 3: 实现主执行循环

**Files:**
- Modify: `mcp_executor.py` (添加 run 方法和 main 函数)

- [ ] **Step 1: 添加主执行循环方法"""

```python
    def run(self, start_index: int = None, end_index: int = None):
        """
        运行批量处理

        Args:
            start_index: 起始索引（默认从进度文件恢复）
            end_index: 结束索引（默认处理到末尾）
        """
        print("\n" + "=" * 60)
        print("豆瓣音乐 MCP 自动标签添加器")
        print("=" * 60)
        print(f"专辑总数：{len(self.albums)}")

        # 加载进度（断点续传）
        self._load_progress()

        # 设置索引范围
        if start_index is None:
            start_index = self.current_index
        if end_index is None:
            end_index = len(self.albums) - 1

        print(f"起始索引：{start_index}")
        print(f"结束索引：{end_index}")
        print(f"待处理：{end_index - start_index + 1} 张专辑")
        print("=" * 60)

        # 主循环
        for i in range(start_index, min(end_index + 1, len(self.albums))):
            album = self.albums[i]
            subject_id = album.get('subject_id', '')

            # 跳过无效条目
            if not subject_id:
                print(f"\n[{i}] [SKIP] 无效条目，跳过")
                self.failed_count += 1
                self.failed.append({
                    'index': i,
                    'subject_id': '',
                    'title': album.get('title', 'Unknown'),
                    'reason': 'invalid_entry'
                })
                continue

            # 处理专辑
            result = self.process_album(album, i)

            # 更新统计
            self.results.append(result)
            if result['success']:
                self.success_count += 1
            else:
                self.failed_count += 1

            self.current_index = i + 1

            # 定期保存进度（每 SAVE_INTERVAL 张）
            if (self.success_count + self.failed_count) % SAVE_INTERVAL == 0:
                print(f"\n[CHECKPOINT] 已处理 {self.success_count + self.failed_count} 张，保存进度...")
                self._save_progress()

            # 延迟（除了最后一张）
            if i < min(end_index, len(self.albums) - 1):
                print(f"[DELAY] 等待 {DELAY_BETWEEN_ALBUMS} 秒...")
                time.sleep(DELAY_BETWEEN_ALBUMS)

        # 最终保存
        print("\n" + "=" * 60)
        print("批次处理完成")
        print("=" * 60)
        self._save_progress()
        self._save_result()

        # 打印摘要
        self._print_summary()

        return {
            'processed': self.success_count + self.failed_count,
            'success': self.success_count,
            'failed': self.failed_count
        }
```

- [ ] **Step 2: 添加结果保存和摘要方法"""

```python
    def _save_result(self):
        """保存最终结果"""
        result = {
            'completed_at': datetime.now().isoformat(),
            'start_index': 0,
            'end_index': len(self.albums) - 1,
            'processed_count': self.success_count + self.failed_count,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'success_rate': self.success_count / (self.success_count + self.failed_count) if (self.success_count + self.failed_count) > 0 else 0,
            'results': self.results,
            'failed': self.failed
        }

        try:
            with open(self.result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"[INFO] 结果已保存：{self.result_file}")
        except Exception as e:
            print(f"[ERROR] 保存结果失败：{e}")

    def _print_summary(self):
        """打印摘要"""
        total = self.success_count + self.failed_count
        success_rate = self.success_count / total * 100 if total > 0 else 0

        print(f"\n摘要:")
        print(f"  已处理：{total} 张")
        print(f"  成功：{self.success_count} 张")
        print(f"  失败：{self.failed_count} 张")
        print(f"  成功率：{success_rate:.1f}%")
```

- [ ] **Step 3: 添加 main 函数"""

```python
def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='豆瓣音乐 MCP 自动标签添加器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
    python mcp_executor.py              # 从头开始
    python mcp_executor.py --resume     # 从断点恢复
    python mcp_executor.py --start 0 --end 100  # 指定范围
        '''
    )

    parser.add_argument(
        '--cookie',
        type=str,
        default='cookie.txt',
        help='Cookie 文件路径 (默认：cookie.txt)'
    )
    parser.add_argument(
        '--album-list',
        type=str,
        default='album_list_full.json',
        help='专辑列表文件路径 (默认：album_list_full.json)'
    )
    parser.add_argument(
        '--start',
        type=int,
        default=None,
        help='起始索引（默认从进度文件恢复）'
    )
    parser.add_argument(
        '--end',
        type=int,
        default=None,
        help='结束索引（默认处理到末尾）'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='从进度文件恢复（断点续传）'
    )

    args = parser.parse_args()

    # 创建执行器
    executor = McpExecutor(
        cookie_file=args.cookie,
        album_list_file=args.album_list
    )

    # 运行
    executor.run(
        start_index=args.start if not args.resume else None,
        end_index=args.end
    )


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: 提交代码"""

```bash
git add mcp_executor.py
git commit -m "feat: 实现主执行循环和命令行接口"
```

---

### Task 4: 测试执行器（前 10 张专辑）

**Files:**
- Test: `mcp_executor.py`

- [ ] **Step 1: 运行测试（前 10 张专辑）"""

```bash
cd C:\Users\shuyua01\Code\douban
python mcp_executor.py --start 0 --end 9
```

Expected: 处理前 10 张专辑，输出详细日志，保存进度到 `mcp_executor_progress.json`

- [ ] **Step 2: 验证进度文件"""

```bash
python -c "
import json
with open('mcp_executor_progress.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f'current_index: {data.get(\"current_index\")}')
print(f'success_count: {data.get(\"success_count\")}')
print(f'failed_count: {data.get(\"failed_count\")}')
print(f'results: {len(data.get(\"results\", []))} 条')
"
```

Expected: 显示当前索引、成功数、失败数

- [ ] **Step 3: 验证结果文件"""

```bash
python -c "
import json
with open('mcp_executor_result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f'处理数量：{data.get(\"processed_count\")}')
print(f'成功：{data.get(\"success_count\")}')
print(f'失败：{data.get(\"failed_count\")}')
print(f'成功率：{data.get(\"success_rate\", 0) * 100:.1f}%')
"
```

Expected: 显示处理统计

- [ ] **Step 4: 提交测试结果"""

```bash
git add mcp_executor_progress.json mcp_executor_result.json
git commit -m "test: 测试前 10 张专辑处理"
```

---

### Task 5: 全量执行（6391 张专辑）

**Files:**
- Execute: `mcp_executor.py`

- [ ] **Step 1: 启动全量处理"""

```bash
cd C:\Users\shuyua01\Code\douban
python mcp_executor.py
```

Expected: 从索引 0 开始处理全部 6391 张专辑

- [ ] **Step 2: 监控进度（每小时检查一次）"""

```bash
python -c "
import json
with open('mcp_executor_progress.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
total = data.get('success_count', 0) + data.get('failed_count', 0)
rate = data.get('success_count', 0) / total * 100 if total > 0 else 0
print(f'进度：{data.get(\"current_index\")}/6391')
print(f'成功：{data.get(\"success_count\")} ({rate:.1f}%)')
print(f'失败：{data.get(\"failed_count\")}')
"
```

- [ ] **Step 3: 处理完成后验证结果"""

```bash
python -c "
import json
with open('mcp_executor_result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f'===== 最终结果 =====')
print(f'总处理：{data.get(\"processed_count\")}/6391')
print(f'成功：{data.get(\"success_count\")}')
print(f'失败：{data.get(\"failed_count\")}')
print(f'成功率：{data.get(\"success_rate\", 0) * 100:.1f}%')
"
```

Expected: 成功率 ≥ 90%

- [ ] **Step 4: 提交最终结果"""

```bash
git add mcp_executor_progress.json mcp_executor_result.json
git commit -m "chore: 完成 6391 张专辑标签添加"
```

---

## 自审检查

### 1. 规范覆盖检查

| 规范要求 | 对应 Task | 状态 |
|----------|-----------|------|
| 单批次顺序执行 | Task 3 (run 方法) | ✓ |
| 10 个数据源生成标签 | Task 1 (tag_generator 导入) | ✓ |
| 每专辑最多 10 个标签 | Task 1 (MAX_TAGS_PER_ALBUM) | ✓ |
| 保留已有标签 | Task 2 (_extract_existing_tags + 合并逻辑) | ✓ |
| 每 5 张保存进度 | Task 3 (SAVE_INTERVAL) | ✓ |
| 断点续传 | Task 1 (_load_progress) + Task 3 (--resume) | ✓ |
| MCP 工具调用 | Task 2 (add_tags_via_mcp) | ✓ |

### 2. 占位符检查

- 无 "TBD"、"TODO"
- 无 "添加适当的错误处理"等模糊描述
- 所有代码步骤都有完整代码

### 3. 类型一致性检查

- `MAX_TAGS_PER_ALBUM = 10` 在所有引用处一致
- `SAVE_INTERVAL = 5` 在所有引用处一致
- 方法签名一致：`generate_tags()` 返回 `List[str]`，`add_tags_via_mcp()` 返回 `Dict`
- 进度文件结构在所有任务中一致

### 4. 潜在问题

**注意：** Task 5 的全量执行需要约 9 小时，需要在 Claude Code 会话中长时间运行。MCP 工具函数（`mcp_navigate`、`mcp_snapshot`、`mcp_click`、`mcp_fill`）需要在执行时由外部注入。

**解决方案：** 在 Task 4 测试前，需要在 Claude Code 中实际调用 MCP 工具并注入到执行器。

---

## 执行选择

计划已保存到 `docs/superpowers/plans/2026-04-07-douban-mcp-auto-tagger-plan.md`

**两种执行方式：**

**1. Subagent-Driven（推荐）** - 每个 Task dispatch 一个 fresh subagent，Task 间 review，快速迭代

**2. Inline Execution** - 在当前会话中使用 executing-plans 批量执行，带 checkpoints

**选择哪种方式？**
