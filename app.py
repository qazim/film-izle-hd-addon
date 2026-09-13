from flask import Flask, jsonify
from flask_cors import CORS
import requests
from extractor import search_movies, get_movie_details

app = Flask(__name__)
CORS(app)

MANIFEST = {
    "id": "com.qalib.filmizlehd",
    "version": "1.0.0",
    "name": "Film İzle HD",
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
    
    # 1. Stremio-dan gələn IMDb ID (məsələn: tt1234567) vasitəsilə film adını öyrənirik
    try:
        meta_res = requests.get(f"https://v3-cinemeta.strem.io/meta/movie/{id}.json", timeout=5).json()
        movie_title = meta_res.get('meta', {}).get('name')
        if not movie_title:
            return jsonify({"streams": []})
    except Exception as e:
        print(f"Cinemeta xətası: {e}")
        return jsonify({"streams": []})

    # 2. extractor.py-dakı search_movies funksiyası ilə filmi tapırıq
    search_results = search_movies(movie_title)
    if not search_results:
        return jsonify({"streams": []})

    # 3. İlk tapılan filmin detallarını və m3u8 linkini çəkirik
    best_match = search_results[0]
    details = get_movie_details(best_match['url'])
    
    if not details or not details.get('streams'):
        return jsonify({"streams": []})

    stremio_streams = []
    for s in details['streams']:
        if s.get('type') == 'hls':
            stremio_streams.append({
                "title": f"Film İzle HD | {s.get('source_name', 'Hızlı Sunucu')}",
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
