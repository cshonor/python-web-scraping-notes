"""第12章：调用公开 JSON API。"""
from __future__ import annotations

import requests

BASE = "https://jsonplaceholder.typicode.com"


def main() -> None:
    r = requests.get(f"{BASE}/posts", params={"_limit": 5}, timeout=20)
    r.raise_for_status()
    posts = r.json()
    for p in posts:
        print(p["id"], p["title"][:50] + ("..." if len(p["title"]) > 50 else ""))


if __name__ == "__main__":
    main()
