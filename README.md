# 豆瓣音乐 CD 条形码查询与标记工具

这是一个 Python 程序，可以根据 CD 的条形码在豆瓣音乐网站上查找对应的条目，并将其标记为"在听"状态。

## 功能特点

- 根据 CD 条形码在豆瓣音乐网站搜索对应条目
- 自动登录豆瓣账号
- 将找到的音乐条目标记为"在听"状态
- **自动标签添加**：从多数据源（Discogs、MusicBrainz 等）查询古典音乐专辑元数据，自动生成标签
- **批量处理**：支持为用户的收藏列表（听过/在听/想听）批量添加标签

## 安装

1. 确保已安装 Python 3.6 或更高版本
2. 克隆或下载此仓库
3. 安装依赖包：

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本用法

```bash
python douban_music.py <条形码>
```

程序会提示你输入豆瓣账号和密码。

### 带参数的用法

```bash
python douban_music.py <条形码> -u <豆瓣用户名> -p <豆瓣密码>
```

### 示例

```bash
# 基本用法
python douban_music.py 0099925362621

# 带参数的用法
python douban_music.py 0099925362621 -u your_username -p your_password
```

## 自动标签添加

### 查询标签数据

```bash
python classical_tagger.py
```

这会从以下数据源查询专辑信息并生成标签：
- Discogs
- MusicBrainz
- Deezer
- iTunes
- Last.fm
- AllMusic

### 添加标签到豆瓣

**API 版本**（快速，但可能不稳定）：
```bash
python add_tags_auto.py
```

**浏览器模拟版本**（稳定，需要 Claude Code + Chrome DevTools MCP）：
```bash
python douban_tagger_batch.py
```

详细使用说明请参考 [README_TAGGER.md](README_TAGGER.md)

## 注意事项

- 本程序仅用于个人学习和使用
- 请勿频繁使用，以免对豆瓣服务器造成压力
- 豆瓣网站结构可能会变化，如遇问题请更新程序
- 批量处理时请设置适当的延迟，避免触发反机器人机制

## 依赖库

- requests: 用于发送 HTTP 请求
- beautifulsoup4: 用于解析 HTML
- lxml: 用于提供 HTML 解析器

## 项目文件结构

```
douban/
├── douban_music.py           # 主程序：条形码查询与标记
├── classical_tagger.py       # 古典音乐标签查询工具
├── add_tags_auto.py          # API 版标签添加
├── douban_tagger_batch.py    # 浏览器模拟版标签添加（批量）
├── douban_tagger_run.py      # 浏览器模拟版（精简）
├── tag_result.json           # 标签数据输出
├── cookie.txt                # 豆瓣 cookie（需手动配置）
├── README.md                 # 主说明文档
├── README_TAGGER.md          # 标签工具详细说明
└── CLAUDE.md                 # 开发与使用备忘录
```
