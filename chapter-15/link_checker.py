"""第15章：单页同域链接探测（礼貌限速，仅用于你有权测试的站点）。"""
from __future__ import annotations

import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

START = "https://example.com/"
DELAY = 0.5


def main() -> None:
    session = requests.Session()
    session.headers["User-Agent"] = "LinkCheckerDemo/1.0"
    r = session.get(START, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    origin = urlparse(START).netloc
    links: set[str] = set()
    for a in soup.find_all("a", href=True):
        u = urljoin(START, a["href"])
        if urlparse(u).scheme.startswith("http") and urlparse(u).netloc == origin:
            links.add(u.split("#")[0])
    for u in sorted(links):
        try:
            h = session.head(u, allow_redirects=True, timeout=10)
            print(h.status_code, u)
        except requests.RequestException as e:
            print("ERR", u, e)
        time.sleep(DELAY)


if __name__ == "__main__":
    main()
