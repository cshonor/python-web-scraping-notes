"""第7章：远程 CSV + StringIO + DictReader（带离线回退）。"""
from __future__ import annotations

import csv
import sys
from io import StringIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = "https://pythonscraping.com/files/MontyPythonAlbums.csv"
FALLBACK = """Name,Year
Monty Python and the Holy Grail,1975
Monty Python's Life of Brian,1979
Monty Python Live at the Hollywood Bowl,1982
The Meaning of Life,1983
"""


def fetch_csv_text() -> str:
    req = Request(URL, headers={"User-Agent": "Chapter07CsvDemo/1.0 (educational)"})
    try:
        with urlopen(req, timeout=25) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, OSError) as e:
        print("远程获取失败，使用内置示例 CSV:", e, file=sys.stderr)
        return FALLBACK


def main() -> int:
    data_file = StringIO(fetch_csv_text())
    dict_reader = csv.DictReader(data_file)
    if not dict_reader.fieldnames:
        print("无表头", file=sys.stderr)
        return 1
    print("列标题:", dict_reader.fieldnames)
    for row in dict_reader:
        name = row.get("Name", "")
        year = row.get("Year", "")
        print(f"专辑名称: {name}, 发行年份: {year}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
