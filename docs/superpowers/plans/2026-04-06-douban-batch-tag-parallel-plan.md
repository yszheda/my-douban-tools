# 豆瓣音乐批量标签添加 - 并行执行实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 6391 张豆瓣音乐专辑批量添加标签，使用 3 个并行工作树同时执行，预计 9 小时完成。

**Architecture:** 每个工作树独立处理约 2130 张专辑，先离线生成标签数据，再使用 MCP Chrome DevTools 批量添加，进度独立保存可随时恢复。

**Tech Stack:** Python, MCP Chrome DevTools, requests, json

---

### Task 1: 创建并行处理器脚本

**Files:**
- Create: `auto_gen_music_tags/parallel_processor.py`
- Modify: `auto_gen_music_tags/tag_generator.py` (已存在)
- Modify: `auto_gen_music_tags/browser_adder.py` (已存在)

- [ ] **Step 1: 创建并行处理器框架**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""豆瓣音乐批量标签并行处理器

使用方法:
    python parallel_processor.py --batch a --start 0 --end 2130
    python parallel_processor.py --batch b --start 2131 --end 4260
    python parallel_processor.py --batch c --start 4261 --end 6391
"""

import json
import time
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 导入标签生成器和添加器
sys.path.insert(0, str(Path(__file__).parent))
from tag_generator import DoubanMusicTagGenerator

# 配置
ALBUM_LIST_FILE = Path(__file__).parent.parent / "album_list_full.json"
PROGRESS_FILE = Path(__file__).parent.parent / "progress_{batch}.json"
RESULT_FILE = Path(__file__).parent.parent / "result_{batch}.json"
TAGS_FILE = Path(__file__).parent.parent / "tags_batch_{batch}.json"

MAX_TAGS_PER_ALBUM = 10
DELAY_BETWEEN_ALBUMS = 5  # 秒
DELAY_BETWEEN_API_CALLS = 0.5  # 数据源 API 调用延迟


class ParallelTagProcessor:
    """并行标签处理器"""
    
    def __init__(self, batch_id: str, start_index: int, end_index: int):
        self.batch_id = batch_id
        self.start_index = start_index
        self.end_index = end_index
        self.tagger = DoubanMusicTagGenerator()
        self.progress = self.load_progress()
        self.results = []
        self.failed = []
        
    def load_progress(self) -> Dict:
        """加载进度"""
        try:
            with open(PROGRESS_FILE.format(batch=self.batch_id), 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'current_index': self.start_index,
                'processed': [],
                'failed': [],
                'started_at': None,
                'last_updated': None
            }
    
    def save_progress(self):
        """保存进度"""
        self.progress['last_updated'] = datetime.now().isoformat()
        with open(PROGRESS_FILE.format(batch=self.batch_id), 'w', encoding='utf-8') as f:
            json.dump(self.progress, f, ensure_ascii=False, indent=2)
    
    def generate_tags_for_album(self, subject_id: str, title: str) -> List[str]:
        """为单张专辑生成标签"""
        result = self.tagger.generate_tags(
            subject_id=subject_id,
            album_info={'title': title},
            verbose=False
        )
        tags = result.get('tags_all', [])
        return tags[:MAX_TAGS_PER_ALBUM]
    
    def process_album(self, album: Dict) -> Optional[Dict]:
        """处理单张专辑"""
        subject_id = album['subject_id']
        title = album.get('title', '')
        
        # 生成标签
        tags = self.generate_tags_for_album(subject_id, title)
        
        if not tags:
            return None
        
        return {
            'subject_id': subject_id,
            'title': title,
            'tags': tags,
            'processed_at': datetime.now().isoformat()
        }
    
    def run(self):
        """执行批量处理"""
        print(f"\n{'='*60}")
        print(f"Batch {self.batch_id}: 处理索引 {self.start_index}-{self.end_index}")
        print(f"{'='*60}")
        
        # 加载专辑数据
        with open(ALBUM_LIST_FILE, 'r', encoding='utf-8') as f:
            albums_data = json.load(f)
        
        albums = albums_data['collections']['collect']
        batch_albums = albums[self.start_index:self.end_index]
        
        # 从断点继续
        current_index = self.progress.get('current_index', self.start_index)
        self.results = self.progress.get('processed', [])
        self.failed = self.progress.get('failed', [])
        
        self.progress['started_at'] = self.progress.get('started_at') or datetime.now().isoformat()
        
        for i, album in enumerate(batch_albums):
            absolute_index = self.start_index + i
            
            if absolute_index < current_index:
                continue
            
            print(f"\n[{self.batch_id}] 处理 {absolute_index}/{self.end_index}: {album['subject_id']}")
            
            result = self.process_album(album)
            
            if result:
                self.results.append(result)
                print(f"[{self.batch_id}] 成功：生成 {len(result['tags'])} 个标签")
            else:
                self.failed.append({
                    'subject_id': album['subject_id'],
                    'title': album.get('title', ''),
                    'reason': 'no_tags_generated',
                    'index': absolute_index
                })
                print(f"[{self.batch_id}] 失败：未生成标签")
            
            # 每 10 张保存一次进度
            if (i + 1) % 10 == 0:
                self.progress['processed'] = self.results
                self.progress['failed'] = self.failed
                self.progress['current_index'] = absolute_index + 1
                self.save_progress()
                print(f"[{self.batch_id}] 进度已保存")
            
            # 延迟
            if absolute_index < self.end_index - 1:
                time.sleep(DELAY_BETWEEN_ALBUMS)
        
        # 最终保存
        self.progress['processed'] = self.results
        self.progress['failed'] = self.failed
        self.progress['current_index'] = self.end_index
        self.progress['completed_at'] = datetime.now().isoformat()
        self.save_progress()
        
        # 保存结果
        self.save_result()
        
        print(f"\n{'='*60}")
        print(f"Batch {self.batch_id} 完成")
        print(f"成功：{len(self.results)}, 失败：{len(self.failed)}")
        print(f"{'='*60}")
        
        return self.results, self.failed
    
    def save_result(self):
        """保存最终结果"""
        result = {
            'batch_id': self.batch_id,
            'completed_at': datetime.now().isoformat(),
            'summary': {
                'total_processed': len(self.results),
                'total_failed': len(self.failed),
                'success_rate': len(self.results) / (len(self.results) + len(self.failed)) if (self.results or self.failed) else 0
            },
            'processed': self.results,
            'failed': self.failed
        }
        
        with open(RESULT_FILE.format(batch=self.batch_id), 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 保存标签数据供后续添加使用
        tags_data = {
            'batch_id': self.batch_id,
            'generated_at': datetime.now().isoformat(),
            'albums': [
                {'subject_id': r['subject_id'], 'title': r['title'], 'tags': r['tags']}
                for r in self.results
            ]
        }
        
        with open(TAGS_FILE.format(batch=self.batch_id), 'w', encoding='utf-8') as f:
            json.dump(tags_data, f, ensure_ascii=False, indent=2)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='豆瓣音乐批量标签并行处理器')
    parser.add_argument('--batch', type=str, required=True, choices=['a', 'b', 'c'],
                        help='批次 ID (a, b, c)')
    parser.add_argument('--start', type=int, required=True, help='起始索引')
    parser.add_argument('--end', type=int, required=True, help='结束索引')
    
    args = parser.parse_args()
    
    processor = ParallelTagProcessor(args.batch, args.start, args.end)
    processor.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断，进度已保存")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] 未预期错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

- [ ] **Step 2: 验证脚本创建成功**

Run: `python -c "import auto_gen_music_tags.parallel_processor; print('OK')"`
Expected: OK

- [ ] **Step 3: 提交**

```bash
git add auto_gen_music_tags/parallel_processor.py
git commit -m "feat: 添加并行标签处理器"
```

---

### Task 2: 创建结果合并脚本

**Files:**
- Create: `merge_batch_results.py`

- [ ] **Step 1: 创建合并脚本**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""合并 3 个批次的处理结果"""

