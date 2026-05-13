"""第6章：将维基「文本编辑器比较」页首张 wikitable 导出为 CSV。"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

URL = "https://en.wikipedia.org/wiki/Comparison_of_text_editors"
OUT = Path(__file__).resolve().parent / "editors.csv"
USER_AGENT = (
    "Chapter06Wikitable/1.0 (educational; mailto:you@example.com); "
    "https://meta.wikimedia.org/wiki/User-Agent_policy"
)


def main() -> int:
    try:
        req = Request(URL, headers={"User-Agent": USER_AGENT})
        resp = urlopen(req, timeout=40)
        raw = resp.read()
    except (HTTPError, URLError, OSError) as e:
        print("请求失败:", e, file=sys.stderr)
        return 1

    bs = BeautifulSoup(raw, "lxml")
    tables = bs.find_all("table", {"class": "wikitable"})
    if not tables:
        print("未找到 class=wikitable 的表格", file=sys.stderr)
        return 1
    table = tables[0]
    rows = table.find_all("tr")

    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            csv_row = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
            writer.writerow(csv_row)

    print("CSV 已写入:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
