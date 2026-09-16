from flask import Flask, jsonify
from flask_cors import CORS
import requests
from extractor import search_movies, get_movie_details

app = Flask(__name__)
CORS(app)

MANIFEST = {
    "id": "com.qalib.filmizlehd",
    "version": "1.0.0",
    "name": "HDFilmCehennemi",
    "description": "Film İzle HD reposu əsasında Stremio axın addonu",
    "resources": ["stream"],
    "types": ["movie"],
    "catalogs": [],
    "idPrefixes": ["tt"]
}

@app.route('/')
def home():
    return "Film-İzlə-HD Stremio Addon işləyir! Manifest üçün: /manifest.json"
    
@app.route('/manifest.json')
def manifest():
    return jsonify(MANIFEST)

@app.route('/stream/<string:type>/<string:id>.json')
def stream(type, id):
    if type != 'movie':
        return jsonify({"streams": []})
    
    # 1. Stremio-dan gələn IMDb ID vasitəsilə film adını və ilini öyrənirik
    try:
        meta_res = requests.get(f"https://v3-cinemeta.strem.io/meta/movie/{id}.json", timeout=5).json()
        meta = meta_res.get('meta', {})
        movie_title = meta.get('name')
        movie_year = str(meta.get('year', '')) # Cinemeta-dan ili alırıq (məsələn: "2026")
        
        if not movie_title:
            return jsonify({"streams": []})
    except Exception as e:
        print(f"Cinemeta xətası: {e}")
        return jsonify({"streams": []})

    # 2. extractor.py-dakı search_movies funksiyası ilə filmləri tapırıq
    search_results = search_movies(movie_title)
    if not search_results:
        return jsonify({"streams": []})

    # 3. İL UYĞUNLUĞU: Siyahıdan ilinə uyğun gələn filmi tapırıq
    best_match = None
    if movie_year:
        for item in search_results:
            # Saytdan gələn il ilə Cinemeta-dakı il üst-üstə düşürsə
            if item.get('year') == movie_year:
                best_match = item
                break
    
    # Əgər illə dəqiq uyğunlaşma tapılmasa, ehtiyat olaraq ilk nəticəni götürürük
    if not best_match:
        best_match = search_results[0]

    # 4. Seçilən filmin detallarını və m3u8 linkini çəkirik
    details = get_movie_details(best_match['url'])
    
    if not details or not details.get('streams'):
        return jsonify({"streams": []})

    stremio_streams = []
    for s in details['streams']:
        if s.get('type') == 'hls':
            stremio_streams.append({
                "title": f"HDFilmCehennemi.com | {s.get('source_name', 'Hızlı Sunucu')}",
                "url": s['m3u8_url'],
                "behaviorHints": {
                    "notWebReady": False,
                    "proxyHeaders": {
                        "request": s.get('headers', {})
                    }
                }
            })

    return jsonify({"streams": stremio_streams})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000)
