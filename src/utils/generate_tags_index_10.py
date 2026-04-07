#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为索引 10 的专辑生成标签"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from auto_gen_music_tags.tag_generator import DoubanMusicTagGenerator
import json

gen = DoubanMusicTagGenerator('cookie.txt')
result = gen.generate_tags('34391898', verbose=True)
tags = result.get('tags_all', [])[:10]
print(f"\n生成的标签 ({len(tags)} 个):")
print(' '.join(tags))

# 保存标签到临时文件
with open('temp_tags_index_10.json', 'w', encoding='utf-8') as f:
    json.dump({'tags': tags, 'result': result}, f, ensure_ascii=False, indent=2)
print("\n标签已保存到 temp_tags_index_10.json")
