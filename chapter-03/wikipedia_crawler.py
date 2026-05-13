"""第3章：维基百科随机游走（去重、限速、UA、异常处理）。"""
from __future__ import annotations

import random
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

# 维基媒体 User-Agent 政策：https://meta.wikimedia.org/wiki/User-Agent_policy
# 请将 mailto 改为你可收信的地址。
HEADERS = {
    "User-Agent": (
        "Chapter03WikiCrawler/1.0 (educational notes; "
        "https://github.com/REMitchell/python-scraping; mailto:you@example.com)"
    ),
}

visited_pages: set[str] = set()


def _fetch_bytes(url: str) -> bytes | None:
    """带短暂重试的请求（缓解偶发 SSL 中断等）。"""
    last_err: BaseException | None = None
    for attempt in range(3):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=20) as resp:
                return resp.read()
        except (HTTPError, URLError, OSError) as e:
            last_err = e
            time.sleep(0.4 * (attempt + 1))
    print(f"访问失败: {last_err}")
    return None


def get_wiki_links(article_path: str):
    """
    获取英文维基页面正文区域内的词条链接（/wiki/ 且无冒号）。
    :param article_path: 如 /wiki/Kevin_Bacon
    :return: Tag 列表；整页请求失败时返回 None（与「有页面但无匹配链接」区分）
    """
    url = f"https://en.wikipedia.org{article_path}"
    raw = _fetch_bytes(url)
    if raw is None:
        return None

    try:
        bs = BeautifulSoup(raw, "html.parser")
        content = bs.find("div", {"id": "bodyContent"})
        if not content:
            return []
        return content.find_all("a", href=re.compile(r"^(/wiki/)((?!:).)*$"))
    except AttributeError as e:
        print(f"解析异常: {e}")
        return []


def random_crawl(start_path: str, max_pages: int = 15, sleep_sec: float = 1.5) -> None:
    """
    随机游走：从起始词条路径出发，随机挑选下一词条，最多访问 max_pages 个不同路径。
    """
    current = start_path

    for i in range(max_pages):
        if current in visited_pages:
            print(f"已爬过，停止: {current}")
            break

        print(f"[{i + 1}/{max_pages}] 正在爬取: {current}")
        visited_pages.add(current)

        links = get_wiki_links(current)
        if links is None:
            print("整页请求失败，结束")
            break
        if not links:
            print("页面中无符合条件的词条链接，结束")
            break

        nxt = random.choice(links)
        href = nxt.attrs.get("href")
        if not href:
            print("随机链接缺少 href，结束")
            break

        current = href
        time.sleep(sleep_sec)


if __name__ == "__main__":
    random.seed(int(time.time()))
    random_crawl("/wiki/Kevin_Bacon", max_pages=15, sleep_sec=1.5)
    print(f"\n完成。共记录 {len(visited_pages)} 个不同词条路径。")
