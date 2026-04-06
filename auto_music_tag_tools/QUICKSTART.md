# 豆瓣音乐批量处理 - 快速入门

## 一键启动

**Windows 用户**：双击运行 `scripts/run.bat`

脚本会自动：
1. 检查 Python 环境
2. 安装 Playwright (如未安装)
3. 检查 Cookie 文件
4. 引导你选择运行模式

---

## 手动使用

### 1. 安装依赖

```bash
pip install playwright
playwright install chromium
```

### 2. 获取 Cookie

**方法 A**: 使用图形化工具
1. 在浏览器中打开 `scripts/get_douban_cookie.html`
2. 确保已登录豆瓣
3. 点击"获取 Cookie"按钮
4. 复制到 `scripts/douban_cookie.txt`

**方法 B**: 手动获取
1. 登录 https://music.douban.com
2. 按 F12 打开开发者工具
3. 找到 Application -> Cookies
4. 复制 `dbcl2`, `gr`, `ck` 的值
5. 保存到 `scripts/douban_cookie.txt`

### 3. 运行脚本

```bash
# 测试模式 (推荐首次使用)
python scripts/run_douban_automation.py --test

# 处理所有专辑
python scripts/run_douban_automation.py --all

# 只处理 A 开头的专辑
python scripts/run_douban_automation.py --letter A

# 从 B 开头开始处理
python scripts/run_douban_automation.py --from B

# 空运行 (查看会处理哪些专辑)
python scripts/run_douban_automation.py --dry-run
```

---

## 输出文件

运行后会生成：

1. **JSON 结果** - `douban_results_YYYYMMDD_HHMMSS.json`
   ```json
   {
     "directory": "专辑目录",
     "title": "专辑标题",
     "artist": "艺术家",
     "status": "marked|created|not_found",
     "url": "豆瓣链接",
     "message": "处理信息"
   }
   ```

2. **Markdown 报告** - `douban_results_YYYYMMDD_HHMMSS.md`
   - 已标记的专辑列表
   - 未找到的专辑列表 (需要手动创建)

---

## 处理流程

对于每个专辑：

```
读取专辑信息 → 搜索豆瓣 → 匹配验证 → 标记已听 → 添加标签
                                            ↓
                                    未找到 → 记录待创建
```

### 标签规则

自动添加以下标签：
- 艺术家名 (例："Andrei Vieru")
- 厂牌名 (例："ECM", "Philips")
- 作曲家名 (例："Bach", "Debussy")

---

## 常见问题

### Q: Cookie 无效/过期
**A**: 重新获取 Cookie，豆瓣 Cookie 有效期约几天

### Q: 触发验证码
**A**: 暂停脚本，在浏览器手动完成验证码，等待 10-15 分钟后继续

### Q: 匹配度低
**A**: 脚本会跳过匹配度低于 0.3 的结果，避免误标记

### Q: 创建条目失败
**A**: 豆瓣目前不支持用户直接创建，需要手动提交至：
https://music.douban.com/new_subject

---

## 处理进度

总共约 **370 个专辑**，预计耗时：

| 模式 | 数量 | 预计时间 |
|------|------|----------|
| 测试 | 5 | ~1 分钟 |
| 单字母 | ~20 | ~5 分钟 |
| 全部 | 370 | ~60 分钟 |

**建议**：
1. 先用 `--test` 测试
2. 再用 `--letter A` 测试单个字母
3. 最后用 `--all` 批量处理

---

## 脚本文件说明

```
scripts/
├── run.bat                        # Windows 快速启动
├── run_douban_automation.py       # 主启动脚本
├── douban_automation.py           # 核心自动化逻辑
├── get_douban_cookie.html         # Cookie 获取工具
├── douban_cookie.txt              # Cookie 文件 (需创建)
├── README_DOUBAN.md               # 详细文档
└── QUICKSTART.md                  # 本文件
```

---

## 下一步

1. 运行测试模式确认环境正常
2. 检查输出结果是否符合预期
3. 开始批量处理
4. 处理未找到的专辑 (手动创建)

---

**遇到问题？** 查看 `README_DOUBAN.md` 获取详细文档
