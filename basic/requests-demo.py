"""
Minimal requests + BeautifulSoup demo.
Fetches a stable public page (example.com) and prints the title.
"""

from __future__ import annotations

import sys

import requests
from bs4 import BeautifulSoup


def main() -> int:
    url = "https://example.com"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; ScrapingDemo/1.0; +https://example.com)"
        ),
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print("Request failed:", e, file=sys.stderr)
        return 1

    soup = BeautifulSoup(resp.text, "lxml")
    title = soup.title.string.strip() if soup.title and soup.title.string else "(no title)"
    print("Status:", resp.status_code)
    print("Title:", title)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
