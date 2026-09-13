"""
Film İzle HD - Merkezi Yapilandirma
Tum uygulama ayarlari bu dosyada tanimlidir.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Sunucu Ayarlari
WEB_PORT = int(os.environ.get('PORT', 5000))
PLAYER_PORT = 8765

# Cache Ayarlari
CACHE_TTL_SECONDS = 3600
SCRAPE_BATCH_SIZE = 10
SCRAPE_MAX_WORKERS = 5

# Rate Limiting
RATE_LIMIT_PER_MINUTE = 60

# Zaman Asimlari (timeout)
REQUEST_TIMEOUT = 12
SEGMENT_TIMEOUT = 15
SUBTITLE_TIMEOUT = 10

# HLS Ayarlari
HLS_MAX_BUFFER = 60
HLS_MAX_MAX_BUFFER = 180
HLS_BACK_BUFFER = 60

# Tarama Ayarlari (Hizli baslangic icin azaltildi)
INITIAL_SEARCH_QUERIES = [
    '2025', '2026'
]

# CORS Ayarlari
ALLOWED_ORIGINS = ['http://localhost:5000', 'http://localhost:8765']
