#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
进度管理模块

管理批量处理的进度状态，支持断点续跑。
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict, field

from .collector import AlbumEntry


@dataclass
class ProcessingStats:
    """处理统计信息"""
    total: int = 0
    processed: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    started_at: str = ""
    completed_at: str = ""
    last_updated: str = ""

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now().isoformat()
        self.last_updated = datetime.now().isoformat()


class ProgressManager:
    """进度管理器"""

    def __init__(self, progress_file: str = "progress.json"):
        self.progress_file = progress_file
        self.collections: Dict[str, List[AlbumEntry]] = {}
        self.stats: Dict[str, ProcessingStats] = {}
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }

    def initialize(self, collections: Dict[str, List[AlbumEntry]]):
        """初始化进度管理器"""
        self.collections = collections
        for collection_type, entries in collections.items():
            self.stats[collection_type] = ProcessingStats(
                total=len(entries),
                processed=0,
                success=0,
                failed=0,
                skipped=0
            )

    def load(self) -> bool:
        """从文件加载进度"""
        if not os.path.exists(self.progress_file):
            return False

        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.metadata = data.get('metadata', {})
            self.collections = {}
            self.stats = {}

            for collection_type in ['collect', 'do', 'wish']:
                if collection_type in data.get('collections', {}):
                    entries = []
                    for entry_data in data['collections'][collection_type]:
                        entry = AlbumEntry(**entry_data)
                        entries.append(entry)
                    self.collections[collection_type] = entries

                if collection_type in data.get('stats', {}):
                    stats_data = data['stats'][collection_type]
                    self.stats[collection_type] = ProcessingStats(**stats_data)

            print(f"[INFO] 进度已加载：{self.progress_file}")
            return True

        except Exception as e:
            print(f"[ERROR] 加载进度失败：{e}")
            return False

    def save(self):
        """保存进度到文件"""
        self.metadata['updated_at'] = datetime.now().isoformat()

        output = {
            'metadata': self.metadata,
            'collections': {},
            'stats': {}
        }

        for collection_type, entries in self.collections.items():
            output['collections'][collection_type] = [asdict(entry) for entry in entries]

        for collection_type, stats in self.stats.items():
            output['stats'][collection_type] = asdict(stats)

        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    def mark_success(self, collection_type: str, subject_id: str, tags: List[str]):
        """标记条目处理成功"""
        if collection_type not in self.collections:
            return

        for entry in self.collections[collection_type]:
            if entry.subject_id == subject_id:
                entry.status = "done"
                entry.tags = tags
                entry.updated_at = datetime.now().isoformat()
                break

        # 更新统计
        if collection_type in self.stats:
            self.stats[collection_type].processed += 1
            self.stats[collection_type].success += 1
            self.stats[collection_type].last_updated = datetime.now().isoformat()

        self.save()

    def mark_failed(self, collection_type: str, subject_id: str, error: str = ""):
        """标记条目处理失败"""
        if collection_type not in self.collections:
            return

        for entry in self.collections[collection_type]:
            if entry.subject_id == subject_id:
                entry.status = "failed"
                entry.updated_at = datetime.now().isoformat()
                break

        # 更新统计
        if collection_type in self.stats:
            self.stats[collection_type].processed += 1
            self.stats[collection_type].failed += 1
            self.stats[collection_type].last_updated = datetime.now().isoformat()

        self.save()

    def get_pending_entries(self, collection_type: str) -> List[AlbumEntry]:
        """获取待处理的条目"""
        if collection_type not in self.collections:
            return []

        return [
            entry for entry in self.collections[collection_type]
            if entry.status == "pending"
        ]

    def get_next_pending(self, collection_type: str) -> Optional[AlbumEntry]:
        """获取下一个待处理的条目"""
        pending = self.get_pending_entries(collection_type)
        return pending[0] if pending else None

    def has_pending(self, collection_type: str) -> bool:
        """检查是否还有待处理的条目"""
        return len(self.get_pending_entries(collection_type)) > 0

    def has_any_pending(self) -> bool:
        """检查是否还有任何待处理的条目"""
        for collection_type in self.collections:
            if self.has_pending(collection_type):
                return True
        return False

    def print_progress(self):
        """打印当前进度"""
        print("\n" + "=" * 60)
        print("处理进度")
        print("=" * 60)

        for collection_type in ['collect', 'do', 'wish']:
            if collection_type in self.stats:
                stats = self.stats[collection_type]
                pending = stats.total - stats.processed
                print(f"\n{collection_type}:")
                print(f"  总计：{stats.total}")
                print(f"  已处理：{stats.processed} (成功：{stats.success}, 失败：{stats.failed})")
                print(f"  待处理：{pending}")

        print("\n" + "=" * 60)

    def get_summary(self) -> Dict:
        """获取处理摘要"""
        total = sum(s.total for s in self.stats.values())
        processed = sum(s.processed for s in self.stats.values())
        success = sum(s.success for s in self.stats.values())
        failed = sum(s.failed for s in self.stats.values())

        return {
            'total': total,
            'processed': processed,
            'success': success,
            'failed': failed,
            'progress_percent': (processed / total * 100) if total > 0 else 0
        }


def initialize_progress(collections: Dict[str, List[AlbumEntry]], progress_file: str = "progress.json") -> ProgressManager:
    """初始化进度管理器"""
    manager = ProgressManager(progress_file)
    manager.initialize(collections)
    manager.save()
    return manager


def load_progress(progress_file: str = "progress.json") -> Optional[ProgressManager]:
    """加载进度管理器"""
    manager = ProgressManager(progress_file)
    if manager.load():
        return manager
    return None
