"""第10章：Session + POST 示例（httpbin）。"""
from __future__ import annotations

import requests

s = requests.Session()
url = "https://httpbin.org/post"
r = s.post(url, data={"user": "demo", "token": "abc"}, timeout=20)
r.raise_for_status()
data = r.json()
print("form keys in json:", sorted(data.get("form", {}).keys()))
