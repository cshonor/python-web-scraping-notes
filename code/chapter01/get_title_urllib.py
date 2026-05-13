"""第1章：urllib + BeautifulSoup 稳健获取 h1（与书中示例一致）。"""
from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from bs4 import BeautifulSoup


def getTitle(url: str):
    """
    一个稳健的网页标题获取函数
    集成了网络连接异常处理和标签解析异常处理
    """
    try:
        html = urlopen(url, timeout=15)
    except (HTTPError, URLError) as e:
        print(f"网络连接异常: {e}")
        return None

    try:
        bs = BeautifulSoup(html.read(), "html.parser")
        title = bs.body.h1
    except AttributeError as e:
        print(f"标签解析异常: {e}")
        return None

    return title


if __name__ == "__main__":
    target_url = "http://www.pythonscraping.com/pages/page1.html"
    title = getTitle(target_url)
    if title is None:
        print("未能找到标题")
    else:
        print(f"网页标题为: {title}")
