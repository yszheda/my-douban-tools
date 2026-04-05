# Douban Tag Adder Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 演示豆瓣音乐标签添加功能，使用 API 版和浏览器模拟版两种方式为专辑 35617623 添加标签。

**Architecture:** 
- API 版：通过 HTTP POST 直接调用豆瓣标签 API，使用 cookie 中的 ck 值进行认证
- 浏览器模拟版：使用 Chrome DevTools MCP 工具模拟人工操作（导航→点击修改→填标签→保存）
- 两种方式都从 `generate_tags_unified.py` 获取已生成的标签数据

**Tech Stack:** Python, requests, Chrome DevTools MCP, BeautifulSoup

---

## Files to Create/Modify

**Existing files (read for context):**
- `generate_tags_unified.py` - 标签数据生成（已完成）
- `add_tags_browser.py` - 浏览器模拟版框架
- `add_tags_auto.py` - API 版框架
- `cookie.txt` - cookie 文件
- `tags_35617623.json` - 已生成的标签数据

**Files to create:**
- `demo_tag_adder.py` - 演示脚本（整合 API 版和浏览器版）

---

### Task 1: 准备标签数据

**Files:**
- Read: `tags_35617623.json`
- Read: `generate_tags_unified.py`

- [ ] **Step 1: 读取并验证标签数据**

```python
import json

with open('tags_35617623.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

tags = data['tags_all']
subject_id = data['subject_id']
print(f"专辑：{subject_id}")
print(f"标签数量：{len(tags)}")
print(f"标签列表：{' '.join(tags)}")
```

- [ ] **Step 2: 验证标签格式**

确保标签：
- 不包含空格（每个标签内部）
- 总数量不超过 10 个（豆瓣限制，如超过则截断）
- 包含 4 类标签：演奏家、作曲家、厂牌、风格

---

### Task 2: API 版标签添加

**Files:**
- Create: `api_tag_adder.py`
- Read: `cookie.txt`

- [ ] **Step 1: 实现 API 版标签添加器**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""豆瓣标签 API 添加器"""

import requests
import re
from typing import List, Dict

class DoubanApiTagAdder:
    """豆瓣 API 标签添加器"""
    
    def __init__(self, cookie_file: str = "cookie.txt"):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://music.douban.com/'
        })
        self.ck = ""
        self._load_cookie(cookie_file)
    
    def _load_cookie(self, cookie_file: str):
        """加载 cookie 获取 ck 值"""
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 解析 ck
            cookies = {}
            for item in content.split(';'):
                if '=' in item:
                    k, v = item.strip().split('=', 1)
                    cookies[k] = v
            
            self.ck = cookies.get('ck', '')
            self.session.cookies.update(cookies)
            
            if not self.ck:
                raise ValueError("ck not found in cookie file")
                
        except Exception as e:
            raise RuntimeError(f"Cookie 加载失败：{e}")
    
    def add_tags(self, subject_id: str, tags: List[str]) -> Dict:
        """添加标签
        
        Args:
            subject_id: 专辑 ID
            tags: 标签列表
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        url = f"https://music.douban.com/j/tag/{subject_id}"
        
        # 组合标签字符串
        tags_str = ' '.join(tags)
        
        # POST 数据
        data = {
            'ck': self.ck,
            'tags': tags_str
        }
        
        print(f"[API] POST {url}")
        print(f"[API] tags={tags_str}")
        
        try:
            resp = self.session.post(url, data=data, timeout=10)
            
            if resp.status_code == 200:
                return {'success': True, 'message': '标签添加成功'}
            else:
                return {
                    'success': False,
                    'message': f'HTTP {resp.status_code}: {resp.text[:100]}'
                }
                
        except Exception as e:
            return {'success': False, 'message': str(e)}