import json
from pathlib import Path
from datetime import datetime

RESULT_FILES = [
    Path(__file__).parent / "result_a.json",
    Path(__file__).parent / "result_b.json",
    Path(__file__).parent / "result_c.json",
]

def merge_results():
    """合并所有批次结果"""
    all_processed = []
    all_failed = []
    batch_summaries = []
    
    for result_file in RESULT_FILES:
        if not result_file.exists():
            print(f"[WARN] {result_file} 不存在，跳过")
            continue
        
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        batch_id = data.get('batch_id', 'unknown')
        summary = data.get('summary', {})
        
        all_processed.extend(data.get('processed', []))
        all_failed.extend(data.get('failed', []))
        batch_summaries.append({
            'batch_id': batch_id,
            'processed': summary.get('total_processed', 0),
            'failed': summary.get('total_failed', 0),
            'success_rate': summary.get('success_rate', 0)
        })
        
        print(f"[OK] 合并 {batch_id}: {summary.get('total_processed')} 成功，{summary.get('total_failed')} 失败")
    
    # 计算总结果
    total = len(all_processed) + len(all_failed)
    success_rate = len(all_processed) / total if total > 0 else 0
    
    final_result = {
        'merged_at': datetime.now().isoformat(),
        'batches': batch_summaries,
        'summary': {
            'total_albums': 6391,
            'total_processed': len(all_processed),
            'total_failed': len(all_failed),
            'total': total,
            'success_rate': success_rate
        },
        'processed': all_processed,
        'failed': all_failed
    }
    
    # 保存最终结果
    output_file = Path(__file__).parent / "final_summary.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print("最终结果:")
    print(f"  总专辑数：6391")
    print(f"  已处理：{len(all_processed)}")
    print(f"  失败：{len(all_failed)}")
    print(f"  成功率：{success_rate:.2%}")
    print(f"  结果已保存到：{output_file}")
    print(f"{'='*60}")
    
    return final_result


