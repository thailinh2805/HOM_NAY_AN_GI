"""Tạo bản web tĩnh (một file HTML, không cần máy chủ) từ templates/index.html + places.json.

    python build_static.py   ->  dist/index.html

File này mở trực tiếp bằng trình duyệt hoặc đưa lên GitHub Pages / Netlify đều được.
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
data = json.loads((BASE / "places.json").read_text(encoding="utf-8"))
html = (BASE / "templates" / "index.html").read_text(encoding="utf-8")
html = html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
page = (
    '<!doctype html><html lang="vi"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
    "</head><body>" + html + "</body></html>"
)
out = BASE / "dist" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(page, encoding="utf-8")
print("Đã tạo", out)
