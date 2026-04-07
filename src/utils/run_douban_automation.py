#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆瓣音乐批量处理工具 - 主启动脚本

功能：
1. 检查环境和依赖
2. 验证 Cookie 有效性
3. 批量处理专辑目录
4. 生成处理报告

使用方法:
    python scripts/run_douban_automation.py [选项]

示例:
    python scripts/run_douban_automation.py --test     # 测试模式，处理 5 个专辑
    python scripts/run_douban_automation.py --all      # 处理所有专辑
    python scripts/run_douban_automation.py --from A   # 从字母 A 开头的专辑开始
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime

# 颜色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_banner():
    """打印欢迎横幅"""
    print(f"{Colors.OKCYAN}")
    print("=" * 60)
    print("  豆瓣音乐批量处理工具")
    print("  古典音乐专辑收藏库")
    print("=" * 60)
    print(f"{Colors.ENDC}")

def check_dependencies():
    """检查依赖项"""
    print(f"\n{Colors.BOLD}检查依赖项...{Colors.ENDC}")

    missing = []

    # 检查 Python 版本
    if sys.version_info < (3, 7):
        print(f"{Colors.FAIL}[FAIL] Python 版本过低，需要 3.7+{Colors.ENDC}")
        return False
    print(f"{Colors.OKGREEN}[OK] Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}{Colors.ENDC}")

    # 检查 playwright
    try:
        import playwright
        print(f"{Colors.OKGREEN}[OK] Playwright 已安装{Colors.ENDC}")
    except ImportError:
        print(f"{Colors.FAIL}[FAIL] Playwright 未安装{Colors.ENDC}")
        missing.append('playwright')

    # 检查浏览器
    try:
        subprocess.run(['playwright', 'show-installed-browsers'],
                      capture_output=True, timeout=10)
        print(f"{Colors.OKGREEN}[OK] Chromium 浏览器已安装{Colors.ENDC}")
    except:
        print(f"{Colors.WARNING}[WARN] Chromium 浏览器可能未安装{Colors.ENDC}")
        print(f"  运行：{Colors.BOLD}playwright install chromium{Colors.ENDC}")

    if missing:
        print(f"\n{Colors.WARNING}安装缺失的依赖：{Colors.ENDC}")
        print(f"  pip install {' '.join(missing)}")
        if 'playwright' in missing:
            print(f"  playwright install chromium")
        return False

    return True

def check_cookie(cookie_file: str) -> bool:
    """检查 Cookie 文件"""
    if not Path(cookie_file).exists():
        print(f"{Colors.WARNING}! Cookie 文件不存在：{cookie_file}{Colors.ENDC}")
        return False

    cookie_content = Path(cookie_file).read_text(encoding='utf-8').strip()

    if not cookie_content:
        print(f"{Colors.FAIL}[FAIL] Cookie 文件为空{Colors.ENDC}")
        return False

    if 'dbcl2' not in cookie_content:
        print(f"{Colors.FAIL}[FAIL] Cookie 中缺少 dbcl2{Colors.ENDC}")
        return False

    print(f"{Colors.OKGREEN}[OK] Cookie 文件有效{Colors.ENDC}")
    return True

def get_album_directories(base_path: str, start_letter: str = None):
    """获取专辑目录列表"""
    base = Path(base_path)

    directories = [
        d for d in base.iterdir()
        if d.is_dir() and not d.name.startswith('.') and d.name != 'scripts'
    ]

    # 按字母顺序排序
    directories.sort(key=lambda x: x.name.lower())

    # 过滤起始字母
    if start_letter:
        start_letter = start_letter.upper()
        directories = [
            d for d in directories
            if d.name[0].upper() >= start_letter
        ]

    return directories

def run_automation(cookie_file: str, base_path: str, limit: int = None,
                   headless: bool = False, no_create: bool = True,
                   output: str = None):
    """运行自动化脚本"""

    cmd = [
        sys.executable,
        str(Path(__file__).parent / 'douban_automation.py'),
        '--path', str(base_path),
        '--cookie-file', cookie_file,
    ]

    if headless:
        cmd.append('--headless')

    if no_create:
        cmd.append('--no-create')

    if limit:
        cmd.extend(['--limit', str(limit)])

    if output:
        cmd.extend(['--output', output])

    print(f"\n{Colors.BOLD}执行命令:{Colors.ENDC}")
    print(f"  {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}脚本执行失败：{e}{Colors.ENDC}")
        return False

    return True

