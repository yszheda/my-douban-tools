#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from datetime import datetime

# 读取新数据
with open('page_data.json', 'r', encoding='utf-8') as f:
    new_entries = json.load(f)

# 读取现有数据
with open('album_list_full.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

# 去重合并
existing_ids = {e['subject_id'] for e in results['collections']['collect']}
new_unique = [e for e in new_entries if e['subject_id'] not in existing_ids]
results['collections']['collect'].extend(new_unique)

# 更新统计
results['stats'] = {k: len(v) for k, v in results['collections'].items()}
results['stats']['total'] = sum(results['stats'].values())
results['exported_at'] = datetime.now().isoformat()

# 保存结果
with open('album_list_full.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# 更新进度文件
with open('export_progress.json', 'r', encoding='utf-8') as f:
    progress = json.load(f)

progress['entries']['collect'] = results['collections']['collect']
progress['current_page'] += 1
progress['current_start'] += 30
progress['last_updated'] = datetime.now().isoformat()

with open('export_progress.json', 'w', encoding='utf-8') as f:
    json.dump(progress, f, ensure_ascii=False, indent=2)

# 从 progress 文件读取最新页码
with open('export_progress.json', 'r', encoding='utf-8') as f:
    progress = json.load(f)
next_page = progress['current_page']
next_start = progress['current_start']
print(f"Collect 第 {next_page-1} 页完成：新增 {len(new_unique)} 条，累计 {len(results['collections']['collect'])} 条")
print(f"下一页：start={next_start}, page={next_page}")
