from flask import Flask, jsonify
from flask_cors import CORS
import requests
from extractor import search_movies, get_movie_details

app = Flask(__name__)
CORS(app)

MANIFEST = {
    "id": "com.qalib.filmizlehd",
    "version": "1.0.0",
    "name": "HD_Turk",
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
    best_match = []
    for item in search_results:
        # Saytdan gələn il ilə Cinemeta-dakı il üst-üstə düşürsə
        if item.get('title'):
            best_match.append(item)
    #print(best_match)
    
    # Əgər illə dəqiq uyğunlaşma tapılmasa, ehtiyat olaraq ilk nəticəni götürürük
    if not best_match:
        best_match = search_results[0]

    # 4. Seçilən filmin detallarını və m3u8 linkini çəkirik
    #details = get_movie_details(best_match['url'])
    details = []
    stremio_streams = []
    for n, title in enumerate(best_match[:5]):
        details.append(get_movie_details(title['url']))
        print(f"{n} {title['title']}")
        
    # details = [{'title': '...', 'streams': [...]}]
    for movie in details:
        # Hər bir filmin daxilindəki 'streams' siyahısını götürürük
        movie_streams = movie.get('streams', [])
        
        # 'streams' siyahısının daxilindəki hər bir axını (stream) yoxlayırıq
        for s in movie_streams:
            if s.get('type') == 'hls':
                #print("\nhls tapıldı!\n")
                stremio_streams.append({
                    "title": f"{s.get('source_name', 'Hızlı Sunucu')}",
                    "url": s.get('m3u8_url'),
                    "behaviorHints": {
                        "notWebReady": False,
                        "proxyHeaders": {
                            "request": s.get('headers', {})
                        }
                    }
                })
                #print(stremio_streams)

    return jsonify({"streams": stremio_streams})



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000)
