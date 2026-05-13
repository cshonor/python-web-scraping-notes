"""第3章：极简同域链接收集（示例页）。"""
from __future__ import annotations

import time
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

START = "https://example.com/"
MAX_PAGES = 5
DELAY_SEC = 0.5


def same_domain(base: str, url: str) -> bool:
    return urlparse(base).netloc == urlparse(url).netloc


def main() -> None:
    session = requests.Session()
    session.headers.update(
        {"User-Agent": "Chapter03Demo/1.0 (educational; +https://example.com)"}
    )
    seen: set[str] = set()
    q: deque[str] = deque([START])

    while q and len(seen) < MAX_PAGES:
        url = q.popleft()
        if url in seen:
            continue
        try:
            r = session.get(url, timeout=15)
            r.raise_for_status()
        except requests.RequestException as e:
            print("skip", url, e)
            continue
        seen.add(url)
        print("OK", url, "len", len(r.text))
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.find_all("a", href=True):
            abs_url = urljoin(url, a["href"])
            if abs_url not in seen and same_domain(START, abs_url):
                q.append(abs_url.split("#")[0])
        time.sleep(DELAY_SEC)


if __name__ == "__main__":
    main()
