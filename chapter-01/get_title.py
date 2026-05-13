"""第1章：安全获取页面 h1 文本（urllib + BeautifulSoup）。"""
from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


def get_h1_text(url: str) -> str | None:
    """
    安全获取网页 h1 标题文本。
    包含：网络异常处理；h1 不存在时返回说明字符串。
    """
    try:
        req = Request(
            url,
            headers={"User-Agent": "Chapter01GetTitle/1.0 (educational)"},
        )
        html = urlopen(req, timeout=15)
    except (HTTPError, URLError, OSError) as e:
        print(f"访问失败：{e}")
        return None

    bs = BeautifulSoup(html.read(), "html.parser")
    h1_tag = bs.find("h1")
    if h1_tag:
        return h1_tag.get_text(strip=True)
    return "页面没有 h1 标签"


if __name__ == "__main__":
    # 部分网络环境对 https 握手不稳定时可改用 http（仅作教学页）
    for demo_url in (
        "https://www.pythonscraping.com/pages/page1.html",
        "http://www.pythonscraping.com/pages/page1.html",
    ):
        title = get_h1_text(demo_url)
        if title is not None:
            print("网页 H1 标题：", title)
            break
    else:
        print("网页 H1 标题：", None)
