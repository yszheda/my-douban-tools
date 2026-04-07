#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆瓣音乐批量处理 - 批次结果合并脚本

合并 result_a.json, result_b.json, result_c.json 到 final_summary.json
"""

import json
from pathlib import Path

RESULT_FILES = [
    "result_a.json",
    "result_b.json",
    "result_c.json",
]


def merge_results():
    """合并所有批次结果并生成最终摘要"""
    merged = {
        "processed": [],
        "failed": [],
    }

    for filepath in RESULT_FILES:
        if not Path(filepath).exists():
            print(f"[WARN] 文件不存在：{filepath}")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        processed = data.get("processed", [])
        failed = data.get("failed", [])

        merged["processed"].extend(processed)
        merged["failed"].extend(failed)

        print(f"[OK] 合并 {filepath.split('_')[1].replace('.json', '')}: {len(processed)} 成功，{len(failed)} 失败")

    total = len(merged["processed"]) + len(merged["failed"])
    success_rate = (len(merged["processed"]) / total * 100) if total > 0 else 0

    summary = {
        "total_albums": total,
        "processed": merged["processed"],
        "failed": merged["failed"],
        "success_count": len(merged["processed"]),
        "failed_count": len(merged["failed"]),
        "success_rate": round(success_rate, 2),
    }

    output_file = "final_summary.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print("最终结果:")
    print(f"  总专辑数：{total}")
    print(f"  已处理：{len(merged['processed'])}")
    print(f"  失败：{len(merged['failed'])}")
    print(f"  成功率：{success_rate:.2f}%")
    print(f"  结果已保存到：{output_file}")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    merge_results()
