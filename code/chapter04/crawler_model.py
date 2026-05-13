"""第4章：抓取 / 解析 / 运行 分离。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


@dataclass
class PageRecord:
    url: str
    title: str
    fetched_at: str


def fetch(url: str, session: requests.Session) -> str | None:
    try:
        r = session.get(url, timeout=15)
        r.raise_for_status()
        return r.text
    except requests.RequestException:
        return None


def parse(url: str, html: str) -> PageRecord | None:
    soup = BeautifulSoup(html, "lxml")
    t = soup.title.string.strip() if soup.title and soup.title.string else ""
    if not t:
        return None
    return PageRecord(
        url=url,
        title=t,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )


def run(url: str) -> None:
    session = requests.Session()
    html = fetch(url, session)
    if not html:
        print("fetch failed")
        return
    rec = parse(url, html)
    print(rec)


if __name__ == "__main__":
    run("https://example.com/")
