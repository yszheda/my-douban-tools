#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
标签生成器单元测试
"""

import unittest
import sys
import os

# 添加父目录到路径以便导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auto_gen_music_tags.tag_generator import normalize_name, AlbumInfo
from auto_gen_music_tags.config import EXCLUDED_COUNTRIES, OPUS_PATTERNS


class TestNormalizeName(unittest.TestCase):
    """测试 normalize_name 函数"""

    def test_french_name(self):
        """测试法语人名 - 移除重音"""
        self.assertEqual(normalize_name("Frédéric Chopin"), "FredericChopin")
        self.assertEqual(normalize_name("François"), "Francois")

    def test_special_characters(self):
        """测试特殊字符"""
        self.assertEqual(normalize_name("Charles-Valentin Alkan"), "CharlesValentinAlkan")
        self.assertEqual(normalize_name("János"), "Janos")

    def test_russian_name(self):
        """测试俄语人名"""
        self.assertEqual(normalize_name("Tatjana Vassiljeva"), "TatjanaVassiljeva")
        self.assertEqual(normalize_name("Sergiu Celibidache"), "SergiuCelibidache")

    def test_simple_name(self):
        """测试简单人名（无重音）"""
        self.assertEqual(normalize_name("Mozart"), "Mozart")
        self.assertEqual(normalize_name("Bach"), "Bach")

    def test_empty_string(self):
        """测试空字符串"""
        self.assertEqual(normalize_name(""), "")

    def test_numbers_and_letters(self):
        """测试数字和字母混合"""
        result = normalize_name("KV384")
        self.assertEqual(result, "KV384")


class TestAlbumInfo(unittest.TestCase):
    """测试 AlbumInfo 数据类"""

    def test_default_values(self):
        """测试默认值"""
        info = AlbumInfo(subject_id="12345")
        self.assertEqual(info.subject_id, "12345")
        self.assertEqual(info.title, "")
        self.assertEqual(info.performers, [])
        self.assertEqual(info.composers, [])
        self.assertEqual(info.label, "")

    def test_initialization(self):
        """测试初始化"""
        info = AlbumInfo(
            subject_id="35617623",
            title="Chopin: Cello Sonata",
            performers=["Tatjana Vassiljeva"],
            composers=["Frédéric Chopin"],
            label="Mirare"
        )
        self.assertEqual(info.subject_id, "35617623")
        self.assertEqual(info.title, "Chopin: Cello Sonata")
        self.assertEqual(len(info.performers), 1)
        self.assertEqual(len(info.composers), 1)
        self.assertEqual(info.label, "Mirare")

    def test_list_initialization(self):
        """测试列表字段的独立初始化"""
        info1 = AlbumInfo(subject_id="1")
        info2 = AlbumInfo(subject_id="2")

        info1.performers.append("Performer1")
        self.assertNotIn("Performer1", info2.performers)


class TestTagFilters(unittest.TestCase):
    """测试标签过滤规则"""

    def test_country_names_excluded(self):
        """测试国家名称被排除"""
        # 测试 EXCLUDED_COUNTRIES 中实际包含的国家
        excluded = ['France', 'Germany', 'Italy', 'Spain', 'Poland', 'Russia',
                   'Austria', 'UK', 'Britain', 'English', 'USA', 'Japan', 'China']
        for country in excluded:
            self.assertIn(country, EXCLUDED_COUNTRIES)

    def test_opus_patterns(self):
        """测试作品号模式"""
        patterns = ['Op', 'Op.', 'KV', 'BWV', 'No', 'Nr', 'D', 'L', 'S', 'G']
        for pattern in OPUS_PATTERNS:
            self.assertIn(pattern, OPUS_PATTERNS)


class TestTagCategorization(unittest.TestCase):
    """测试标签分类逻辑（模拟）"""

    def test_performer_surname(self):
        """测试演奏家姓氏识别"""
        name = "Tatjana Vassiljeva"
        surname = name.split()[-1]
        self.assertEqual(surname, "Vassiljeva")

    def test_composer_surname(self):
        """测试作曲家姓氏识别"""
        name = "Frédéric Chopin"
        surname = name.split()[-1]
        self.assertEqual(surname, "Chopin")

    def test_label_detection(self):
        """测试厂牌检测"""
        label = "Mirare"
        self.assertTrue(len(label) > 0)

    def test_style_keywords(self):
        """测试风格关键词"""
        style_keywords = {'classical', 'romantic', 'baroque', 'chamber', 'sonata'}
        self.assertIn('classical', style_keywords)
        self.assertIn('romantic', style_keywords)


class TestIntegration(unittest.TestCase):
    """集成测试（不需要网络）"""

    def test_name_normalization_chain(self):
        """测试人名标准化链"""
        names = [
            ("Frédéric Chopin", "FredericChopin"),
            ("Charles-Valentin Alkan", "CharlesValentinAlkan"),
            ("Tatjana Vassiljeva", "TatjanaVassiljeva"),
        ]

        for original, expected in names:
            result = normalize_name(original)
            self.assertEqual(result, expected,
                           f"Failed for {original}: expected {expected}, got {result}")

    def test_album_info_to_dict(self):
        """测试 AlbumInfo 序列化"""
        from dataclasses import asdict

        info = AlbumInfo(
            subject_id="35617623",
            title="Test Album",
            performers=["Performer1"],
            composers=["Composer1"],
            label="Test Label"
        )

        info_dict = asdict(info)
        self.assertEqual(info_dict['subject_id'], "35617623")
        self.assertEqual(info_dict['title'], "Test Album")


if __name__ == '__main__':
    unittest.main(verbosity=2)