if __name__ == '__main__':
    merge_results()
```

- [ ] **Step 2: 提交**

```bash
git add merge_batch_results.py
git commit -m "feat: 添加批次结果合并脚本"
```

---

### Task 3: 启动批次 A (索引 0-2130)

**Files:**
- Use: `auto_gen_music_tags/parallel_processor.py`

- [ ] **Step 1: 启动批次 A**

Run: `python auto_gen_music_tags/parallel_processor.py --batch a --start 0 --end 2130`
Expected: 开始处理，输出日志

- [ ] **Step 2: 验证进度保存**

Run: `cat progress_a.json | head -20`
Expected: 包含 current_index, processed, failed 字段

- [ ] **Step 3: 提交进度**

```bash
git add progress_a.json
git commit -m "chore: 保存批次 A 进度"
```

---

### Task 4: 启动批次 B (索引 2131-4260)

**Files:**
- Use: `auto_gen_music_tags/parallel_processor.py`

- [ ] **Step 1: 启动批次 B**

Run: `python auto_gen_music_tags/parallel_processor.py --batch b --start 2131 --end 4260`
Expected: 开始处理，输出日志

- [ ] **Step 2: 验证进度保存**

Run: `cat progress_b.json | head -20`
Expected: 包含 current_index, processed, failed 字段

- [ ] **Step 3: 提交进度**

```bash
git add progress_b.json
git commit -m "chore: 保存批次 B 进度"
```

---

### Task 5: 启动批次 C (索引 4261-6391)

**Files:**
- Use: `auto_gen_music_tags/parallel_processor.py`

- [ ] **Step 1: 启动批次 C**

Run: `python auto_gen_music_tags/parallel_processor.py --batch c --start 4261 --end 6391`
Expected: 开始处理，输出日志

- [ ] **Step 2: 验证进度保存**

Run: `cat progress_c.json | head -20`
Expected: 包含 current_index, processed, failed 字段

- [ ] **Step 3: 提交进度**

```bash
git add progress_c.json
git commit -m "chore: 保存批次 C 进度"
```

---

### Task 6: 合并结果

**Files:**
- Use: `merge_batch_results.py`

- [ ] **Step 1: 等待所有批次完成**

Run: `ls -la progress_*.json result_*.json`
Expected: 所有文件存在，completed_at 字段有值

- [ ] **Step 2: 合并结果**

Run: `python merge_batch_results.py`
Expected: 输出最终统计，创建 final_summary.json

- [ ] **Step 3: 提交最终结果**

```bash
git add final_summary.json result_*.json tags_batch_*.json
git commit -m "chore: 合并所有批次结果"
```

---

### Task 7: 验证和清理

**Files:**
- Read: `final_summary.json`

- [ ] **Step 1: 验证成功率**

Run: `python -c "import json; r=json.load(open('final_summary.json')); print(f'成功率：{r[\"summary\"][\"success_rate\"]:.2%}')"`
Expected: 成功率 ≥ 90%

- [ ] **Step 2: 检查失败原因**

Run: `python -c "import json; r=json.load(open('final_summary.json')); print('失败原因:', set(f.get('reason','') for f in r['failed'][:10]))"`
Expected: 显示失败原因列表

- [ ] **Step 3: 提交验证报告**

```bash
git add final_summary.json
git commit -m "docs: 添加验证报告"
```

---

## 执行选择

**计划已完成并保存到 `docs/superpowers/plans/2026-04-06-douban-batch-tag-parallel-plan.md`**

有两种执行方式：

**1. Subagent-Driven（推荐）** - 每个 Task  dispatch 一个 fresh subagent，Task 间 review，快速迭代

**2. Inline Execution** - 在当前会话中使用 executing-plans 批量执行，带 checkpoints

**选择哪种方式？**
