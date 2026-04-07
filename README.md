# 豆瓣音乐自动化工具 (my-douban-tools)

豆瓣音乐自动化工具集，支持 CD 条形码查询、标签数据聚合、批量标签添加和收藏列表导出。

## 目录结构

```
my-douban-tools/
├── src/                        # Python 源代码
│   ├── core/                   # 核心业务逻辑
│   │   ├── auto_export.py          # 自动导出脚本
│   │   ├── batch_processor.py      # 批量处理器
│   │   ├── collector.py            # 数据收集器
│   │   ├── export_collections.py   # 导出收藏列表
│   │   ├── tag_generator.py        # 标签生成器
│   │   └── ...
│   ├── mcp/                    # MCP 工具相关代码
│   │   ├── mcp_executor.py         # MCP 执行器框架
│   │   ├── mcp_tagger.py           # MCP 标签添加器
│   │   ├── mcp_batch_executor.py   # MCP 批量执行器
│   │   └── ...
│   ├── utils/                  # 工具函数和调试脚本
│   │   ├── batch_add_tags.py       # 批量添加标签
│   │   ├── find_missing.py         # 查找缺失数据
│   │   └── debug_*.py              # 调试脚本集合
│   └── config.py               # 统一配置模块
├── tools/                      # 浏览器/命令行工具脚本
│   ├── browser/                # 浏览器自动化脚本
│   └── cli/                    # 命令行工具脚本
│       ├── auto_collect_all.js     # 自动收集所有数据
│       ├── inject_ids.js           # 注入 ID 脚本
│       └── ...
├── config/                     # 配置文件
│   └── settings.json           # 项目配置
├── data/                       # 数据文件
│   ├── raw/                    # 原始数据
│   └── processed/              # 处理后的数据
├── logs/                       # 日志文件
├── docs/                       # 文档
│   └── superpowers/            # Superpowers 技能文档
│       ├── plans/              # 实现计划
│       └── specs/              # 设计规格
├── .gitignore                  # Git 忽略规则
├── CLAUDE.md                   # 开发与使用备忘录
└── README.md                   # 本文件
```

## 功能模块

### 1. CD 条形码查询与标记
根据 CD 条形码在豆瓣音乐网站查找对应条目，并标记为"在听"状态。

### 2. 自动标签生成
从多个数据源查询古典音乐专辑元数据，自动生成标签：
- Discogs API
- MusicBrainz API
- Deezer API
- iTunes API
- Last.fm API
- AllMusic（网页抓取）

### 3. 批量标签添加
提供两种标签添加方式：

**API 版本**（快速，但可能不稳定）：
```bash
python src/mcp/mcp_executor.py
```

**浏览器模拟版本**（稳定，需要 Claude Code + Chrome DevTools MCP）：
```bash
python src/utils/batch_add_tags.py
```

### 4. 收藏列表导出
导出豆瓣音乐收藏列表（听过/在听/想听）：
```bash
python src/core/auto_export.py
```

## 快速开始

### 安装依赖

```bash
pip install requests beautifulsoup4 lxml
```

### 配置 Cookie

创建 `cookie.txt` 文件，格式：
```
ck=yzVU; other_cookie=value; ...
```

### 运行示例

```bash
# 查询标签数据
python src/core/tag_generator.py

# 批量添加标签（MCP 版本）
python src/mcp/mcp_executor.py --resume

# 导出收藏列表
python src/core/auto_export.py
```

## 配置说明

项目配置位于 `config/settings.json`，包括：
- 标签数量限制
- API 超时设置
- 批量处理延迟
- 文件路径配置

Python 代码可通过 `src/config.py` 模块加载配置。

## 开发与使用注意事项

1. **反机器人机制**：批量处理时设置 delay ≥ 3 秒
2. **ck 有效期**：ck 值会过期，失败时重新获取
3. **标签数量**：建议不超过 10 个/专辑
4. **标签编辑规则**：当专辑已有标签和短评时，只能增加新标签，不能删除旧标签

## 相关文档

- [CLAUDE.md](CLAUDE.md) - 开发与使用备忘录
- [docs/superpowers/](docs/superpowers/) - Superpowers 技能文档
- [TAGGER_README.md](TAGGER_README.md) - 标签工具详细说明
- [EXPORT_GUIDE.md](EXPORT_GUIDE.md) - 导出指南

## 用户信息

- 用户 ID: 63343218
- 听过：https://music.douban.com/people/63343218/collect
- 在听：https://music.douban.com/people/63343218/do
- 想听：https://music.douban.com/people/63343218/wish

## 许可证

本工具仅供个人学习和使用。
