"""
Film İzle HD - Stream and Video Extractor
Film arama ve sifrelenmis HLS m3u8 akislarini cozumleme modulu.
Akilli arama (smart_search) ve query expansion destegi ile.
"""

import re
import ast
import json
import urllib.parse
import requests
from bs4 import BeautifulSoup
from common import SCRAPER_HEADERS, logger

HEADERS = SCRAPER_HEADERS
BASE_URL = 'https://hdfilmcehennemini.com'


def search_movies_raw(query: str):
    search_url = f"{BASE_URL}/?s={urllib.parse.quote(query)}"
    try:
        res = requests.get(search_url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            logger.warning("Arama istegi basarisiz: %s -> %d", query, res.status_code)
            return []

        soup = BeautifulSoup(res.text, 'html.parser')
        results = []

        movie_boxes = soup.select('.listmovie, .movie-box')
        for box in movie_boxes:
            title_tag = box.select_one('.film-ismi a, .poster a')
            img_tag = box.select_one('img')
            year_tag = box.select_one('.film-yil')
            rating_tag = box.select_one('.bolum-ust')

            if title_tag:
                href = title_tag.get('href')
                title = title_tag.get_text(strip=True) or (img_tag.get('alt') if img_tag else 'Bilinmeyen Film')
                img = img_tag.get('src') if img_tag else ''
                year = year_tag.get_text(strip=True) if year_tag else ''
                rating = rating_tag.get_text(strip=True) if rating_tag else ''

                if href and not any(r['url'] == href for r in results):
                    results.append({
                        'title': title,
                        'url': href,
                        'img': img,
                        'year': year,
                        'rating': rating
                    })
        return results
    except requests.RequestException as e:
        logger.error("Arama istek hatasi '%s': %s", query, e)
        return []
    except Exception as e:
        logger.error("Arama beklenmeyen hata '%s': %s", query, e)
        return []


def search_movies(query: str):
    q_str = query.strip()
    if not q_str:
        return []

    raw_results = search_movies_raw(q_str)
    if raw_results:
        return raw_results

    q_clean = q_str.lower()
    variations = []

    aliases = {
        'spiderman': ['spider-man', 'spider man', 'spider', 'orumcek', 'orümcek'],
        'spider-man': ['spider man', 'spiderman', 'spider', 'orumcek'],
        'örümcek adam': ['spider', 'spider-man', 'orumcek'],
        'orumcek adam': ['spider', 'spider-man', 'orumcek'],
        'ironman': ['iron man', 'demir adam', 'iron'],
        'demir adam': ['iron man', 'iron'],
        'superman': ['super-man', 'super man', 'super'],
        'batman': ['the batman', 'batman'],
        'hizli ve ofkeli': ['hızlı', 'hizli', 'fast', 'fast and furious'],
        'hızlı ve öfkeli': ['hızlı', 'hizli', 'fast', 'fast and furious'],
        'fast and furious': ['hızlı', 'hizli', 'fast'],
        'star wars': ['star wars', 'starwars', 'yildiz savaslari'],
        'yildiz savaslari': ['star wars'],
        'yıldız savaşları': ['star wars'],
        'yuzuklerin efendisi': ['yuzuk', 'lord of the rings'],
        'yüzüklerin efendisi': ['yuzuk', 'lord of the rings'],
        'lord of the rings': ['yuzuk', 'lord of the rings', 'lotr'],
        'harry potter': ['harry potter', 'harry'],
        'avengers': ['yenilmezler', 'avengers'],
        'yenilmezler': ['avengers'],
        'transformers': ['transformers'],
        'godzilla': ['godzilla'],
        'jurassic park': ['jurassic', 'dinozor'],
        'jurassic world': ['jurassic'],
    }

    if q_clean in aliases:
        variations.extend(aliases[q_clean])

    if 'man' in q_clean and not q_clean.endswith(' man') and not q_clean.startswith('man '):
        variations.append(q_clean.replace('man', ' man'))
        variations.append(q_clean.replace('man', '-man'))

    tr_map = str.maketrans('çğışöüÇĞİŞÖÜ', 'cgisouCGISOU')
    ascii_q = q_str.translate(tr_map)
    if ascii_q != q_str:
        variations.append(ascii_q)

    words = q_str.split()
    if len(words) > 1:
        variations.append(words[0])

    all_results = []
    seen_urls = set()

    for v in variations:
        if v.lower() == q_clean:
            continue
        v_res = search_movies_raw(v)
        for m in v_res:
            if m['url'] not in seen_urls:
                seen_urls.add(m['url'])
                all_results.append(m)
        if len(all_results) >= 12:
            break

    return all_results


def decode_rplayer(html: str):
    m = re.search(r'eval\(function\(h,u,n,t,e,r\).*?\}\((.*?)\)\)', html, re.DOTALL)
    if not m:
        m = re.search(r'}\((.+)\)\s*$', html.strip())
    if not m:
        return None

    try:
        args_str = m.group(1)
        args = ast.literal_eval(f"({args_str})")
        h, u, n, t, e, r = args

        chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"

        def _0xe72c(d, e, f):
            g = list(chars)
            h_chars = g[0:e]
            i_chars = g[0:f]
            j = 0
            for c_idx, b in enumerate(reversed(d)):
                if b in h_chars:
                    j += h_chars.index(b) * (e ** c_idx)
            k = ""
            while j > 0:
                k = i_chars[j % f] + k
                j = (j - (j % f)) // f
            return k or "0"

        res_str = ""
        i = 0
        len_h = len(h)
        sep = n[e]
        while i < len_h:
            s = ""
            while i < len_h and h[i] != sep:
                s += h[i]
                i += 1
            i += 1
            for j_idx, char in enumerate(n):
                s = s.replace(char, str(j_idx))
            if s:
                num = int(_0xe72c(s, e, 10)) - t
                res_str += chr(num)

        return urllib.parse.unquote(res_str)
    except Exception as e:
        logger.error("RPlayer decode hatasi: %s", e)
        return None


def get_movies_from_page(page_url: str):
    try:
        res = requests.get(page_url, headers=HEADERS, timeout=12)
        if res.status_code != 200:
            logger.warning("Sayfa istegi basarisiz: %s -> %d", page_url, res.status_code)
            return [], 0

        soup = BeautifulSoup(res.text, 'html.parser')
        results = []

        movie_boxes = soup.select('.listmovie, .movie-box')
        for box in movie_boxes:
            title_tag = box.select_one('.film-ismi a, .poster a')
            img_tag = box.select_one('img')
            year_tag = box.select_one('.film-yil')
            rating_tag = box.select_one('.bolum-ust')

            if title_tag:
                href = title_tag.get('href')
                title = title_tag.get_text(strip=True) or (img_tag.get('alt') if img_tag else 'Bilinmeyen Film')
                img = img_tag.get('src') if img_tag else ''
                year = year_tag.get_text(strip=True) if year_tag else ''
                rating = rating_tag.get_text(strip=True) if rating_tag else ''

                if href and not any(r['url'] == href for r in results):
                    results.append({
                        'title': title,
                        'url': href,
                        'img': img,
                        'year': year,
                        'rating': rating
                    })

        max_page = 1
        for a_tag in soup.select('a[href]'):
            href_text = a_tag.get('href', '')
            m = re.search(r'/page/(\d+)', href_text)
            if m:
                pnum = int(m.group(1))
                if pnum > max_page:
                    max_page = pnum

        return results, max_page
    except requests.RequestException as e:
        logger.error("Sayfa istek hatasi %s: %s", page_url, e)
        return [], 0
    except Exception as e:
        logger.error("Sayfa parse hatasi %s: %s", page_url, e)
        return [], 0


def get_all_movies(max_pages=0):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    all_movies = []
    seen_urls = set()

    base_page = f"{BASE_URL}/"
    first_results, total_pages = get_movies_from_page(base_page)

    for m in first_results:
        if m['url'] not in seen_urls:
            seen_urls.add(m['url'])
            all_movies.append(m)

    if max_pages <= 0:
        pages_to_scan = total_pages
    else:
        pages_to_scan = min(total_pages, max_pages)

    if pages_to_scan < 2:
        return all_movies

    def fetch_page(page_num):
        page_url = f"{BASE_URL}/page/{page_num}/"
        movies, _ = get_movies_from_page(page_url)
        return page_num, movies

    batch_size = 10
    for batch_start in range(2, pages_to_scan + 1, batch_size):
        batch_end = min(batch_start + batch_size, pages_to_scan + 1)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_page, p): p for p in range(batch_start, batch_end)}
            for future in as_completed(futures):
                try:
                    _, page_movies = future.result()
                    for m in page_movies:
                        if m['url'] not in seen_urls:
                            seen_urls.add(m['url'])
                            all_movies.append(m)
                except Exception as e:
                    logger.warning("Sayfa tarama hatasi: %s", e)

    return all_movies


