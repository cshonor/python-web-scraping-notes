"""第2章：page3 综合示例（属性、导航树、正则、lambda）。"""
from __future__ import annotations

import re
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from bs4 import BeautifulSoup

URL = "http://www.pythonscraping.com/pages/page3.html"


def main() -> int:
    try:
        resp = urlopen(URL, timeout=20)
        raw = resp.read()
    except (HTTPError, URLError) as e:
        print("网络错误:", e)
        return 1

    bs = BeautifulSoup(raw, "html.parser")

    nameList = bs.find_all("span", {"class": "green"})
    for name in nameList:
        print(f"人物名称: {name.get_text()}")

    print("\n产品列表：")
    table = bs.find("table", {"id": "giftList"})
    if table and table.tr:
        for sibling in table.tr.next_siblings:
            if getattr(sibling, "name", None) is not None:
                print(sibling.get_text().strip())
    else:
        print("(未找到 giftList 表格)")

    images = bs.find_all("img", {"src": re.compile(r"\.\.\/img\/gifts\/img.*\.jpg")})
    for image in images:
        print(f"找到图片: {image['src']}")

    tags = bs.find_all(lambda tag: len(tag.attrs) == 2)
    print(f"\n具有2个属性的标签数量: {len(tags)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
