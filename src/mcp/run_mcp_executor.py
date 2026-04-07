#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运行豆瓣音乐 MCP 自动标签添加器

在 Claude Code 环境中执行，使用 MCP Chrome DevTools 工具
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入执行器
from mcp_executor import McpExecutor

def run_executor():
    """创建执行器并运行"""
    executor = McpExecutor(
        cookie_file="cookie.txt",
        album_list_file="album_list_full.json"
    )

    # 运行完整批次
    executor.run(start_index=0, end_index=6390)

    return executor

if __name__ == '__main__':
    run_executor()
