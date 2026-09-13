"""
Film İzle HD - Ortak Modul
Paylasilan sabitler, yardimcilar, proxy, guvenlik ve logging.
"""

import os
import re
import time
import logging
import html
import threading
import urllib.parse
from collections import defaultdict

from config import BASE_DIR, TEMPLATES_DIR, ALLOWED_ORIGINS

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('filmizlehd')

# --- Shared Headers ---
PROXY_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://ksdpictures.site/',
    'Origin': 'https://ksdpictures.site'
}

SCRAPER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://hdfilmcehennemini.com/'
}


# --- Template Loader ---
def load_template(filename):
    """Templates dizininden HTML dosyasini yukler."""
    path = os.path.join(TEMPLATES_DIR, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error("Template bulunamadi: %s", path)
        return ""


# --- M3U8 Proxy Rewrite ---
def rewrite_m3u8(content, base_url, server_origin):
    """M3U8 playlist icerigini yerel proxy URL'lerine donusturur."""
    lines = content.splitlines()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            new_lines.append(line)
            continue

        if stripped.startswith('#'):
            def replace_uri(match):
                raw_uri = match.group(1).strip()
                abs_uri = urllib.parse.urljoin(base_url, raw_uri)
                proxied = f"{server_origin}/hls/playlist.m3u8?url={urllib.parse.quote(abs_uri)}"
                return f'URI="{proxied}"'

            line_mod = re.sub(r'URI="([^"]+)"', replace_uri, line)
            new_lines.append(line_mod)
        else:
            abs_url = urllib.parse.urljoin(base_url, stripped)
            segment_exts = ('.woff', '.woff2', '.ttf', '.css', '.js', '.txt', '.ts', '.m4s', '.mp4')
            is_segment = any(ext in abs_url.lower() for ext in segment_exts) or \
                         ('/strm/' in abs_url and '/fx/strm/' not in abs_url)
            if is_segment:
                proxied = f"{server_origin}/hls/segment?url={urllib.parse.quote(abs_url)}"
            else:
                proxied = f"{server_origin}/hls/playlist.m3u8?url={urllib.parse.quote(abs_url)}"
            new_lines.append(proxied)

    return '\n'.join(new_lines)


# --- Input Sanitization (XSS Korumesi) ---
def sanitize_input(text):
    """Kullanici girisini temizler, XSS vektorlerini temizler."""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    text = html.escape(text)
    text = re.sub(r'[<>"\';]', '', text)
    return text[:200]


def sanitize_url(url):
    """URL parametresini dogrular - sadece http/https izin verir."""
    if not isinstance(url, str):
        return ""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return ""
    return url


def is_origin_allowed(origin):
    """Verilen origin izinli mi kontrol eder."""
    if not origin:
        return False
    return origin in ALLOWED_ORIGINS


def get_cors_headers(origin=None):
    """CORS header'larini dondurur - yalnizca izinli origin'ler icin."""
    headers = {}
    if origin and is_origin_allowed(origin):
        headers['Access-Control-Allow-Origin'] = origin
    elif not origin:
        headers['Access-Control-Allow-Origin'] = '*'
    return headers


# --- Rate Limiter ---
class RateLimiter:
    """Basit token bucket rate limiter."""

    def __init__(self, max_per_minute=30):
        self._max = max_per_minute
        self._requests = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key='default'):
        now = time.time()
        with self._lock:
            self._requests[key] = [t for t in self._requests[key] if now - t < 60]
            if len(self._requests[key]) >= self._max:
                return False
            self._requests[key].append(now)
            return True


# --- Thread-Safe Cache ---
class ThreadSafeCache:
    """Thread-guvenli, zaman asimli cache."""

    def __init__(self, ttl_seconds=3600):
        self._data = None
        self._ttl = ttl_seconds
        self._last_update = 0
        self._lock = threading.Lock()
        self._scraping = False

    @property
    def data(self):
        with self._lock:
            return self._data if self._data else []

    @data.setter
    def data(self, value):
        with self._lock:
            self._data = value
            self._last_update = time.time()

    @property
    def is_valid(self):
        with self._lock:
            return bool(self._data) and (time.time() - self._last_update < self._ttl)

    @property
    def scraping(self):
        with self._lock:
            return self._scraping

    @scraping.setter
    def scraping(self, value):
        with self._lock:
            self._scraping = value

    def get_shuffled(self):
        """Cache gecerliyse karistirilmis listeyi dondurur."""
        import random
        if not self.is_valid:
            return []
        with self._lock:
            if not self._data:
                return []
            shuffled = list(self._data)
            random.shuffle(shuffled)
            return shuffled
