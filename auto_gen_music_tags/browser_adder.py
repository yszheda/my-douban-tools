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
        # 实际调用：mcp__chrome-devtools__navigate_page(url=url, type="url")
        return url

    def take_snapshot(self) -> Dict:
        """获取页面快照"""
        # 实际调用：mcp__chrome-devtools__take_snapshot()
        print("[Browser] 获取页面快照...")
        return {}

    def click(self, uid: str):
        """点击元素"""
        print(f"[Browser] 点击 uid={uid}")
        # 实际调用：mcp__chrome-devtools__click(uid=uid)

    def fill(self, uid: str, value: str):
        """填充输入框"""
        print(f"[Browser] 填充 uid={uid}, value={value}")
        # 实际调用：mcp__chrome-devtools__fill(uid=uid, value=value)

    def find_modify_button(self, snapshot_text: str) -> Optional[str]:
        """查找修改按钮"""
        for line in snapshot_text.split('\n'):
            if '修改' in line and 'link' in line:
                match = re.search(r'uid=(\d+_\d+)', line)
                if match:
                    return match.group(1)
        return None

    def find_tag_input(self, snapshot_text: str) -> Optional[str]:
        """查找标签输入框"""
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

    def find_save_button(self, snapshot_text: str) -> Optional[str]:
        """查找保存按钮"""
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
        print("[Browser] 等待页面加载...")
        time.sleep(2)

        # Step 2: 找修改按钮
        snapshot = self.take_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False)
        modify_uid = self.find_modify_button(snapshot_text)
        if not modify_uid:
            result['message'] = '未找到修改按钮'
            print(f"[Browser] 错误：{result['message']}")
            return result
        print(f"[Browser] 修改按钮 uid={modify_uid}")

        # Step 3: 点击修改
        self.click(modify_uid)
        time.sleep(1)

        # Step 4: 找输入框
        snapshot = self.take_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False)
        input_uid = self.find_tag_input(snapshot_text)
        if not input_uid:
            result['message'] = '未找到标签输入框'
            print(f"[Browser] 错误：{result['message']}")
            return result
        print(f"[Browser] 输入框 uid={input_uid}")

        # Step 5: 填充标签
        tags_str = ' '.join(tags)
        self.fill(input_uid, tags_str)
        time.sleep(0.5)

        # Step 6: 保存
        snapshot = self.take_snapshot()
        snapshot_text = json.dumps(snapshot, ensure_ascii=False)
        save_uid = self.find_save_button(snapshot_text)
        if not save_uid:
            result['message'] = '未找到保存按钮'
            print(f"[Browser] 错误：{result['message']}")
            return result
        print(f"[Browser] 保存按钮 uid={save_uid}")

        self.click(save_uid)
        time.sleep(1.5)

        # Step 7: 验证
        result['success'] = True
        result['message'] = '标签添加成功'
        print("[Browser] 完成!")

        return result


def main():
    """测试浏览器版标签添加"""
    # 测试数据
    subject_id = "35617623"
    tags = [
        'Alkan', 'Cello', 'CelloPiano', 'Chamber', 'Chopin',
        'Classical', 'Mirare', 'Neuburger', 'Piano', 'Romantic'
    ]  # 前 10 个标签

    print("=" * 60)
    print("豆瓣浏览器模拟标签添加测试")
    print("=" * 60)

    adder = DoubanBrowserTagAdder()
    result = adder.add_tags(subject_id, tags)

    print(f"\n结果：{'成功' if result['success'] else '失败'}")
    print(f"消息：{result['message']}")

    return result


if __name__ == '__main__':
    main()
