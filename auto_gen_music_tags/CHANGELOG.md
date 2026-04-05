# 变更日志

## [1.0.0] - 2026-04-06

### 新增
- 整合 10 个数据源的标签生成器 (`tag_generator.py`)
  - 豆瓣音乐页面
  - MusicBrainz API
  - Presto Music
  - Discogs
  - Last.fm
  - iTunes API
  - Deezer API
  - Spotify
  - AllMusic
  - Wikipedia

- 浏览器模拟版标签添加器 (`browser_adder.py`)
  - 使用 Chrome DevTools MCP 工具
  - 模拟人工操作流程
  - 保留旧标签和短评

- API 版标签添加器 (`api_adder.py`)
  - HTTP POST 直接调用豆瓣 API
  - 逐标签提交模式

- 演示脚本 (`demo.py`)
  - 整合生成和添加流程
  - 支持两种添加方式选择

- 配置模块 (`config.py`)
  - 统一配置管理
  - 超时设置、标签限制、排除规则

### 文档
- `README.md` - 使用指南
- `DESIGN.md` - 设计文档
- `API.md` - API 接口文档
- `CHANGELOG.md` - 变更日志

### 测试
- `test_tag_generator.py` - 标签生成器单元测试
- `test_browser_adder.py` - 浏览器添加器集成测试
- `test_api_adder.py` - API 添加器单元测试
- `test_all.py` - 测试运行器

### 核心功能
- 标签标准化（人名去重音、无空格格式）
- 标签分类（演奏家、作曲家、厂牌、风格）
- 标签过滤（排除国家名、作品号）
- 旧标签保留机制（编辑时只增不删）
