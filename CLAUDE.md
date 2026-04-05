# 豆瓣音乐工具 - CLAUDE.md

## 项目概述

豆瓣音乐自动化工具，包括：
1. CD 条形码查询与标记
2. 古典音乐标签数据聚合
3. 自动标签添加（API 版 + 浏览器模拟版）

## 目标专辑与用户

- 示例专辑：https://music.douban.com/subject/37133003/ (Mozart: Die Entführung aus dem Serail, Josef Krips)
- 条形码：0028948071913
- 用户 ID：63343218
  - 听过：https://music.douban.com/people/63343218/collect
  - 在听：https://music.douban.com/people/63343218/do
  - 想听：https://music.douban.com/people/63343218/wish

## 标签数据源

查询古典音乐专辑元数据的优先级：
1. Discogs API（需要 token）
2. MusicBrainz API（无需授权）
3. Deezer API（无需授权）
4. iTunes API（无需授权）
5. Last.fm API（可选授权）
6. AllMusic（网页抓取）

## 标签添加工具

### API 版 (add_tags_auto.py)
- 通过 HTTP POST 直接调用豆瓣标签 API
- 快速但不稳定，可能被反爬
- Endpoint 尝试：`/j/tag/{subject_id}`

### 浏览器模拟版 (douban_tagger_batch.py)
- 调用 Chrome DevTools MCP 工具
- 模拟人工操作：导航 → 点击修改 → 填标签 → 保存
- 稳定可靠，绕过反爬

## Cookie 配置

`cookie.txt` 格式：
```
ck=yzVU; other_cookie=value; ...
```

ck 值用于 API 请求认证，会从页面或 cookie 中自动提取。

## 生成的标签示例

针对 Mozart: Die Entführung aus dem Serail (barcode: 0028948071913)：
```
Decca, DieEntführungAusDemSerail, JosefKrips, KV384, 
LondonSymphonyOrchestra, Mozart, WienerPhilharmoniker, 
Classical, Opera
```

## 开发与使用注意事项

1. **反机器人机制**：批量处理时设置 delay ≥ 3 秒
2. **ck 有效期**：ck 值会过期，失败时重新获取
3. **标签数量**：建议不超过 10 个/专辑
4. **网络环境**：部分国际 API 可能需要特殊网络

## 执行流程（浏览器模拟版）

```
1. navigate_page(url) → 导航到专辑页面
2. take_snapshot() → 查找"修改"按钮 uid
3. click(uid) → 打开修改对话框
4. take_snapshot() → 查找标签输入框 uid
5. fill(uid, "tag1 tag2 ...") → 填入标签
6. take_snapshot() → 查找"保存"按钮 uid
7. click(uid) → 保存
8. take_snapshot() → 验证结果
```

## 标签编辑规则（重要）

**当专辑已有标签和短评时，编辑标签只能增加新标签，不能删除旧标签或短评。**

浏览器模拟版实现方式：
1. 打开编辑对话框后，先读取输入框中现有的标签
2. 将新标签与旧标签合并（去重）
3. 填充完整标签列表到输入框
4. 保存

违反此规则会导致用户已有的收藏标记信息丢失。

## 相关文件

- `classical_tagger.py` - 标签数据查询聚合
- `add_tags_auto.py` - API 版标签添加
- `douban_tagger_batch.py` - 浏览器模拟版（批量）
- `tag_result.json` - 标签数据输出
- `README_TAGGER.md` - 标签工具详细说明
