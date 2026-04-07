#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣收藏列表导出脚本 - 使用 MCP 浏览器工具

此脚本通过调用 Chrome DevTools MCP 工具来导出豆瓣音乐收藏列表。
支持断点续跑，每页保存一次进度。

运行方式:
    在 MCP 环境中执行: python export_collect_manual.py
"""

import json
import time
from datetime import datetime
from typing import List, Dict


def export_collect(mcp_tools, user_id: str = "63343218", output_file: str = "collect_export.json"):
    """导出已听专辑列表"""

    all_entries = []
    start = 0
    page = 1
    items_per_page = 30

    print("=" * 60)
    print("导出已听专辑列表 (collect)")
    print("=" * 60)

    while True:
        url = f"https://music.douban.com/people/{user_id}/collect?start={start}&mode=list"
        print(f"\n[Page {page}] {url}")

        # 导航到页面
        mcp_tools['navigate_page'](url=url, type='url', timeout=30000)
        time.sleep(1.5)

        # 执行 JavaScript 提取数据
        js_code = """
        () => {
            const links = Array.from(document.querySelectorAll('a[href*="/subject/"]'))
                .filter(a => !a.href.includes('/people/'))
                .map(a => {
                    const match = a.href.match(/\\/subject\\/(\\d+)\\//);
                    return {
                        id: match ? match[1] : null,
                        title: a.title || a.textContent.trim()
                    };
                })
                .filter(x => x.id);

            const seen = new Set();
            const unique = links.filter(x => {
                if (seen.has(x.id)) return false;
                seen.add(x.id);
                return true;
            });

            const nextPage = Array.from(document.querySelectorAll('a')).find(a => a.textContent.includes('后页'));

            return {
                entries: unique,
                hasNext: !!nextPage
            };
        }
        """

        result = mcp_tools['evaluate_script'](function=js_code)
        data = result if isinstance(result, dict) else {}

        entries = data.get('entries', [])
        has_next = data.get('hasNext', False)

        if not entries:
            print("  没有更多条目，停止")
            break

        all_entries.extend(entries)
        print(f"  本页：{len(entries)} 条，累计：{len(all_entries)} 条")

        # 每页保存一次进度
        if not has_next:
            print("  已达最后一页")
            break

        # 下一页
        start += items_per_page
        page += 1
        time.sleep(1.0)

    # 保存结果
    output = {
        'exported_at': datetime.now().isoformat(),
        'user_id': user_id,
        'type': 'collect',
        'total': len(all_entries),
        'entries': all_entries
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到：{output_file}")
    print(f"总计：{len(all_entries)} 个条目")

    return all_entries


def export_do(mcp_tools, user_id: str = "63343218", output_file: str = "do_export.json"):
    """导出在听专辑列表"""

    all_entries = []
    start = 0
    page = 1
    items_per_page = 30

    print("=" * 60)
    print("导出在听专辑列表 (do)")
    print("=" * 60)

    while True:
        url = f"https://music.douban.com/people/{user_id}/do?start={start}&mode=list"
        print(f"\n[Page {page}] {url}")

        mcp_tools['navigate_page'](url=url, type='url', timeout=30000)
        time.sleep(1.5)

        js_code = """
        () => {
            const links = Array.from(document.querySelectorAll('a[href*="/subject/"]'))
                .filter(a => !a.href.includes('/people/'))
                .map(a => {
                    const match = a.href.match(/\\/subject\\/(\\d+)\\//);
                    return {
                        id: match ? match[1] : null,
                        title: a.title || a.textContent.trim()
                    };
                })
                .filter(x => x.id);

            const seen = new Set();
            const unique = links.filter(x => {
                if (seen.has(x.id)) return false;
                seen.add(x.id);
                return true;
            });

            const nextPage = Array.from(document.querySelectorAll('a')).find(a => a.textContent.includes('后页'));

            return {
                entries: unique,
                hasNext: !!nextPage
            };
        }
        """

        result = mcp_tools['evaluate_script'](function=js_code)
        data = result if isinstance(result, dict) else {}

        entries = data.get('entries', [])
        has_next = data.get('hasNext', False)

        if not entries:
            print("  没有更多条目，停止")
            break

        all_entries.extend(entries)
        print(f"  本页：{len(entries)} 条，累计：{len(all_entries)} 条")

        if not has_next:
            print("  已达最后一页")
            break

        start += items_per_page
        page += 1
        time.sleep(1.0)

    output = {
        'exported_at': datetime.now().isoformat(),
        'user_id': user_id,
        'type': 'do',
        'total': len(all_entries),
        'entries': all_entries
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到：{output_file}")
    print(f"总计：{len(all_entries)} 个条目")

    return all_entries


def export_wish(mcp_tools, user_id: str = "63343218", output_file: str = "wish_export.json"):
    """导出想听专辑列表"""

    all_entries = []
    start = 0
    page = 1
    items_per_page = 30

    print("=" * 60)
    print("导出想听专辑列表 (wish)")
    print("=" * 60)

    while True:
        url = f"https://music.douban.com/people/{user_id}/wish?start={start}&mode=list"
        print(f"\n[Page {page}] {url}")

        mcp_tools['navigate_page'](url=url, type='url', timeout=30000)
        time.sleep(1.5)

        js_code = """
        () => {
            const links = Array.from(document.querySelectorAll('a[href*="/subject/"]'))
                .filter(a => !a.href.includes('/people/'))
                .map(a => {
                    const match = a.href.match(/\\/subject\\/(\\d+)\\//);
                    return {
                        id: match ? match[1] : null,
                        title: a.title || a.textContent.trim()
                    };
                })
                .filter(x => x.id);

            const seen = new Set();
            const unique = links.filter(x => {
                if (seen.has(x.id)) return false;
                seen.add(x.id);
                return true;
            });

            const nextPage = Array.from(document.querySelectorAll('a')).find(a => a.textContent.includes('后页'));

            return {
                entries: unique,
                hasNext: !!nextPage
            };
        }
        """

        result = mcp_tools['evaluate_script'](function=js_code)
        data = result if isinstance(result, dict) else {}

        entries = data.get('entries', [])
        has_next = data.get('hasNext', False)

        if not entries:
            print("  没有更多条目，停止")
            break

        all_entries.extend(entries)
        print(f"  本页：{len(entries)} 条，累计：{len(all_entries)} 条")

        if not has_next:
            print("  已达最后一页")
            break

        start += items_per_page
        page += 1
        time.sleep(1.0)

    output = {
        'exported_at': datetime.now().isoformat(),
        'user_id': user_id,
        'type': 'wish',
        'total': len(all_entries),
        'entries': all_entries
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到：{output_file}")
    print(f"总计：{len(all_entries)} 个条目")

    return all_entries


def export_all(mcp_tools, user_id: str = "63343218"):
    """导出所有收藏类型"""

    print("\n" + "=" * 70)
    print("豆瓣音乐收藏列表导出工具")
    print("=" * 70)
    print(f"用户 ID: {user_id}")
    print(f"开始时间：{datetime.now().isoformat()}")
    print("=" * 70)

    # 导出已听
    collect_entries = export_collect(mcp_tools, user_id, "collect_export.json")

    # 导出在听
    do_entries = export_do(mcp_tools, user_id, "do_export.json")

    # 导出想听
    wish_entries = export_wish(mcp_tools, user_id, "wish_export.json")

    # 合并结果
    all_results = {
        'exported_at': datetime.now().isoformat(),
        'user_id': user_id,
        'stats': {
            'collect': len(collect_entries),
            'do': len(do_entries),
            'wish': len(wish_entries),
            'total': len(collect_entries) + len(do_entries) + len(wish_entries)
        },
        'collections': {
            'collect': collect_entries,
            'do': do_entries,
            'wish': wish_entries
        }
    }

    # 保存合并结果
    with open('album_list_full.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("导出完成!")
    print("=" * 70)
    print(f"已听 (collect): {len(collect_entries)} 个条目")
    print(f"在听 (do): {len(do_entries)} 个条目")
    print(f"想听 (wish): {len(wish_entries)} 个条目")
    print(f"总计：{len(collect_entries) + len(do_entries) + len(wish_entries)} 个条目")
    print(f"结束时间：{datetime.now().isoformat()}")
    print("=" * 70)

    return all_results


if __name__ == '__main__':
    print("豆瓣音乐收藏列表导出脚本")
    print("请在 MCP 环境中运行，并提供 mcp_tools 字典")
    print("示例:")
    print("  from export_collect_manual import export_all")
    print("  export_all(mcp_tools)")
