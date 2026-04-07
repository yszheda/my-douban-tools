#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""豆瓣音乐缺失条目查找工具

通过 MCP Chrome DevTools 逐页导航，收集所有条目并与已导出数据比较
"""

import json
import time
from pathlib import Path

# 导入 MCP 客户端
try:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


def load_exported_ids():
    """加载已导出的 ID"""
    with open('album_list_full.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return set(e['subject_id'] for e in data['collections']['collect'])


def collect_page_data():
    """收集当前页面数据（通过 MCP）"""
    # 这里需要通过 MCP 工具调用
    # 由于在 Python 中无法直接调用 MCP，我们生成 JavaScript 代码
    pass


def main():
    print("=" * 60)
    print("豆瓣音乐缺失条目查找工具")
    print("=" * 60)

    # 加载已导出的 ID
    exported_ids = load_exported_ids()
    print(f"\n已导出唯一 ID 数量：{len(exported_ids)}")
    print(f"豆瓣显示总数：6493")
    print(f"预计缺失条目：{6493 - len(exported_ids)}")

    # 生成 JavaScript 代码用于在浏览器中运行
    js_collect = """
// 收集当前页面所有条目
function collectCurrentPage() {
    const links = document.querySelectorAll('a[href*="/subject/"]');
    const items = [];

    links.forEach(link => {
        const match = link.href.match(/\\/subject\\/(\\d+)\\//);
        if (match) {
            const id = match[1];
            if (!items.find(i => i.subject_id === id)) {
                const card = link.closest('.item');
                let title = '';
                if (card) {
                    const titleEl = card.querySelector('.title');
                    if (titleEl) title = titleEl.textContent.trim().replace(/\\s+/g, ' ');
                }
                items.push({ subject_id: id, title: title.substring(0, 100) });
            }
        }
    });

    // 获取页码
    const urlParams = new URLSearchParams(window.location.search);
    const start = parseInt(urlParams.get('start') || '0');
    const page = Math.floor(start / 15) + 1;

    return { page, start, items };
}

// 累积结果到 localStorage
function saveToStorage(pageData) {
    let allData = JSON.parse(localStorage.getItem('douban_missing_finder') || '{"pages": [], "items": []}');

    if (!allData.pages.includes(pageData.page)) {
        allData.pages.push(pageData.page);
        allData.items.push(...pageData.items);
        localStorage.setItem('douban_missing_finder', JSON.stringify(allData));
    }

    return {
        pagesProcessed: allData.pages.length,
        totalItems: allData.items.length,
        uniqueItems: new Set(allData.items.map(i => i.subject_id)).size
    };
}

// 导航到下一页
function goToNextPage() {
    const urlParams = new URLSearchParams(window.location.search);
    let start = parseInt(urlParams.get('start') || '0');
    start += 15;

    const url = new URL(window.location.href);
    url.searchParams.set('start', start);
    window.location.href = url.toString();

    return start;
}

// 运行单页收集
const pageData = collectCurrentPage();
const stats = saveToStorage(pageData);
console.log('Page', pageData.page, '- items:', pageData.items.length, 'total unique:', stats.uniqueItems);

return { ...pageData, ...stats };
"""

    print("\n生成的 JavaScript 代码可以在浏览器中运行来收集所有条目")
    print("使用方法：")
    print("1. 在 Chrome 中打开 https://music.douban.com/people/63343218/collect?sort=time&start=0&mode=grid")
    print("2. 打开开发者工具控制台")
    print("3. 运行生成的 JavaScript 代码")
    print("4. 重复运行直到收集完所有 433 页")
    print("5. 运行以下命令获取结果：")
    print("   JSON.parse(localStorage.getItem('douban_missing_finder'))")


if __name__ == '__main__':
    main()
