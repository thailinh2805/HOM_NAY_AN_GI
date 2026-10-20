"""
Ăn Gì Quanh Làng — website gợi ý quán ăn quanh Bcons Plaza, KTX khu A và KTX khu B (ĐHQG TP.HCM).

Chạy thử trên máy:
    pip install -r requirements.txt
    python app.py
Rồi mở http://localhost:5000

API:
    GET /api/search?q=lẩu&min=30&max=200&near=ktxb&radius=3&cat=Chay&rating=4&sort=goi-y
    GET /api/random?...   (cùng tham số, trả về 1 quán ngẫu nhiên)
    GET /api/places       (toàn bộ dữ liệu)
"""
import json
import math
import os
import random
from pathlib import Path

from flask import Flask, Response, jsonify, request

BASE = Path(__file__).resolve().parent
DATA = json.loads((BASE / "places.json").read_text(encoding="utf-8"))
LANDMARKS = {lm["id"]: lm for lm in DATA["landmarks"]}
PRICE_FLOOR, PRICE_CEIL = 30, 200

app = Flask(__name__)
app.json.ensure_ascii = False


def haversine_km(lat1, lng1, lat2, lng2):
    """Khoảng cách đường chim bay giữa 2 tọa độ, đơn vị km."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def to_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def strip_accents(text):
    """Bỏ dấu tiếng Việt để tìm 'lau bo' vẫn ra 'Lẩu bò'."""
    import unicodedata

    text = (text or "").replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()


def distance_info(place, near, my_lat=None, my_lng=None):
    """Trả về (khoảng cách km, tên điểm mốc) theo lựa chọn 'near'."""
    if near == "me" and my_lat is not None and my_lng is not None:
        return haversine_km(my_lat, my_lng, place["lat"], place["lng"]), "vị trí của bạn"
    if near in LANDMARKS:
        lm = LANDMARKS[near]
        return haversine_km(lm["lat"], lm["lng"], place["lat"], place["lng"]), lm["name"]
    # "all": lấy điểm mốc gần nhất
    best = min(
        ((haversine_km(lm["lat"], lm["lng"], place["lat"], place["lng"]), lm["name"]) for lm in LANDMARKS.values()),
        key=lambda x: x[0],
    )
    return best


def score(place, dist):
    """Điểm 'Đề xuất': rating cao + nhiều đánh giá + gần."""
    return place["rating"] * math.log10(place["reviews"] + 10) - 0.35 * dist


def search(args):
    q = strip_accents(args.get("q", "").strip())
    pmin = max(PRICE_FLOOR, to_float(args.get("min"), PRICE_FLOOR))
    pmax = min(PRICE_CEIL, to_float(args.get("max"), PRICE_CEIL))
    near = args.get("near", "all")
    radius = to_float(args.get("radius"), 3.0)
    cat = args.get("cat", "")
    min_rating = to_float(args.get("rating"), 0)
    sort = args.get("sort", "goi-y")
    my_lat = to_float(args.get("lat"), None)
    my_lng = to_float(args.get("lng"), None)

    results = []
    for p in DATA["places"]:
        if q:
            hay = strip_accents(" ".join([p["name"], p["type"], p["category"], p["address"], p["highlight"]]))
            if not all(word in hay for word in q.split()):
                continue
        # khoảng giá của quán giao với khoảng giá người dùng chọn
        if p["price_max"] < pmin or p["price_min"] > pmax:
            continue
        if cat and p["category"] != cat:
            continue
        if p["rating"] < min_rating:
            continue
        dist, ref = distance_info(p, near, my_lat, my_lng)
        if dist > radius:
            continue
        results.append({**p, "distance_km": round(dist, 2), "distance_from": ref, "_score": score(p, dist)})

    keys = {
        "gan-nhat": lambda r: r["distance_km"],
        "re-nhat": lambda r: (r["price_min"], r["price_max"]),
        "rating": lambda r: (-r["rating"], -r["reviews"]),
        "goi-y": lambda r: -r["_score"],
    }
    results.sort(key=keys.get(sort, keys["goi-y"]))
    for r in results:
        r.pop("_score", None)
    return results


@app.get("/api/search")
def api_search():
    results = search(request.args)
    return jsonify({"count": len(results), "results": results})


@app.get("/api/random")
def api_random():
    results = search(request.args)
    return jsonify({"pick": random.choice(results) if results else None, "count": len(results)})


@app.get("/api/places")
def api_places():
    return jsonify(DATA)


@app.get("/")
def index():
    html = (BASE / "templates" / "index.html").read_text(encoding="utf-8")
    html = html.replace("/*__DATA__*/null", json.dumps(DATA, ensure_ascii=False))
    html = html.replace("/*__API_MODE__*/false", "true")
    page = (
        '<!doctype html><html lang="vi"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        "</head><body>" + html + "</body></html>"
    )
    return Response(page, mimetype="text/html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # host 0.0.0.0 để máy khác trong cùng mạng Wi-Fi truy cập được qua http://<IP-máy-bạn>:5000
    app.run(host="0.0.0.0", port=port, debug=False)