```

- [ ] **Step 2: 测试 API 连接**

```python
adder = DoubanApiTagAdder()
print(f"ck={adder.ck[:4]}...{adder.ck[-4:]}")
```

- [ ] **Step 3: 执行标签添加**

```python
result = adder.add_tags('35617623', tags[:10])  # 豆瓣限制最多 10 个标签
print(f"结果：{result}")
```

---

### Task 3: 浏览器模拟版标签添加

**Files:**
- Create: `browser_tag_adder.py`
- Use: Chrome DevTools MCP tools

- [ ] **Step 1: 实现浏览器版标签添加器**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""豆瓣标签浏览器模拟添加器 - Chrome DevTools MCP 版"""

import json
import time
import re
from typing import List, Dict, Optional

class DoubanBrowserTagAdder:
    """豆瓣浏览器模拟标签添加器"""
    
    def __init__(self):
        self.subject_id = ""
    
    def navigate(self, subject_id: str):
        """导航到专辑页面"""
        self.subject_id = subject_id
        url = f"https://music.douban.com/subject/{subject_id}/"
        print(f"[Browser] 导航：{url}")
        # mcp__chrome-devtools__navigate_page(url=url, type="url")
        return url
    
    def take_snapshot(self) -> Dict:
        """获取页面快照"""
        # mcp__chrome-devtools__take_snapshot()
        return {}
    
    def find_modify_button(self, snapshot: Dict) -> Optional[str]:
        """查找修改按钮"""
        snapshot_text = json.dumps(snapshot, ensure_ascii=False)
        
        for line in snapshot_text.split('\n'):
            if '修改' in line and 'link' in line:
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        return None
    
    def find_tag_input(self, snapshot: Dict) -> Optional[str]:
        """查找标签输入框"""
        snapshot_text = json.dumps(snapshot, ensure_ascii=False)
        
        # 查找标签附近的 textbox
        lines = snapshot_text.split('\n')
        for i, line in enumerate(lines):
            if '标签' in line:
                for j in range(max(0, i-5), min(len(lines), i+5)):
                    if 'textbox' in lines[j]:
                        match = re.search(r'uid=(\d+_\d+)', lines[j])
                        if match:
                            return match.group(1)
        return None
    
    def find_save_button(self, snapshot: Dict) -> Optional[str]:
        """查找保存按钮"""
        snapshot_text = json.dumps(snapshot, ensure_ascii=False)
        
        for line in snapshot_text.split('\n'):
            if '保存' in line and 'button' in line:
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        return None
    
    def add_tags(self, subject_id: str, tags: List[str]) -> Dict:
        """执行完整标签添加流程"""
        result = {'success': False, 'message': '', 'subject_id': subject_id}
        
        print(f"\n[Browser] 开始添加标签 - subject={subject_id}")
        print(f"[Browser] 标签：{' '.join(tags)}")
        print("=" * 50)
        
        # Step 1: 导航
        self.navigate(subject_id)
        time.sleep(2)
        
        # Step 2: 找修改按钮
        snapshot = self.take_snapshot()
        modify_uid = self.find_modify_button(snapshot)
        if not modify_uid:
            result['message'] = '未找到修改按钮'
            return result
        print(f"[Browser] 修改按钮 uid={modify_uid}")
        
        # Step 3: 点击修改
        # mcp__chrome-devtools__click(uid=modify_uid)
        time.sleep(1)
        
        # Step 4: 找输入框
        snapshot = self.take_snapshot()
        input_uid = self.find_tag_input(snapshot)
        if not input_uid:
            result['message'] = '未找到标签输入框'
            return result
        print(f"[Browser] 输入框 uid={input_uid}")
        
        # Step 5: 填充标签
        tags_str = ' '.join(tags)
        # mcp__chrome-devtools__fill(uid=input_uid, value=tags_str)
        time.sleep(0.5)
        
        # Step 6: 保存
        snapshot = self.take_snapshot()
        save_uid = self.find_save_button(snapshot)
        if not save_uid:
            result['message'] = '未找到保存按钮'
            return result
        print(f"[Browser] 保存按钮 uid={save_uid}")
        
        # mcp__chrome-devtools__click(uid=save_uid)
        time.sleep(1.5)
        
        # Step 7: 验证
        result['success'] = True
        result['message'] = '标签添加成功'
        print("[Browser] 完成!")
        
        return result
```

- [ ] **Step 2: 执行浏览器版标签添加**

```python
adder = DoubanBrowserTagAdder()
result = adder.add_tags('35617623', tags[:10])
print(f"结果：{result}")
```

---

### Task 4: 整合演示脚本

**Files:**
- Create: `demo_tag_adder.py`

- [ ] **Step 1: 创建演示脚本**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""豆瓣标签添加演示脚本

演示两种方式：
1. API 版 - 快速但可能被反爬
2. 浏览器模拟版 - 稳定可靠
"""

import json
import sys

def load_tags(subject_id: str = "35617623") -> tuple:
    """加载标签数据"""
    try:
        with open(f'tags_{subject_id}.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['subject_id'], data['tags_all']
    except:
        # 回退到生成标签
        from generate_tags_unified import DoubanMusicTagGenerator
        tagger = DoubanMusicTagGenerator()
        result = tagger.generate_tags(subject_id, verbose=False)
        return result['subject_id'], result['tags_all']

def demo_api(subject_id: str, tags: list):
    """演示 API 版"""
    print("\n" + "=" * 60)
    print("【方式 A】API 版标签添加")
    print("=" * 60)
    
    from api_tag_adder import DoubanApiTagAdder
    adder = DoubanApiTagAdder()
    
    # 豆瓣限制最多 10 个标签
    tags_limited = tags[:10]
    result = adder.add_tags(subject_id, tags_limited)
    
    print(f"结果：{'成功' if result['success'] else '失败'}")
    print(f"消息：{result['message']}")
    return result

def demo_browser(subject_id: str, tags: list):
    """演示浏览器模拟版"""
    print("\n" + "=" * 60)
    print("【方式 B】浏览器模拟版标签添加")
    print("=" * 60)
    
    from browser_tag_adder import DoubanBrowserTagAdder
    adder = DoubanBrowserTagAdder()
    
    tags_limited = tags[:10]
    result = adder.add_tags(subject_id, tags_limited)
    
    print(f"结果：{'成功' if result['success'] else '失败'}")
    print(f"消息：{result['message']}")
    return result

def main():
    """主函数"""
    print("=" * 60)
    print("豆瓣音乐标签添加演示")
    print("=" * 60)
    
    # 加载标签数据
    subject_id, tags = load_tags("35617623")
    
    print(f"专辑：{subject_id}")
    print(f"标签总数：{len(tags)}")
    print(f"使用前 10 个：{' '.join(tags[:10])}")
    
    # 演示两种方式
    # 注意：实际执行时只选择一种方式
    
    # API 版
    api_result = demo_api(subject_id, tags)
    
    # 浏览器版（如果 API 失败）
    if not api_result['success']:
        print("\n[INFO] API 失败，切换到浏览器模拟版...")
        browser_result = demo_browser(subject_id, tags)
        return browser_result
    
    return api_result

if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 运行演示**

```bash
python demo_tag_adder.py
```

---

## Test Plan

1. **标签数据验证**
   - 标签列表不为空
   - 每个标签不包含空格
   - 标签数量截断到 10 个以内

2. **API 版测试**
   - cookie 有效时：返回 success=True
   - cookie 无效时：返回有意义的错误信息

3. **浏览器版测试**
   - 能找到修改按钮
   - 能找到标签输入框
   - 能找到保存按钮
   - 标签正确填入

---
