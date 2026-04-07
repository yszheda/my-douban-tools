#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运行所有测试
"""

import unittest
import sys
import os

# 添加父目录到路径以便导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_all_tests():
    """运行所有测试"""
    #  discover 测试文件
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()

    # 添加测试文件
    test_files = [
        'test_tag_generator',
        'test_browser_adder',
        'test_api_adder',
    ]

    for test_file in test_files:
        try:
            module = __import__(f'auto_gen_music_tags.{test_file}', fromlist=[''])
            tests = test_loader.loadTestsFromModule(module)
            test_suite.addTests(tests)
            print(f"[OK] 加载 {test_file}")
        except Exception as e:
            print(f"[X] 无法加载 {test_file}: {e}")

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # 打印摘要
    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    print(f"运行测试数：{result.testsRun}")
    print(f"成功：{result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败：{len(result.failures)}")
    print(f"错误：{len(result.errors)}")

    if result.failures:
        print("\n失败详情:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback[:100]}...")

    if result.errors:
        print("\n错误详情:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback[:100]}...")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
