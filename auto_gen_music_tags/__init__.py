"""豆瓣音乐标签自动生成工具

自动化为豆瓣音乐专辑添加标准化标签的工具包。
支持 10 个数据源查询，包含 API 版和浏览器模拟版两种添加方式。
"""

__version__ = "1.0.0"
__author__ = "Galois"
__email__ = ""

from .tag_generator import DoubanMusicTagGenerator, normalize_name, AlbumInfo
from .browser_adder import DoubanBrowserTagAdder
from .api_adder import DoubanApiTagAdder
from .collector import DoubanCollector, AlbumEntry
from .progress import ProgressManager, initialize_progress, load_progress
from .batch_processor import BatchProcessor

__all__ = [
    "DoubanMusicTagGenerator",
    "normalize_name",
    "AlbumInfo",
    "DoubanBrowserTagAdder",
    "DoubanApiTagAdder",
    "DoubanCollector",
    "AlbumEntry",
    "ProgressManager",
    "initialize_progress",
    "load_progress",
    "BatchProcessor",
]
