# 豆瓣音乐批量标签添加 - 并行执行设计

**日期:** 2026-04-06  
**状态:** 用户批准，待实施

---

## 目标

为 6391 张豆瓣音乐专辑批量添加标签，使用 3 个并行工作树同时执行。

---

## 架构概述

```
工作树 A (索引 0-2130)     工作树 B (索引 2131-4260)     工作树 C (索引 4261-6391)
     ↓                          ↓                           ↓
独立 Python 生成标签        独立 Python 生成标签         独立 Python 生成标签
     ↓                          ↓                           ↓
独立 MCP 添加标签           独立 MCP 添加标签            独立 MCP 添加标签
     ↓                          ↓                           ↓
progress_a.json           progress_b.json            progress_c.json
```

### 工作树隔离

每个工作树有独立的：
- 进度文件
- 结果文件
- 日志输出
- Claude Code 会话

---

## 数据分配

| 工作树 | 起始索引 | 结束索引 | 专辑数量 | 预计时间 |
|--------|----------|----------|----------|----------|
| A      | 0        | 2130     | 2131 张  | ~9 小时  |
| B      | 2131     | 4260     | 2130 张  | ~9 小时  |
| C      | 4261     | 6391     | 2131 张  | ~9 小时  |

**总预计时间:** ~9 小时（并行执行）

---

## 执行流程（每个工作树）

### Phase 1: 标签生成（离线 Python）

```python
# 读取 album_list_full.json[start:end]
# 逐张调用 tag_generator.py 生成标签
# 保存到 tags_batch_{a,b,c}.json
```

### Phase 2: 标签添加（MCP 浏览器模拟）

```
for each album in batch:
    1. navigate_page(url) → 导航到专辑页面
    2. take_snapshot() → 查找"修改"按钮
    3. click(uid) → 打开编辑对话框
    4. take_snapshot() → 读取已有标签
    5. fill(uid, "旧标签 + 新标签") → 合并填充
    6. take_snapshot() → 查找"保存"按钮
    7. click(uid) → 保存
    8. 每 10 张保存进度到 progress_{a,b,c}.json
```

---

## 输出文件

| 文件 | 说明 |
|------|------|
| `tags_batch_a.json` | 工作树 A 生成的标签数据 |
| `tags_batch_b.json` | 工作树 B 生成的标签数据 |
| `tags_batch_c.json` | 工作树 C 生成的标签数据 |
| `progress_a.json` | 工作树 A 添加进度 |
| `progress_b.json` | 工作树 B 添加进度 |
| `progress_c.json` | 工作树 C 添加进度 |
| `result_a.json` | 工作树 A 添加结果 |
| `result_b.json` | 工作树 B 添加结果 |
| `result_c.json` | 工作树 C 添加结果 |
| `final_summary.json` | 合并后的总结果 |

---

## 错误处理

### 标签生成失败
- 记录到 `failed_generation.json`
- 可单独重试

### 标签添加失败
- 可能原因：ck 过期、页面结构变化、网络问题
- 记录到 `failed_add_{a,b,c}.json`
- 可单独重试

### 中断恢复
- 每个工作树独立保存进度
- 从 `progress_{a,b,c}.json` 读取 `current_index` 恢复

---

## 成功标准

- **成功率 ≥ 90%**: 至少 5750 张专辑成功添加标签
- **旧标签保留**: 编辑时正确合并已有标签
- **进度可恢复**: 中断后可从断点继续

---

## 监控方式

每个工作树输出格式统一的日志：
```
[Batch A] 处理 150/2131: 37371348 - 生成 8 个标签 - 添加成功
[Batch B] 处理 890/2130: 35617623 - 生成 10 个标签 - 添加成功
[Batch C] 处理 1200/2131: 34514855 - 生成 6 个标签 - 添加失败：ck 过期
```

---

## 合并结果

所有工作树完成后，运行合并脚本：
```bash
python merge_results.py
```

输出 `final_summary.json`：
```json
{
  "total_albums": 6391,
  "total_success": 5800,
  "total_failed": 591,
  "success_rate": "90.75%",
  "completed_at": "2026-04-06T23:00:00"
}
```
