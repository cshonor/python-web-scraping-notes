"""第14章：自定义请求头与 Session。"""
from __future__ import annotations

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; EduBot/1.0; +https://example.com)",
    "Accept-Language": "en-US,en;q=0.9",
}

s = requests.Session()
s.headers.update(HEADERS)
r = s.get("https://example.com", timeout=15)
r.raise_for_status()
print(r.status_code, r.headers.get("Content-Type"))
