#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣音乐工具 - 统一配置模块

提供全局配置管理，支持从 settings.json 加载配置。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 配置文件路径
SETTINGS_FILE = PROJECT_ROOT / "config" / "settings.json"


class Config:
    """配置管理器"""

    def __init__(self, settings_file: Optional[Path] = None):
        self.settings_file = settings_file or SETTINGS_FILE
        self._settings: Dict[str, Any] = {}
        self._load_settings()

    def _load_settings(self):
        """从 settings.json 加载配置"""
        if self.settings_file.exists():
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                self._settings = json.load(f)
        else:
            self._settings = self._get_defaults()

    def _get_defaults(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "project": {
                "name": "my-douban-tools",
                "version": "1.0.0"
            },
            "tag_limits": {
                "max_tags_per_album": 10,
                "tag_min_length": 2,
                "tag_max_length": 50
            },
            "delays": {
                "batch": {"between_albums": 5.0},
                "api": {"between_requests": 1.5},
                "browser": {
                    "navigate": 2.0,
                    "click": 1.0,
                    "fill": 0.5,
                    "save": 1.5
                }
            },
            "timeouts": {
                "musicbrainz": 10,
                "discogs": 15,
                "deezer": 10,
                "itunes": 10,
                "douban": 10
            }
        }

    def get(self, path: str, default: Any = None) -> Any:
        """
        通过路径获取配置值

        Args:
            path: 点分隔的配置路径，如 "delays.batch.between_albums"
            default: 默认值（如果配置不存在）

        Returns:
            配置值
        """
        keys = path.split(".")
        value = self._settings
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    @property
    def max_tags_per_album(self) -> int:
        return self.get("tag_limits.max_tags_per_album", 10)

    @property
    def delay_between_albums(self) -> float:
        return self.get("delays.batch.between_albums", 5.0)

    @property
    def cookie_file(self) -> Path:
        return PROJECT_ROOT / self.get("files.cookie", "cookie.txt")

    @property
    def album_list_file(self) -> Path:
        return PROJECT_ROOT / self.get("files.album_list", "album_list_full.json")


# 全局配置实例
config = Config()


# ========== 向后兼容的常量定义 ==========
# 这些常量保持与旧代码的兼容性

# 标签限制
MAX_TAGS_PER_ALBUM = config.max_tags_per_album
TAG_MIN_LENGTH = 2
TAG_MAX_LENGTH = 50

# 延迟设置（秒）
DELAY_BETWEEN_ALBUMS = config.delay_between_albums
API_DELAY_BETWEEN_TAGS = config.get("delays.api.between_requests", 1.5)
BROWSER_DELAY_NAVIGATE = config.get("delays.browser.navigate", 2.0)
BROWSER_DELAY_CLICK = config.get("delays.browser.click", 1.0)
BROWSER_DELAY_FILL = config.get("delays.browser.fill", 0.5)
BROWSER_DELAY_SAVE = config.get("delays.browser.save", 1.5)

# 超时设置（秒）
TIMEOUT_MUSICBRAINZ = config.get("timeouts.musicbrainz", 10)
TIMEOUT_DISCOGS = config.get("timeouts.discogs", 15)
TIMEOUT_DEEZER = config.get("timeouts.deezer", 10)
TIMEOUT_ITUNES = config.get("timeouts.itunes", 10)
TIMEOUT_DOUBAN = config.get("timeouts.douban", 10)

# 文件路径
COOKIE_FILE = str(config.cookie_file)
ALBUM_LIST_FILE = str(config.album_list_file)