def generate_report(results_file: str):
    """生成处理报告"""
    if not Path(results_file).exists():
        return

    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    total = len(results)
    marked = sum(1 for r in results if r['status'] == 'marked')
    created = sum(1 for r in results if r['status'] == 'created')
    not_found = sum(1 for r in results if r['status'] == 'not_found')
    unknown = sum(1 for r in results if r['status'] == 'unknown')

    report_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    report = f"""
# 豆瓣音乐处理报告

**生成时间**: {report_time}

## 摘要

| 项目 | 数量 |
|------|------|
| 总计 | {total} |
| 已标记 | {marked} |
| 已创建 | {created} |
| 未找到 | {not_found} |
| 未知 | {unknown} |

**成功率**: {(marked + created) / total * 100:.1f}% (不含未知)

## 处理详情

### 已标记的专辑 ({marked})

"""

    for r in results:
        if r['status'] == 'marked':
            report += f"- [x] {r['title']} - {r['artist']}\n"
            if r.get('url'):
                report += f"  - {r['url']}\n"

    report += f"\n### 未找到的专辑 ({not_found})\n\n"

    for r in results:
        if r['status'] == 'not_found':
            report += f"- [ ] {r['title']} - {r['artist']}\n"

    report += f"\n### 未知状态的专辑 ({unknown})\n\n"

    for r in results:
        if r['status'] == 'unknown':
            report += f"- [ ] {r['title']} - {r['artist']}\n"

    report_file = Path(results_file).with_suffix('.md')
    report_file.write_text(report, encoding='utf-8')

    print(f"{Colors.OKGREEN}[OK] 报告已保存至：{report_file}{Colors.ENDC}")

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='豆瓣音乐批量处理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --test           测试模式，处理 5 个专辑
  %(prog)s --all            处理所有专辑
  %(prog)s --from A         从字母 A 开头的专辑开始
  %(prog)s --letter B       只处理 B 开头的专辑
  %(prog)s --dry-run        只扫描，不执行
        """
    )

    parser.add_argument('--path', '-p', default='.',
                       help='专辑目录路径 (默认：当前目录)')
    parser.add_argument('--cookie-file', '-c',
                       default=str(Path(__file__).parent / 'douban_cookie.txt'),
                       help='Cookie 文件路径')
    parser.add_argument('--test', action='store_true',
                       help='测试模式：只处理 5 个专辑')
    parser.add_argument('--all', action='store_true',
                       help='处理所有专辑')
    parser.add_argument('--from', dest='from_letter',
                       help='从指定字母开头的专辑开始')
    parser.add_argument('--letter', '-l',
                       help='只处理指定字母开头的专辑')
    parser.add_argument('--dry-run', action='store_true',
                       help='空运行：只扫描目录，不执行操作')
    parser.add_argument('--headless', action='store_true',
                       help='无头模式运行')
    parser.add_argument('--create', action='store_false',
                       help='尝试创建新条目 (默认：不创建)')
    parser.add_argument('--output', '-o',
                       help='结果输出文件')

    args = parser.parse_args()

    print_banner()

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 检查 Cookie
    print(f"\n{Colors.BOLD}检查 Cookie...{Colors.ENDC}")
    if not check_cookie(args.cookie_file):
        print(f"\n{Colors.WARNING}获取 Cookie 的方法:{Colors.ENDC}")
        print(f"1. 在浏览器中打开 {Colors.OKCYAN}scripts/get_douban_cookie.html{Colors.ENDC}")
        print(f"2. 确保已登录豆瓣")
        print("3. 点击 [获取 Cookie] 按钮")
        print(f"4. 复制并保存到 {Colors.OKCYAN}{args.cookie_file}{Colors.ENDC}")
        sys.exit(1)

    # 获取专辑目录
    print(f"\n{Colors.BOLD}扫描专辑目录...{Colors.ENDC}")
    directories = get_album_directories(args.path, args.from_letter)

    if args.letter:
        directories = [
            d for d in directories
            if d.name[0].upper() == args.letter.upper()
        ]

    if args.test:
        directories = directories[:5]

    print(f"找到 {len(directories)} 个专辑目录")

    if args.dry_run:
        print(f"\n{Colors.OKCYAN}空运行模式 - 不执行任何操作{Colors.ENDC}")
        print("\n将要处理的专辑:")
        for d in directories[:20]:  # 只显示前 20 个
            print(f"  - {d.name}")
        if len(directories) > 20:
            print(f"  ... 还有 {len(directories) - 20} 个")
        return

    # 确认
    print(f"\n{Colors.WARNING}[WARN] 即将处理 {len(directories)} 个专辑{Colors.ENDC}")
    print(f"预计时间：约 {len(directories) * 10} 秒 (每个专辑约 10 秒)")

    if not args.test and not args.all:
        response = input(f"\n{Colors.BOLD}是否继续？(y/N): {Colors.ENDC}")
        if response.lower() != 'y':
            print("已取消")
            return

    # 设置输出文件
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'douban_results_{timestamp}.json'

    # 运行自动化
    print(f"\n{Colors.BOLD}开始处理...{Colors.ENDC}")
    start_time = time.time()

    success = run_automation(
        cookie_file=args.cookie_file,
        base_path=args.path,
        limit=5 if args.test else None,
        headless=args.headless,
        no_create=args.create,
        output=args.output
    )

    elapsed = time.time() - start_time

    if success:
        print(f"\n{Colors.OKGREEN}[OK] 处理完成！耗时：{elapsed:.1f} 秒{Colors.ENDC}")
        generate_report(args.output)
    else:
        print(f"\n{Colors.FAIL}[FAIL] 处理失败{Colors.ENDC}")
        sys.exit(1)

if __name__ == '__main__':
    main()
