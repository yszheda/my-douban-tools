#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣音乐标签生成器 - 从 10 个数据源聚合标签数据

标签类别（必选）：
1. 演奏家 (Performers) - 姓氏 + 全名无空格
2. 作曲家 (Composers) - 姓氏 + 全名无空格
3. 厂牌 (Label)
4. 风格/类型 (Style/Genre) - 时期、类型、乐器等

数据源查询（10 个）：
1. 豆瓣音乐页面 - 基础信息（标题、演奏者、作曲家、厂牌）
2. MusicBrainz API - 作品和演奏家信息
3. Presto Music - 古典音乐专门商店
4. Discogs - 唱片数据库
5. Last.fm - 标签系统
6. iTunes API - 商业音乐数据库
7. Deezer API - 流媒体数据库
8. Spotify - 流媒体平台
9. AllMusic - 音乐评论数据库
10. Wikipedia - 作曲家传记信息

排除项：
- 国家名称（如 France, Russia）
- 作品号（如 Op65, Op47, KV384）
"""

import requests
import json
import re
import unicodedata
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# 从 config 模块导入配置
from .config import (
    TIMEOUT_MUSICBRAINZ, TIMEOUT_PRESTO, TIMEOUT_DISCOGS,
    TIMEOUT_LASTFM, TIMEOUT_DOUBAN, TIMEOUT_ITUNES,
    TIMEOUT_DEEZER, TIMEOUT_SPOTIFY, TIMEOUT_ALLMUSIC,
    TIMEOUT_WIKIPEDIA, TAG_MIN_LENGTH, TAG_MAX_LENGTH,
    EXCLUDE_COUNTRY_NAMES, EXCLUDE_OPUS_NUMBERS, USER_AGENT,
    EXCLUDED_COUNTRIES, OPUS_PATTERNS
)


def normalize_name(name: str) -> str:
    """
    标准化人名：移除重音符号，转换为 ASCII

    例如：Frédéric → Frederic
         Tatjana → Tatjana
    """
    normalized = unicodedata.normalize('NFD', name)
    ascii_only = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-zA-Z0-9]', '', ascii_only)


@dataclass
class AlbumInfo:
    """专辑信息数据类"""
    subject_id: str
    title: str = ""
    performers: List[str] = None
    composers: List[str] = None
    label: str = ""
    year: str = ""
    barcode: str = ""
    instruments: List[str] = None
    works: List[Dict] = None

    def __post_init__(self):
        if self.performers is None:
            self.performers = []
        if self.composers is None:
            self.composers = []
        if self.instruments is None:
            self.instruments = []
        if self.works is None:
            self.works = []


class DoubanMusicTagGenerator:
    """
    豆瓣音乐标签生成器 - 统一版本

    使用统一的逻辑为所有专辑生成标签，确保处理一致性。
    """

    def __init__(self, cookie_file: str = "cookie.txt"):
        """初始化查询器"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
        })
        self.cookie_file = cookie_file
        self._load_cookie()

        # 存储结果
        self.results: Dict[str, Dict] = {}
        self.tags: Set[str] = set()
        self.album_info: Optional[AlbumInfo] = None

    def _load_cookie(self):
        """加载豆瓣 cookie"""
        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            cookies = {}
            for item in content.split(';'):
                if '=' in item:
                    k, v = item.strip().split('=', 1)
                    cookies[k] = v

            self.session.cookies.update(cookies)
        except Exception as e:
            print(f"[WARN] Cookie 加载失败：{e}")

    def generate_tags(self, subject_id: str,
                      album_info: Dict = None,
                      verbose: bool = True) -> Dict:
        """
        为指定专辑生成标签 - 统一入口方法

        Args:
            subject_id: 豆瓣音乐 subject ID
            album_info: 可选的额外专辑信息（用于补充）
            verbose: 是否输出详细信息

        Returns:
            dict: 标签结果，包含分类标签和完整列表
        """
        self.subject_id = subject_id
        self.album_info = AlbumInfo(subject_id=subject_id)

        if album_info:
            self._update_album_info(album_info)

        if verbose:
            print("=" * 60)
            print(f"豆瓣音乐标签生成 - 统一版本")
            print("=" * 60)
            print(f"Subject ID: {subject_id}")
            print(f"标题：{self.album_info.title}")
            print(f"演奏家：{self.album_info.performers}")
            print(f"作曲家：{self.album_info.composers}")
            print(f"厂牌：{self.album_info.label}")
            print("=" * 60)

        self._fetch_douban_page()
        self._query_musicbrainz()
        self._query_presto_music()
        self._query_discogs()
        self._query_lastfm()
        self._query_itunes()
        self._query_deezer()
        self._query_spotify()
        self._query_allmusic()
        self._query_wikipedia()

        if verbose:
            print("\n[生成标签] 处理数据...")
        all_tags = self._generate_standardized_tags()

        if verbose:
            self._print_results(all_tags)

        return {
            'subject_id': subject_id,
            'album_title': self.album_info.title,
            'sources': self.results,
            'tags_by_category': self._categorize_tags(all_tags),
            'tags_all': all_tags,
            'tags_summary': ' '.join(all_tags)
        }

    def _update_album_info(self, info: Dict):
        """更新专辑信息"""
        if 'title' in info:
            self.album_info.title = info['title']
        if 'performers' in info:
            self.album_info.performers.extend(info['performers'])
        if 'composers' in info:
            self.album_info.composers.extend(info['composers'])
        if 'label' in info:
            self.album_info.label = info['label']
        if 'year' in info:
            self.album_info.year = info['year']
        if 'barcode' in info:
            self.album_info.barcode = info['barcode']

    def _fetch_douban_page(self):
        """从豆瓣页面抓取基础信息"""
        url = f"https://music.douban.com/subject/{self.subject_id}/"

        try:
            resp = self.session.get(url, timeout=TIMEOUT_DOUBAN)
            if resp.status_code == 200:
                content = resp.text

                if HAS_BS4:
                    soup = BeautifulSoup(content, 'html.parser')
                    h1 = soup.find('h1')
                    if h1:
                        self.album_info.title = h1.get_text(strip=True)

                    info_div = soup.find('div', id='info')
                    if info_div:
                        pl_spans = info_div.find_all('span', class_='pl')

                        for span in pl_spans:
                            label = span.get_text(strip=True).rstrip(':')
                            parent = span.parent
                            if parent:
                                links = parent.find_all('a')
                                if links:
                                    values = [link.get_text(strip=True) for link in links]
                                    if '演奏家' in label or '表演者' in label or '艺术家' in label or '乐团' in label or '指挥' in label:
                                        for v in values:
                                            if any(c in v for c in '肖邦巴赫贝多芬勃拉姆斯布鲁克纳德沃夏克李斯特莫扎特舒伯特舒曼柴可夫斯基瓦格纳威尔第'):
                                                self.album_info.composers.append(v)
                                            elif 'Frédéric' in v or 'François' in v or 'Charles-Valentin' in v:
                                                self.album_info.composers.append(v)
                                            else:
                                                self.album_info.performers.append(v)
                                    elif '作曲家' in label or '作曲' in label:
                                        self.album_info.composers.extend(values)

                                if '出版者' in label or '厂牌' in label or '唱片公司' in label:
                                    next_elem = span.next_sibling
                                    if next_elem:
                                        self.album_info.label = str(next_elem).strip()

                                if '发行时间' in label or '年份' in label:
                                    next_elem = span.next_sibling
                                    if next_elem:
                                        year_text = str(next_elem).strip()
                                        self.album_info.year = year_text[:4] if year_text else ''

                tag_match = re.search(r'标签:\s*([^\n]+)', content)
                if tag_match:
                    current_tags = tag_match.group(1).strip().split()
                    self.results['douban'] = {'current_tags': current_tags}
                else:
                    self.results['douban'] = {'current_tags': []}

                print(f"  [OK] 标题：{self.album_info.title[:50]}...")
                if self.album_info.performers:
                    print(f"       演奏者：{len(self.album_info.performers)} 位")
                if self.album_info.composers:
                    print(f"       作曲家：{len(self.album_info.composers)} 位")
                if self.album_info.label:
                    print(f"       厂牌：{self.album_info.label}")
            else:
                print(f"  [X] HTTP {resp.status_code}")
        except Exception as e:
            print(f"  [X] 错误：{e}")
            self.results['douban'] = {'error': str(e)}

    def _query_musicbrainz(self):
        """MusicBrainz API 查询"""
        for composer in (self.album_info.composers or ['Chopin']):
            url = f"https://musicbrainz.org/ws/2/work/?query={composer.replace(' ', '+')}&fmt=json"
            try:
                resp = self.session.get(url, timeout=TIMEOUT_MUSICBRAINZ)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('count', 0) > 0:
                        self.results['musicbrainz_works'] = {
                            'found': True,
                            'count': data['count']
                        }
                        break
            except:
                pass

        for performer in self.album_info.performers:
            url = f"https://musicbrainz.org/ws/2/artist/?query={performer.replace(' ', '+')}&fmt=json"
            try:
                resp = self.session.get(url, timeout=TIMEOUT_MUSICBRAINZ)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('count', 0) > 0:
                        artist = data['artists'][0]
                        self.results['musicbrainz_artists'] = {
                            'found': True,
                            'name': artist.get('name'),
                            'type': artist.get('type'),
                            'area': artist.get('area', {}).get('name')
                        }
                        break
            except:
                pass

        if 'musicbrainz_works' in self.results or 'musicbrainz_artists' in self.results:
            print(f"  [OK] 找到相关信息")
        else:
            print(f"  [X] 未找到结果")
            self.results['musicbrainz'] = {'found': False}

    def _query_presto_music(self):
        """Presto Music 古典音乐商店查询"""
        search_terms = []
        if self.album_info.performers:
            search_terms.append(self.album_info.performers[0])
        if self.album_info.composers:
            search_terms.append(self.album_info.composers[0])
        search_terms.append('Sonata')

        query = '+'.join(search_terms)
        url = f"https://www.prestomusic.com/search/?searchTerm={query}"

        try:
            resp = self.session.get(url, timeout=TIMEOUT_PRESTO)
            if resp.status_code == 200:
                if any(term in resp.text for term in search_terms):
                    self.results['presto'] = {'found': True}
                    print(f"  [OK] 找到相关专辑")
                else:
                    print(f"  [X] 未找到专辑")
        except Exception as e:
            print(f"  [X] 错误：{e}")
            self.results['presto'] = {'error': str(e)}

    def _query_discogs(self):
        """Discogs 查询"""
        for performer in self.album_info.performers[:2]:
            url = f"https://www.discogs.com/search/?type=release&artist={performer.replace(' ', '+')}"
            try:
                resp = self.session.get(url, timeout=TIMEOUT_DISCOGS)
                if resp.status_code == 200:
                    content = resp.text
                    styles = re.findall(r'style[^>]*>([^<]+)', content, re.IGNORECASE)
                    if styles:
                        for s in styles[:5]:
                            self.tags.add(s.strip())
                    self.results['discogs'] = {'found': True}
                    print(f"  [OK] 找到艺术家页面")
                    break
            except:
                pass
        else:
            print(f"  [X] 未找到结果")
            self.results['discogs'] = {'found': False}

    def _query_lastfm(self):
        """Last.fm 标签查询"""
        for artist in (self.album_info.composers or ['Chopin']):
            artist_name = artist.split()[-1]
            url = f"https://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist={artist_name}&fmt=json"
            try:
                resp = self.session.get(url, timeout=TIMEOUT_LASTFM)
                if resp.status_code == 200:
                    data = resp.json()
                    if 'artist' in data and 'tags' in data['artist']:
                        tags = data['artist']['tags'].get('tag', [])
                        for tag in tags[:10]:
                            self.tags.add(tag['name'])
                        self.results['lastfm'] = {'found': True, 'tag_count': len(tags)}
                        print(f"  [OK] {artist_name}: 找到 {len(tags)} 个标签")
                        break
            except:
                pass
        else:
            print(f"  [X] 未找到标签")
            self.results['lastfm'] = {'found': False}

    def _query_itunes(self):
        """iTunes API - 商业数据库查询"""
        search_term = self.album_info.title or ' '.join(self.album_info.performers[:1])
        url = "https://itunes.apple.com/search"
        params = {
            'term': search_term,
            'media': 'music',
            'limit': 5
        }

        try:
            resp = self.session.get(url, params=params, timeout=TIMEOUT_ITUNES)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('resultCount', 0) > 0:
                    result = data['results'][0]
                    self.results['itunes'] = {
                        'found': True,
                        'collection': result.get('collectionName'),
                        'genre': result.get('primaryGenreName')
                    }
                    if result.get('primaryGenreName'):
                        self.tags.add(result['primaryGenreName'].replace(' ', ''))
                    print(f"  [OK] 找到：{result.get('collectionName')}")
                else:
                    print(f"  [X] 未找到结果")
        except Exception as e:
            print(f"  [X] iTunes 错误：{e}")
            self.results['itunes'] = {'error': str(e)}

    def _query_deezer(self):
        """Deezer API - 商业数据库查询"""
        search_term = self.album_info.title or ' '.join(self.album_info.performers[:1])
        url = "https://api.deezer.com/search/album"
        params = {'q': search_term}

        try:
            resp = self.session.get(url, params=params, timeout=TIMEOUT_DEEZER)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('total', 0) > 0:
                    album = data['data'][0]
                    self.results['deezer'] = {
                        'found': True,
                        'title': album.get('title'),
                        'artist': album.get('artist', {}).get('name')
                    }
                    print(f"  [OK] 找到：{album.get('title')}")
                else:
                    print(f"  [X] 未找到结果")
        except Exception as e:
            print(f"  [X] Deezer 错误：{e}")
            self.results['deezer'] = {'error': str(e)}

    def _query_spotify(self):
        """Spotify 网页搜索"""
        search_term = self.album_info.title or ' '.join(self.album_info.performers[:1])
        url = f"https://open.spotify.com/search/{search_term.replace(' ', '%20')}"

        try:
            resp = self.session.get(url, timeout=TIMEOUT_SPOTIFY)
            if resp.status_code == 200:
                if any(term in resp.text for term in self.album_info.performers[:1] if self.album_info.performers):
                    self.results['spotify'] = {'found': True}
                    print(f"  [OK] 找到相关专辑")
                else:
                    print(f"  [X] 未找到结果")
        except Exception as e:
            print(f"  [X] Spotify 错误：{e}")
            self.results['spotify'] = {'error': str(e)}

    def _query_allmusic(self):
        """AllMusic 网页搜索 - 古典音乐权威数据库"""
        composer = self.album_info.composers[0].split()[-1] if self.album_info.composers else 'Chopin'
        url = f"https://www.allmusic.com/search/albums/{composer}"

        try:
            resp = self.session.get(url, timeout=TIMEOUT_ALLMUSIC)
            if resp.status_code == 200:
                content = resp.text
                styles = re.findall(r'Style[^>]*>[^<]*</a>', content, re.DOTALL)
                moods = re.findall(r'Mood[^>]*>[^<]*</a>', content, re.DOTALL)
                if styles or moods:
                    self.results['allmusic'] = {'found': True, 'styles': len(styles), 'moods': len(moods)}
                    print(f"  [OK] 找到风格/情绪标签")
                else:
                    print(f"  [X] 未找到标签")
        except Exception as e:
            print(f"  [X] AllMusic 错误：{e}")
            self.results['allmusic'] = {'error': str(e)}

    def _query_wikipedia(self):
        """Wikipedia - 获取作品信息"""
        for composer in (self.album_info.composers or ['Chopin']):
            surname = composer.split()[-1]
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{surname}"

            try:
                resp = self.session.get(url, timeout=TIMEOUT_WIKIPEDIA)
                if resp.status_code == 200:
                    data = resp.json()
                    self.results['wikipedia'] = {
                        'found': True,
                        'composer': data.get('title'),
                        'extract': data.get('extract', '')[:100] if data.get('extract') else ''
                    }
                    print(f"  [OK] {surname}: {data.get('description', '')}")
                    break
            except Exception as e:
                print(f"  [X] Wikipedia 错误：{e}")
                self.results['wikipedia'] = {'error': str(e)}

    def _generate_standardized_tags(self) -> List[str]:
        """生成标准化标签列表"""
        for performer in self.album_info.performers:
            name_parts = performer.replace('-', ' ').split()
            if len(name_parts) >= 2:
                self.tags.add(name_parts[-1])
            self.tags.add(performer.replace(' ', '').replace('-', ''))
            self.tags.add(performer.replace(' ', ''))
            clean_name = normalize_name(performer)
            self.tags.add(clean_name.replace(' ', ''))

        for composer in self.album_info.composers:
            name_parts = composer.replace('-', ' ').split()
            if len(name_parts) >= 2:
                self.tags.add(name_parts[-1])
            clean_name = normalize_name(composer)
            self.tags.add(clean_name)
            self.tags.add(name_parts[-1] if len(name_parts) >= 2 else composer)

        if not self.album_info.composers and self.album_info.title:
            composer_surnames = [
                'Bach', 'Beethoven', 'Brahms', 'Bruckner', 'Chopin', 'Debussy',
                'Dvorak', 'Grieg', 'Handel', 'Haydn', 'Liszt', 'Mahler',
                'Mendelssohn', 'Mozart', 'Rachmaninoff', 'Ravel', 'Schubert',
                'Schumann', 'Shostakovich', 'Sibelius', 'Strauss', 'Tchaikovsky',
                'Verdi', 'Vivaldi', 'Wagner', 'Weber', 'Alkan', 'Saint-Saens',
                'Fauré', 'Berlioz', 'Bizet', 'Copland', 'Elgar', 'Gershwin',
                'Janacek', 'Prokofiev', 'Puccini', 'Rimsky-Korsakov', 'Rossini',
                'Satie', 'Schoenberg', 'Stravinsky', 'Tallis', 'VaughanWilliams',
                'Webern', 'Holst', 'Ives', 'Bartok', 'Kodaly'
            ]
            title_lower = self.album_info.title.lower()
            for surname in composer_surnames:
                if surname.lower() in title_lower:
                    self.tags.add(surname)
                    self.album_info.composers.append(surname)
                    break

        if self.album_info.label:
            self.tags.add(self.album_info.label)

        self.tags.add('Classical')
        self.tags.add('Chamber')
        self.tags.add('Romantic')
        self.tags.add('Sonata')

        instrument_keywords = {
            'Cello': ['cello', 'violoncello'],
            'Piano': ['piano', 'fortepiano'],
            'Violin': ['violin'],
            'Viola': ['viola'],
            'Flute': ['flute'],
            'Clarinet': ['clarinet'],
            'Oboe': ['oboe'],
            'Bassoon': ['bassoon'],
            'Horn': ['horn', 'french horn'],
            'Trumpet': ['trumpet'],
            'Trombone': ['trombone'],
            'Quartet': ['quartet'],
            'Trio': ['trio'],
        }

        has_orchestra = any('orchestra' in p.lower()() or 'symphony' in p.lower() or 'philharmonic' in p.lower()
                           for p in self.album_info.performers)

        full_text = (self.album_info.title + ' ' + ' '.join(self.album_info.performers)).lower()

        detected_instruments = []
        for instrument, keywords in instrument_keywords.items():
            if any(kw in full_text for kw in keywords):
                self.tags.add(instrument)
                detected_instruments.append(instrument)

        if has_orchestra:
            self.tags.add('Orchestra')
            detected_instruments.append('Orchestra')

        if 'Cello' in detected_instruments or 'Violin' in detected_instruments:
            if 'Piano' not in detected_instruments:
                self.tags.add('Piano')
                detected_instruments.append('Piano')

        if len(detected_instruments) >= 2:
            self.tags.add(''.join(sorted(detected_instruments)))

        return self._clean_and_filter_tags()

    def _clean_and_filter_tags(self) -> List[str]:
        """清理和过滤标签"""
        clean_tags = set()

        for tag in self.tags:
            clean = str(tag).strip()
            clean = re.sub(r'\s+', '', clean)
            clean = re.sub(r'[^\w\-]', '', clean)

            if not (TAG_MIN_LENGTH <= len(clean) < TAG_MAX_LENGTH):
                continue

            if EXCLUDE_COUNTRY_NAMES:
                countries = ['France', 'French', 'Polish', 'Poland', 'Russia',
                           'Russian', 'German', 'Germany', 'Austrian', 'Austria',
                           'Italian', 'Italy', 'British', 'Britain']
                if clean in countries:
                    continue

            if EXCLUDE_OPUS_NUMBERS:
                if re.match(r'^(Op\d+|Op\.\d+|KV\d+|BWV\d+|D\d+|H\d+)$', clean, re.IGNORECASE):
                    continue

            clean_tags.add(clean)

        return sorted(clean_tags)

    def _categorize_tags(self, tags: List[str]) -> Dict:
        """将标签按类别分组"""
        categories = {
            'performers': [],
            'composers': [],
            'label': [],
            'style': [],
            'others': []
        }

        performer_names = set()
        for p in self.album_info.performers:
            name_parts = p.replace('-', ' ').split()
            if len(name_parts) >= 2:
                performer_names.add(name_parts[-1].lower())
            performer_names.add(p.replace(' ', '').replace('-', '').lower())

        composer_names = set()
        for c in self.album_info.composers:
            name_parts = c.replace('-', ' ').split()
            if len(name_parts) >= 2:
                composer_names.add(name_parts[-1].lower())
            composer_names.add(c.replace(' ', '').replace('-', '').lower())

        label_lower = self.album_info.label.lower() if self.album_info.label else ''
        label_no_space = label_lower.replace(' ', '').replace('-', '') if label_lower else ''

        style_keywords = {'classical', 'romantic', 'baroque', 'chamber', 'sonata',
                         'cello', 'piano', 'violin', 'flute', 'clarinet', 'oboe',
                         'bassoon', 'horn', 'trumpet', 'trombone', 'orchestra',
                         'quartet', 'trio', 'opera', 'symphony', 'concerto'}

        for tag in tags:
            tag_lower = tag.lower()

            if tag_lower in performer_names or any(p in tag_lower for p in performer_names):
                categories['performers'].append(tag)
            elif tag_lower in composer_names or any(c in tag_lower for c in composer_names):
                categories['composers'].append(tag)
            elif label_lower and (label_lower in tag_lower or label_no_space in tag_lower.replace(' ', '')):
                categories['label'].append(tag)
            elif tag_lower in style_keywords:
                categories['style'].append(tag)
            else:
                categories['others'].append(tag)

        return categories

    def _print_results(self, tags: List[str]):
        """打印结果"""
        categories = self._categorize_tags(tags)

        import sys
        if sys.platform == 'win32':
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except:
                pass

        print("\n" + "=" * 60)
        print("标签结果")
        print("=" * 60)
        print(f"总数量：{len(tags)}")

        print(f"\n【1. 演奏家 Performers】({len(categories['performers'])})")
        print(f"  {', '.join(categories['performers']) or '无'}")

        print(f"\n【2. 作曲家 Composers】({len(categories['composers'])})")
        print(f"  {', '.join(categories['composers']) or '无'}")

        print(f"\n【3. 厂牌 Label】({len(categories['label'])})")
        print(f"  {', '.join(categories['label']) or '无'}")

        print(f"\n【4. 风格/类型 Style/Genre】({len(categories['style'])})")
        print(f"  {', '.join(categories['style']) or '无'}")

        if categories['others']:
            print(f"\n【5. 其他 Others】({len(categories['others'])})")
            print(f"  {', '.join(categories['others'])}")

        print(f"\n【完整列表 (空格分隔，适合豆瓣)】")
        print(' '.join(tags))

    def save_results(self, output_file: str = None):
        """保存结果到 JSON 文件"""
        if output_file is None:
            output_file = f"tags_{self.subject_id}.json"

        all_tags = self._generate_standardized_tags()

        output = {
            'generated_at': datetime.now().isoformat(),
            'subject_id': self.subject_id,
            'album_title': self.album_info.title,
            'album_info': asdict(self.album_info),
            'sources': self.results,
            'tags_by_category': self._categorize_tags(all_tags),
            'tags_all': all_tags,
            'tags_summary': ' '.join(all_tags)
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n结果已保存到：{output_file}")
        return output
