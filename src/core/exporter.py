#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣收藏列表导出器 - 使用浏览器 MCP 工具

使用方法：
1. 打开 Chrome DevTools MCP
2. 运行此脚本
3. 脚本会自动导航到每个页面并提取专辑信息
"""

import json
import time
from datetime import datetime
from typing import List, Dict


def export_collection_with_mcp(mcp_tools, collection_type: str, user_id: str = "63343218", max_pages: int = None) -> List[Dict]:
    """使用 MCP 工具导出收藏列表"""

    all_entries = []
    start = 0
    page = 1
    items_per_page = 30

    print(f"\n{'='*60}")
    print(f"导出 {collection_type} 列表")
    print(f"{'='*60}")

    while True:
        url = f"https://music.douban.com/people/{user_id}/{collection_type}?start={start}&mode=list"
        print(f"[Page {page}] {url}")

        # 导航
        mcp_tools['navigate_page'](url=url, type='url', timeout=30000)
        time.sleep(2.0)

        # 执行 JS
        js = """
        () => {
            const links = Array.from(document.querySelectorAll('a[href*="/subject/"]'))
                .filter(a => !a.href.includes('/people/'))
                .map(a => {
                    const match = a.href.match(/\\/subject\\/(\\d+)\\//);
                    return {
                        subject_id: match ? match[1] : null,
                        title: a.title || a.textContent.trim()
                    };
                })
                .filter(x => x.subject_id);

            // 去重
            const seen = new Set();
            const unique = links.filter(x => {
                if (seen.has(x.subject_id)) return false;
                seen.add(x.subject_id);
                return true;
            });

            // 检查下一页
            const hasNext = Array.from(document.querySelectorAll('a')).some(a => a.textContent.includes('后页'));

            return { entries: unique, hasNext };
        }
        """

        result = mcp_tools['evaluate_script'](function=js)
        data = result if isinstance(result, dict) else {}

        entries = data.get('entries', [])
        has_next = data.get('hasNext', False)

        if not entries:
            print("  无条目，停止")
            break

        all_entries.extend(entries)
        print(f"  本页：{len(entries)}, 累计：{len(all_entries)}")

        if not has_next:
            print("  最后一页")
            break

        if max_pages and page >= max_pages:
            print(f"  已达最大页数 {max_pages}")
            break

        start += items_per_page
        page += 1
        time.sleep(1.5)

    print(f"{collection_type} 完成：{len(all_entries)} 条")
    return all_entries


def export_all_collections(mcp_tools, user_id: str = "63343218", output_file: str = "album_list_full.json"):
    """导出所有收藏类型"""

    print(f"\n{'='*70}")
    print("豆瓣音乐收藏列表导出工具")
    print(f"{'='*70}")
    print(f"用户：{user_id}")
    print(f"开始：{datetime.now().isoformat()}")

    results = {}

    for ctype in ['collect', 'do', 'wish']:
        entries = export_collection_with_mcp(mcp_tools, ctype, user_id)
        results[ctype] = entries

    # 保存
    output = {
        'exported_at': datetime.now().isoformat(),
        'user_id': user_id,
        'stats': {k: len(v) for k, v in results.items()},
        'collections': results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*70}")
    print("导出完成!")
    print(f"已听 (collect): {len(results['collect'])}")
    print(f"在听 (do): {len(results['do'])}")
    print(f"想听 (wish): {len(results['wish'])}")
    print(f"总计：{sum(len(v) for v in results.values())}")
    print(f"保存到：{output_file}")
    print(f"{'='*70}")

    return output


if __name__ == '__main__':
    print("请在 MCP 环境中导入并运行:")
    print("  from exporter import export_all_collections")
    print("  export_all_collections(mcp_tools)")
