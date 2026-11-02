"""第2章：page3 综合解析（属性、导航树、正则、lambda）。"""
from __future__ import annotations

import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

URLS = (
    "https://www.pythonscraping.com/pages/page3.html",
    "http://www.pythonscraping.com/pages/page3.html",
)

# 书中「红/绿人物名」的示例页是 warandpeace.html，不是 page3.html。
# 早期版本在 page3.html 上找 span.green，必然为空（该页没有这个 class）。
WAR_URLS = (
    "https://www.pythonscraping.com/pages/warandpeace.html",
    "http://www.pythonscraping.com/pages/warandpeace.html",
)


def get_soup(url: str) -> BeautifulSoup | None:
    """安全获取 BeautifulSoup 对象。"""
    try:
        req = Request(
            url,
            headers={"User-Agent": "Chapter02ComplexParse/1.0 (educational)"},
        )
        html = urlopen(req, timeout=20)
    except (HTTPError, URLError, OSError) as e:
        print(f"访问失败：{e}")
        return None
    return BeautifulSoup(html.read(), "html.parser")


def first_soup(urls: tuple[str, ...]) -> BeautifulSoup | None:
    """按顺序尝试多个 URL，返回第一个拿到的 soup。"""
    for url in urls:
        soup = get_soup(url)
        if soup is not None:
            return soup
    return None


def main() -> int:
    bs = first_soup(URLS)
    if bs is None:
        return 1

    print("===== 1. 所有绿色人物名称（warandpeace.html） =====")
    war = first_soup(WAR_URLS)
    if war is None:
        print("(warandpeace.html 访问失败，跳过)")
    else:
        names = war.find_all("span", class_="green")
        if not names:
            print("(未找到 span.green，页面结构可能已变)")
        for name in names:
            print(name.get_text(strip=True))

    print("\n===== 2. 产品表格数据 =====")
    table = bs.find("table", id="giftList")
    if table and table.tr:
        for sibling in table.tr.next_siblings:
            if getattr(sibling, "name", None):
                print(sibling.get_text(strip=True))
    else:
        print("(未找到 giftList 表格或其首行)")

    print("\n===== 3. 图片路径（正则） =====")
    for img in bs.find_all("img", {"src": re.compile(r"\.\.\/img\/gifts\/img.*\.jpg")}):
        print(img["src"])

    print("\n===== 4. 恰好含 2 个属性的标签（前 10 个） =====")
    tags = bs.find_all(lambda tag: len(tag.attrs) == 2)
    for t in tags[:10]:
        print(t)
    print(f"... 共 {len(tags)} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
