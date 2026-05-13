"""
第3章：维基百科随机游走（书中逻辑 + HTTPS / UA / 限速 / 上限）。

运行前请将 USER_AGENT 中的邮箱改为你可收信的地址（维基媒体 User-Agent 政策）。
"""
from __future__ import annotations

import random
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

BASE = "https://en.wikipedia.org"
# https://meta.wikimedia.org/wiki/User-Agent_policy
USER_AGENT = "Chapter03Notes/1.0 (educational scraping notes; mailto:you@example.com)"

MAX_PAGES = 12
SLEEP_SEC = 1.0
MAX_TRIES_SAME_PAGE = 80

pages: set[str] = set()


def _fetch(article_path: str) -> bytes | None:
    req = Request(f"{BASE}{article_path}", headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=25) as resp:
            return resp.read()
    except (HTTPError, URLError, OSError) as e:
        print(f"网络错误 {article_path}: {e}")
        return None


def getLinks(article_path: str):
    raw = _fetch(article_path)
    if not raw:
        return []
    try:
        bs = BeautifulSoup(raw, "html.parser")
        body = bs.find("div", {"id": "bodyContent"})
        if not body:
            return []
        return body.find_all("a", href=re.compile(r"^(/wiki/)((?!:).)*$"))
    except AttributeError as e:
        print(f"解析异常: {e}")
        return []


def crawl(article_path: str) -> None:
    if len(pages) >= MAX_PAGES:
        return

    links = getLinks(article_path)
    tries = 0
    while links and len(pages) < MAX_PAGES and tries < MAX_TRIES_SAME_PAGE:
        tries += 1
        time.sleep(SLEEP_SEC)
        a = random.choice(links)
        href = a.attrs.get("href")
        if not href:
            continue
        if href not in pages:
            print(f"发现新词条: {href}")
            pages.add(href)
            crawl(href)


def main() -> int:
    start = "/wiki/Kevin_Bacon"
    pages.add(start)
    print("起始:", start, "| 最多再发现", MAX_PAGES - 1, "个新词条（含礼貌延迟）")
    crawl(start)
    print("完成。已记录词条路径数:", len(pages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
