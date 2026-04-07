#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣收藏列表导出器 - 使用 MCP 工具

此脚本通过调用 MCP 浏览器工具来导出豆瓣音乐收藏列表。
由于需要在 MCP 环境中运行，此脚本提供执行框架。
"""

import json
import time
from datetime import datetime


def export_collect(mcp_tools, user_id="63343218", output_file="collect_entries.json"):
    """导出已听专辑列表"""

    all_entries = []
    start = 0
    page = 1
    items_per_page = 30

    print("=" * 60)
    print("导出已听专辑列表 (collect)")
    print("=" * 60)
    print(f"用户：{user_id}")
    print(f"开始时间：{datetime.now().isoformat()}")

    while True:
        url = f"https://music.douban.com/people/{user_id}/collect?start={start}&mode=list"
        print(f"\n[Page {page}] {url}")

        # 导航
        mcp_tools['navigate_page'](url=url, type='url', timeout=30000)
        time.sleep(2.0)

        # 提取数据
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

            const seen = new Set();
            const unique = links.filter(x => {
                if (seen.has(x.subject_id)) return false;
                seen.add(x.subject_id);
                return true;
            });

            const hasNext = Array.from(document.querySelectorAll('a')).some(a => a.textContent.includes('后页'));

            return { entries: unique, hasNext, count: unique.length };
        }
        """

        result = mcp_tools['evaluate_script'](function=js)
        data = result if isinstance(result, dict) else {}

        entries = data.get('entries', [])
        has_next = data.get('hasNext', False)
        count = data.get('count', 0)

        if count == 0:
            print("  无条目，停止")
            break

        all_entries.extend(entries)
        print(f"  本页：{count} 条，累计：{len(all_entries)} 条")

        # 每页保存进度
        with open('collect_entries.json', 'w', encoding='utf-8') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'user_id': user_id,
                'total': len(all_entries),
                'entries': all_entries
            }, f, ensure_ascii=False, indent=2)

        if not has_next:
            print("  已达最后一页")
            break

        start += items_per_page
        page += 1
        time.sleep(1.5)

    print(f"\n导出完成：共 {len(all_entries)} 条")
    return all_entries


def export_do(mcp_tools, user_id="63343218", output_file="do_entries.json"):
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
        time.sleep(2.0)

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

            const seen = new Set();
            const unique = links.filter(x => {
                if (seen.has(x.subject_id)) return false;
                seen.add(x.subject_id);
                return true;
            });

            const hasNext = Array.from(document.querySelectorAll('a')).some(a => a.textContent.includes('后页'));

            return { entries: unique, hasNext, count: unique.length };
        }
        """

        result = mcp_tools['evaluate_script'](function=js)
        data = result if isinstance(result, dict) else {}

        entries = data.get('entries', [])
        has_next = data.get('hasNext', False)
        count = data.get('count', 0)

        if count == 0:
            print("  无条目，停止")
            break

        all_entries.extend(entries)
        print(f"  本页：{count} 条，累计：{len(all_entries)} 条")

        with open('do_entries.json', 'w', encoding='utf-8') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'user_id': user_id,
                'total': len(all_entries),
                'entries': all_entries
            }, f, ensure_ascii=False, indent=2)

        if not has_next:
            print("  已达最后一页")
            break

        start += items_per_page
        page += 1
        time.sleep(1.5)

    print(f"\n导出完成：共 {len(all_entries)} 条")
    return all_entries


def export_wish(mcp_tools, user_id="63343218", output_file="wish_entries.json"):
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
        time.sleep(2.0)

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

            const seen = new Set();
            const unique = links.filter(x => {
                if (seen.has(x.subject_id)) return false;
                seen.add(x.subject_id);
                return true;
            });

            const hasNext = Array.from(document.querySelectorAll('a')).some(a => a.textContent.includes('后页'));

            return { entries: unique, hasNext, count: unique.length };
        }
        """

        result = mcp_tools['evaluate_script'](function=js)
        data = result if isinstance(result, dict) else {}

        entries = data.get('entries', [])
        has_next = data.get('hasNext', False)
        count = data.get('count', 0)

        if count == 0:
            print("  无条目，停止")
            break

        all_entries.extend(entries)
        print(f"  本页：{count} 条，累计：{len(all_entries)} 条")

        with open('wish_entries.json', 'w', encoding='utf-8') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'user_id': user_id,
                'total': len(all_entries),
                'entries': all_entries
            }, f, ensure_ascii=False, indent=2)

        if not has_next:
            print("  已达最后一页")
            break

        start += items_per_page
        page += 1
        time.sleep(1.5)

    print(f"\n导出完成：共 {len(all_entries)} 条")
    return all_entries


def export_all(mcp_tools, user_id="63343218"):
    """导出所有收藏类型"""

    print("\n" + "=" * 70)
    print("豆瓣音乐收藏列表导出工具")
    print("=" * 70)
    print(f"用户：{user_id}")
    print(f"开始时间：{datetime.now().isoformat()}")

    # 导出每种类型
    collect_entries = export_collect(mcp_tools, user_id)
    do_entries = export_do(mcp_tools, user_id)
    wish_entries = export_wish(mcp_tools, user_id)

    # 合并结果
    results = {
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

    # 保存最终结果
    with open('album_list_full.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("导出完成!")
    print(f"已听 (collect): {len(collect_entries)}")
    print(f"在听 (do): {len(do_entries)}")
    print(f"想听 (wish): {len(wish_entries)}")
    print(f"总计：{len(collect_entries) + len(do_entries) + len(wish_entries)}")
    print(f"结束时间：{datetime.now().isoformat()}")
    print("=" * 70)

    return results


if __name__ == '__main__':
    print("豆瓣音乐收藏列表导出脚本")
    print("请在 MCP 环境中导入并运行:")
    print("  from exporter_full import export_all")
    print("  export_all(mcp_tools)")
