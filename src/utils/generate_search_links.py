#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成豆瓣音乐搜索链接 HTML 文件
用于半自动化批量处理专辑
"""

import json
from pathlib import Path
from datetime import datetime


def parse_album_file(directory: str):
    """解析专辑信息文件"""
    file_path = Path(directory) / "专辑基本信息.md"

    if not file_path.exists():
        return None

    try:
        content = file_path.read_text(encoding='utf-8')

        title = ""
        artist = ""

        # 解析标题 - 方法 1: ## 专辑名称
        import re
        title_match = re.search(r'##\s*专辑名称\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()

        # 解析标题 - 方法 2: - **专辑名称**：XXX
        if not title:
            title_match2 = re.search(r'-\s*\*\*专辑名称\*\*\s*[:：]\s*(.+?)(?:\n|$)', content)
            if title_match2:
                title = title_match2.group(1).strip()
                # 移除括号内的中文翻译
                if '（' in title:
                    title = title.split('（')[0].strip()

        # 解析艺术家 - 方法 1: ## 艺术家
        artist_match = re.search(r'##\s*艺术家\s*\n.*?\*\*(.+?)\*\*', content, re.DOTALL)
        if artist_match:
            artist = artist_match.group(1).strip()

        # 解析艺术家 - 方法 2: - **艺术家**：XXX
        if not artist:
            artist_match2 = re.search(r'-\s*\*\*艺术家\*\*\s*[:：]\s*(.+?)(?:\n|$)', content)
            if artist_match2:
                artist = artist_match2.group(1).strip()
                # 只取第一个艺术家（移除换行和多余信息）
                if '\n' in artist:
                    artist = artist.split('\n')[0].strip()

        # 清理艺术家 - 移除括号注释
        if artist and '(' in artist:
            artist = artist.split('(')[0].strip()
        # 移除冒号后的内容
        if artist and ':' in artist:
            artist = artist.split(':')[0].strip()
        if artist and '：' in artist:
            artist = artist.split('：')[0].strip()

        return {
            'directory': directory,
            'title': title,
            'artist': artist
        }

    except Exception as e:
        print(f"  解析失败：{e}")
        return None


def generate_search_links(base_path: str, output_file: str):
    """生成搜索链接 HTML 文件"""
    base = Path(base_path)

    directories = sorted([
        d for d in base.iterdir()
        if d.is_dir() and not d.name.startswith('.') and d.name != 'scripts'
    ])

    albums = []
    for directory in directories:
        album = parse_album_file(str(directory))
        if album:
            albums.append(album)

    # 生成 HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>豆瓣音乐批量处理 - 搜索链接</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #007722;
            border-bottom: 2px solid #007722;
            padding-bottom: 10px;
        }}
        .info {{
            background: #fff;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .batch-controls {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .batch-controls button {{
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        .btn-open {{
            background: #007722;
            color: white;
        }}
        .btn-open:hover {{
            background: #005511;
        }}
        .btn-check {{
            background: #0066cc;
            color: white;
        }}
        .btn-check:hover {{
            background: #0055aa;
        }}
        .album-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 10px;
        }}
        .album-item {{
            background: white;
            padding: 12px;
            border-radius: 6px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .album-title {{
            font-weight: bold;
            color: #333;
            font-size: 14px;
        }}
        .album-artist {{
            color: #666;
            font-size: 12px;
        }}
        .album-links {{
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }}
        .album-links a {{
            padding: 6px 12px;
            border-radius: 4px;
            text-decoration: none;
            font-size: 12px;
            display: inline-block;
        }}
        .btn-search {{
            background: #007722;
            color: white;
        }}
        .btn-search:hover {{
            background: #005511;
        }}
        .btn-done {{
            background: #e0e0e0;
            color: #333;
            cursor: pointer;
            border: 1px solid #ccc;
        }}
        .btn-done.completed {{
            background: #007722;
            color: white;
            border-color: #007722;
        }}
        .checkbox {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: #666;
        }}
        .progress {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 1000;
        }}
        .progress-bar {{
            width: 200px;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: #007722;
            transition: width 0.3s;
        }}
    </style>
</head>
<body>
    <h1>豆瓣音乐批量处理 - 搜索链接</h1>

    <div class="info">
        <p><strong>总数：</strong> {len(albums)} 个专辑</p>
        <p><strong>使用方法：</strong></p>
        <ol>
            <li>点击"批量打开 5 个链接"按钮，会在新标签页打开 5 个搜索结果</li>
            <li>在每个标签页中：找到对应专辑 → 点击"听过" → 添加标签</li>
            <li>完成后回到此页面，勾选"已完成"复选框</li>
            <li>继续处理下一批</li>
        </ol>
        <p><strong>标签建议：</strong> 艺术家名、作曲家名、厂牌名（如：ECM、Philips、DG）</p>
    </div>

    <div class="batch-controls">
        <button class="btn-open" onclick="openBatch(5)">批量打开 5 个链接</button>
        <button class="btn-open" onclick="openBatch(10)">批量打开 10 个链接</button>
        <button class="btn-check" onclick="markAllVisible()">标记可见为完成</button>
        <button onclick="saveProgress()">保存进度</button>
        <button onclick="loadProgress()">加载进度</button>
    </div>

    <div class="progress" id="progressBox">
        <div>进度：<span id="progressText">0 / {len(albums)}</span></div>
        <div class="progress-bar">
            <div class="progress-fill" id="progressBar" style="width: 0%"></div>
        </div>
    </div>

    <div class="album-list" id="albumList">
"""

    for i, album in enumerate(albums):
        safe_title = album['title'].replace('"', '&quot;').replace("'", '&#39;')
        safe_artist = album['artist'].replace('"', '&quot;').replace("'", '&#39;')

        # 豆瓣搜索链接
        search_query = f"{album['artist']} {album['title']}".strip()
        search_url = f"https://music.douban.com/search?query={search_query}&type=1"

        html += f"""
        <div class="album-item" id="album-{i}">
            <div class="checkbox">
                <input type="checkbox" id="check-{i}" onchange="updateProgress()">
                <label for="check-{i}">已完成</label>
            </div>
            <div class="album-title">{safe_title or '（无标题）'}</div>
            <div class="album-artist">{safe_artist or '（无艺术家）'}</div>
            <div class="album-links">
                <a href="{search_url}" target="_blank" class="btn-search" onclick="markAsDone({i}, false)">打开搜索</a>
            </div>
        </div>
"""

    html += """
    </div>

    <script>
        let batchIndex = 0;

        function openBatch(count) {
            const items = document.querySelectorAll('.album-item');
            let opened = 0;

            for (let i = batchIndex; i < items.length && opened < count; i++) {
                const checkbox = document.getElementById(`check-${i}`);
                if (!checkbox.checked) {
                    const link = items[i].querySelector('.btn-search');
                    link.click();
                    opened++;
                }
            }

            batchIndex += count;
            if (batchIndex >= items.length) batchIndex = 0;
        }

        function markAsDone(index, manual) {
            if (manual) {
                const checkbox = document.getElementById(`check-${index}`);
                checkbox.checked = true;
                updateProgress();
            }
        }

        function markAllVisible() {
            const visibleItems = document.querySelectorAll('.album-item:not([style*="display: none"])');
            visibleItems.forEach(item => {
                const checkbox = item.querySelector('input[type="checkbox"]');
                checkbox.checked = true;
            });
            updateProgress();
        }

        function updateProgress() {
            const total = document.querySelectorAll('.album-item').length;
            const completed = document.querySelectorAll('input[type="checkbox"]:checked').length;

            document.getElementById('progressText').textContent = `${completed} / ${total}`;
            document.getElementById('progressBar').style.width = `${(completed / total) * 100}%`;
        }

        function saveProgress() {
            const progress = [];
            document.querySelectorAll('.album-item').forEach((item, index) => {
                const checkbox = document.getElementById(`check-${index}`);
                if (checkbox.checked) {
                    progress.push(index);
                }
            });

            localStorage.setItem('douban_progress', JSON.stringify(progress));
            alert('进度已保存！');
        }

        function loadProgress() {
            const progress = localStorage.getItem('douban_progress');
            if (progress) {
                const indices = JSON.parse(progress);
                indices.forEach(index => {
                    const checkbox = document.getElementById(`check-${index}`);
                    if (checkbox) {
                        checkbox.checked = true;
                    }
                });
                updateProgress();
                alert('进度已加载！');
            }
        }

        // 初始化进度
        updateProgress();
    </script>
</body>
</html>
"""

    output_path = Path(output_file)
    output_path.write_text(html, encoding='utf-8')
    print(f"已生成搜索链接文件：{output_path}")
    print(f"共 {len(albums)} 个专辑")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='生成豆瓣音乐搜索链接')
    parser.add_argument('--path', '-p', default='.', help='专辑目录路径')
    parser.add_argument('--output', '-o', default='search_links.html', help='输出文件路径')

    args = parser.parse_args()

    generate_search_links(args.path, args.output)
    print("\n使用方法：")
    print(f"1. 在浏览器中打开 {args.output}")
    print('2. 点击 [批量打开] 按钮开始处理')
