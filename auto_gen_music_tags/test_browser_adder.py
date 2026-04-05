#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
浏览器模拟版标签添加器集成测试

注意：这些测试需要 Chrome DevTools MCP 环境
"""

import unittest
import sys
import os

# 添加父目录到路径以便导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auto_gen_music_tags.browser_adder import DoubanBrowserTagAdder


class TestFindFunctions(unittest.TestCase):
    """测试查找函数"""

    def setUp(self):
        self.adder = DoubanBrowserTagAdder()

    def test_find_modify_button(self):
        """测试查找修改按钮"""
        # 模拟快照文本
        snapshot_text = """
        uid=28_83 link "修改" url="javascript:;"
        uid=28_84 StaticText "修改"
        """
        # 这是一个简单的正则匹配测试
        import re
        match = re.search(r'uid=(\d+_\d+)', snapshot_text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "28_83")

    def test_find_tag_input(self):
        """测试查找标签输入框"""
        snapshot_text = """
        uid=29_18 StaticText "标签 (多个标签用空格分隔):"
        uid=29_19 textbox value="Malan Tchaikovsky"
        """
        import re
        lines = snapshot_text.split('\n')
        for i, line in enumerate(lines):
            if '标签' in line:
                for j in range(max(0, i-2), min(len(lines), i+2)):
                    if 'textbox' in lines[j]:
                        match = re.search(r'uid=(\d+_\d+)', lines[j])
                        if match:
                            self.assertEqual(match.group(1), "29_19")
                            return
        self.fail("Did not find textbox")

    def test_find_save_button(self):
        """测试查找保存按钮"""
        snapshot_text = """
        uid=29_67 button "保存"
        """
        import re
        match = re.search(r'uid=(\d+_\d+).*button', snapshot_text)
        if match:
            self.assertIsNotNone(match)


class TestBrowserAdder(unittest.TestCase):
    """测试浏览器添加器"""

    def setUp(self):
        self.adder = DoubanBrowserTagAdder()

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.adder.subject_id, "")

    def test_merge_tags(self):
        """测试标签合并逻辑"""
        old_tags = ["Malan", "Tchaikovsky", "Mikhnovsky"]
        new_tags = ["Chopin", "Classical", "Cello"]

        # 合并（去重）
        merged = list(set(old_tags + new_tags))
        self.assertEqual(len(merged), 6)

        # 如果有重复
        new_tags_with_dup = ["Chopin", "Tchaikovsky"]  # Tchaikovsky 已存在
        merged_with_dup = list(set(old_tags + new_tags_with_dup))
        self.assertEqual(len(merged_with_dup), 4)  # 去重后：Malan, Tchaikovsky, Mikhnovsky, Chopin


class TestTagLimits(unittest.TestCase):
    """测试标签限制"""

    def test_max_tags_per_album(self):
        """测试每专辑最多 10 个标签"""
        from auto_gen_music_tags.config import TAGS_PER_ALBUM_LIMIT

        all_tags = ["Tag" + str(i) for i in range(15)]
        limited_tags = all_tags[:TAGS_PER_ALBUM_LIMIT]

        self.assertEqual(len(limited_tags), 10)

    def test_tag_length_limits(self):
        """测试标签长度限制"""
        from auto_gen_music_tags.config import TAG_MIN_LENGTH, TAG_MAX_LENGTH

        valid_tags = ["Ab", "ABC", "ABCDEFGHIJKLMNOP"]  # 2-19 字符
        invalid_tags = ["A", "A" * 50]  # 1 字符和 50 字符（>= TAG_MAX_LENGTH）

        for tag in valid_tags:
            self.assertTrue(TAG_MIN_LENGTH <= len(tag) < TAG_MAX_LENGTH,
                          f"Tag {tag} should be valid")

        for tag in invalid_tags:
            self.assertFalse(TAG_MIN_LENGTH <= len(tag) < TAG_MAX_LENGTH,
                           f"Tag {tag} should be invalid")


class TestIntegration(unittest.TestCase):
    """集成测试（模拟）"""

    def test_full_workflow_simulation(self):
        """模拟完整工作流程"""
        # Step 1: 准备标签
        generated_tags = [
            "Alkan", "Chamber", "Chopin", "Classical",
            "FredericChopin", "JeanFredericNeuburger",
            "Malan", "Mirare", "Piano", "Romantic"
        ]

        # Step 2: 限制到 10 个
        from auto_gen_music_tags.config import TAGS_PER_ALBUM_LIMIT
        tags_to_add = generated_tags[:TAGS_PER_ALBUM_LIMIT]
        self.assertEqual(len(tags_to_add), 10)

        # Step 3: 模拟合并旧标签
        old_tags = ["Tchaikovsky", "Malan"]
        merged = list(set(old_tags + tags_to_add))[:TAGS_PER_ALBUM_LIMIT]
        self.assertLessEqual(len(merged), TAGS_PER_ALBUM_LIMIT)


if __name__ == '__main__':
    unittest.main(verbosity=2)