def get_movie_details(movie_url: str):
    try:
        res = requests.get(movie_url, headers=HEADERS, timeout=12)
        if res.status_code != 200:
            logger.warning("Film detay istegi basarisiz: %s -> %d", movie_url, res.status_code)
            return None

        soup = BeautifulSoup(res.text, 'html.parser')

        title_el = soup.select_one('h1.title-border, h1')
        title = title_el.get_text(strip=True) if title_el else "Film"

        orig_title_el = soup.select_one('.bolum-ismi')
        orig_title = orig_title_el.get_text(strip=True) if orig_title_el else ""

        poster_el = soup.select_one('.film-afis img, .poster img')
        poster = poster_el.get('src') if poster_el else ""

        iframes = soup.select('.video iframe, .video-container iframe, iframe')
        iframe_srcs = [iframe.get('src') for iframe in iframes if iframe.get('src')]

        streams = []
        for src in iframe_srcs:
            if 'yabancidizim.com/rplayer/' in src:
                try:
                    r_res = requests.get(src, headers={'User-Agent': HEADERS['User-Agent'], 'Referer': movie_url}, timeout=10)
                    decoded_js = decode_rplayer(r_res.text)

                    if decoded_js:
                        m_iframe = re.search(r'iframe\.src\s*=\s*["\']([^"\']+)["\']', decoded_js)
                        if m_iframe:
                            ksd_url = m_iframe.group(1)

                            k_res = requests.get(ksd_url, headers={'User-Agent': HEADERS['User-Agent'], 'Referer': 'https://yabancidizim.com/'}, timeout=10)

                            m_video = re.search(r'const videoFile\s*=\s*"([^"]+)"', k_res.text)
                            m_tracks = re.search(r'const tracks\s*=\s*(\[.*?\]);', k_res.text)

                            if m_video:
                                video_file = m_video.group(1).replace(r'\/', '/')
                                tracks = []
                                if m_tracks:
                                    try:
                                        tracks = json.loads(m_tracks.group(1).replace(r'\/', '/'))
                                    except json.JSONDecodeError as e:
                                        logger.warning("Altyazi JSON parse hatasi: %s", e)

                                streams.append({
                                    'type': 'hls',
                                    'source_name': 'Film İzle HD Hızlı Sunucu',
                                    'm3u8_url': video_file,
                                    'tracks': tracks,
                                    'headers': {
                                        'Referer': 'https://ksdpictures.site/',
                                        'Origin': 'https://ksdpictures.site',
                                        'User-Agent': HEADERS['User-Agent']
                                    }
                                })
                except requests.RequestException as e:
                    logger.error("RPlayer/KSD istek hatasi %s: %s", src[:80], e)
            else:
                streams.append({
                    'type': 'iframe',
                    'source_name': 'Harici Oynatici',
                    'iframe_url': src
                })

        return {
            'title': title,
            'orig_title': orig_title,
            'poster': poster,
            'url': movie_url,
            'streams': streams
        }
    except requests.RequestException as e:
        logger.error("Film detay istek hatasi %s: %s", movie_url, e)
        return None
    except Exception as e:
        logger.error("Film detay beklenmeyen hata %s: %s", movie_url, e)
        return None
