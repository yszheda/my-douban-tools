#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""豆瓣音乐缺失条目查找工具

通过 MCP Chrome DevTools 逐页导航收集所有条目，与已导出数据比较找出缺失条目
"""

import json
import time
import sys

# 读取已导出的 ID
with open('album_list_full.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

exported_ids = set(e['subject_id'] for e in data['collections']['collect'])
print(f"已导出唯一 ID: {len(exported_ids)}")
print(f"豆瓣显示总数：6493")
print(f"预计缺失：{6493 - len(exported_ids)} 条")

# 生成 JavaScript 收集脚本
collect_js = """
() => {
    // 收集当前页面所有条目
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
                items.push({ subject_id: id, title: title });
            }
        }
    });

    // 获取页码
    const urlParams = new URLSearchParams(window.location.search);
    const start = parseInt(urlParams.get('start') || '0');
    const page = Math.floor(start / 15) + 1;

    // 累积保存
    let allData = JSON.parse(localStorage.getItem('douban_all_collect') || '[]');
    const existingIds = new Set(allData.map(i => i.subject_id));
    const newItems = items.filter(i => !existingIds.has(i.subject_id));

    allData.push(...newItems);
    localStorage.setItem('douban_all_collect', JSON.stringify(allData));

    return {
        page: page,
        start: start,
        itemsThisPage: items.length,
        newItems: newItems.length,
        totalItems: allData.length,
        uniqueItems: new Set(allData.map(i => i.subject_id)).size
    };
}
"""

# 生成导航脚本
def navigate_js(start):
    return f"""
() => {{
    const url = 'https://music.douban.com/people/63343218/collect?sort=time&start={start}&mode=grid';
    window.location.href = url;
    return {{ navigating_to: start }};
}}
"""

print("\n脚本已生成")
print("由于 MCP 工具调用需要用户确认，建议使用以下方法：")
print("1. 在浏览器控制台运行 collect_js 脚本")
print("2. 运行以下批处理命令自动导航所有页面")

# 生成批处理导航脚本
batch_nav_js = """
(async function autoNavigate() {
    const BASE_URL = 'https://music.douban.com/people/63343218/collect?sort=time&start=';
    const DELAY_MS = 2000;

    for (let start = 0; start < 6500; start += 15) {
        const url = BASE_URL + start;
        console.log('Navigating to', url);
        window.location.href = url;

        // 等待页面加载
        await new Promise(resolve => setTimeout(resolve, DELAY_MS));

        // 运行收集脚本
        const items = [];
        const links = document.querySelectorAll('a[href*="/subject/"]');
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
                    items.push({ subject_id: id, title: title });
                }
            }
        });

        // 保存
        let allData = JSON.parse(localStorage.getItem('douban_all_collect') || '[]');
        const existingIds = new Set(allData.map(i => i.subject_id));
        const newItems = items.filter(i => !existingIds.has(i.subject_id));
        allData.push(...newItems);
        localStorage.setItem('douban_all_collect', JSON.stringify(allData));

        console.log('Page', (start/15)+1, '- new:', newItems.length, '- unique:', new Set(allData.map(i => i.subject_id)).size);
    }

    console.log('完成！');
    return JSON.parse(localStorage.getItem('douban_all_collect'));
})();
"""

with open('auto_collect_all.js', 'w', encoding='utf-8') as f:
    f.write(batch_nav_js)

print(f"\n已生成 auto_collect_all.js ({len(batch_nav_js)} 字符)")
print("\n使用方法：")
print("1. 在 Chrome 中打开豆瓣音乐页面")
print("2. 打开开发者工具控制台")
print("3. 复制粘贴 auto_collect_all.js 的内容并运行")
print("4. 等待脚本自动收集所有 433 页")
print("5. 运行以下命令导出数据：")
print("   JSON.stringify(localStorage.getItem('douban_all_collect'))")
print("6. 将结果保存为 all_collected.json")
print("7. 运行 compare_missing.py 比较找出缺失条目")
