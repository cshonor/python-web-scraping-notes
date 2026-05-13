"""第16章：线程池并发请求（示例 URL，注意全局限速）。"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

URLS = [
    "https://example.com",
    "https://www.iana.org/domains/reserved",
]


def fetch(url: str) -> tuple[str, int]:
    r = requests.get(url, timeout=20)
    return url, r.status_code


def main() -> None:
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fetch, u): u for u in URLS}
        for fut in as_completed(futures):
            url, code = fut.result()
            print(url, code)


if __name__ == "__main__":
    main()
