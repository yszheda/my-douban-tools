"""配置常量

豆瓣音乐标签自动生成工具的配置项。
"""

# ========== 数据源超时设置（秒） ==========
TIMEOUT_MUSICBRAINZ = 10
TIMEOUT_PRESTO = 15
TIMEOUT_DISCOGS = 15
TIMEOUT_LASTFM = 10
TIMEOUT_DOUBAN = 10
TIMEOUT_ITUNES = 10
TIMEOUT_DEEZER = 10
TIMEOUT_SPOTIFY = 10
TIMEOUT_ALLMUSIC = 15
TIMEOUT_WIKIPEDIA = 10

# ========== 标签限制 ==========
TAG_MIN_LENGTH = 2
TAG_MAX_LENGTH = 50
TAGS_PER_ALBUM_LIMIT = 10  # 豆瓣每专辑最多 10 个标签

# ========== 排除项 ==========
EXCLUDE_COUNTRY_NAMES = True
EXCLUDE_OPUS_NUMBERS = True

# 排除的国家名称集合
EXCLUDED_COUNTRIES = {
    "France", "Germany", "Italy", "Spain", "Portugal", "Netherlands",
    "Russia", "Poland", "Czech", "Austria", "Hungary", "Romania",
    "Japan", "China", "Korea", "USA", "UK", "Britain", "English",
    "Switzerland", "Belgium", "Sweden", "Norway", "Denmark", "Finland",
}

# 排除的作品号模式
OPUS_PATTERNS = ["Op", "Op.", "KV", "BWV", "No", "Nr", "D", "L", "S", "G"]

# ========== 用户代理 ==========
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ========== 浏览器模拟版延迟（秒） ==========
BROWSER_DELAY_NAVIGATE = 2.0
BROWSER_DELAY_CLICK = 1.0
BROWSER_DELAY_FILL = 0.5
BROWSER_DELAY_SAVE = 1.5

# ========== API 版延迟（秒） ==========
API_DELAY_BETWEEN_TAGS = 1.5

# ========== 文件路径 ==========
DEFAULT_COOKIE_FILE = "cookie.txt"
DEFAULT_OUTPUT_DIR = "."
