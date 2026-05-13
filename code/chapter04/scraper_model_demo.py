"""
第4章：Website 配置模型 + 通用 Crawler。

- 书中类名与职责：Website 存选择器，Crawler 负责 getPage/safeGet/parse。
- Content 使用 display()，避免定义 print 方法遮蔽内置 print。
- 附带离线 HTML fixture，保证无网/改版下仍能演示模式。
"""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup


class Content:
    """所有网页的共同基类"""

    def __init__(self, url: str, title: str, body: str) -> None:
        self.url = url
        self.title = title
        self.body = body

    def display(self) -> None:
        print(f"URL: {self.url}")
        print(f"TITLE: {self.title}")
        print(f"BODY:\n{self.body}\n")


class Website:
    """描述网站结构（抓取指令：CSS 选择器）"""

    def __init__(self, name: str, url: str, title_tag: str, body_tag: str) -> None:
        self.name = name
        self.url = url
        self.titleTag = title_tag
        self.bodyTag = body_tag


class Crawler:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Chapter04ModelDemo/1.0 (educational)"

    def getPage(self, url: str) -> BeautifulSoup | None:
        try:
            req = self.session.get(url, timeout=20)
            req.raise_for_status()
        except requests.RequestException:
            return None
        return BeautifulSoup(req.text, "lxml")

    def safeGet(self, page_obj: BeautifulSoup, selector: str) -> str:
        selected = page_obj.select(selector)
        if not selected:
            return ""
        return "\n".join(el.get_text(strip=True) for el in selected)

    def parse_from_soup(self, site: Website, url: str, soup: BeautifulSoup) -> Content | None:
        title = self.safeGet(soup, site.titleTag)
        body = self.safeGet(soup, site.bodyTag)
        if title and body:
            c = Content(url, title, body)
            c.display()
            return c
        return None

    def parse(self, site: Website, url: str) -> Content | None:
        bs = self.getPage(url)
        if bs is None:
            return None
        return self.parse_from_soup(site, url, bs)


def demo_offline() -> None:
    crawler = Crawler()
    html_a = """
    <html><body>
      <h1>Headline A</h1>
      <div class="article-body"><p>First graph.</p><p>Second graph.</p></div>
    </body></html>
    """
    html_b = """
    <html><body>
      <article>
        <h1 class="ttl">B title</h1>
        <div class="content"><p>Body only here.</p></div>
      </article>
    </body></html>
    """
    site_a = Website("DemoNews", "https://demo.news", "h1", "div.article-body p")
    site_b = Website("DemoBlog", "https://demo.blog", "h1.ttl", "article div.content p")
    crawler.parse_from_soup(
        site_a,
        "https://demo.news/story/1",
        BeautifulSoup(html_a, "lxml"),
    )
    crawler.parse_from_soup(
        site_b,
        "https://demo.blog/post/2",
        BeautifulSoup(html_b, "lxml"),
    )


def main() -> None:
    demo_offline()
    print("--- example.com：稳定页面，用于验证线上 parse ---")
    ex = Website("Example", "https://example.com/", "h1", "p")
    Crawler().parse(ex, "https://example.com/")


if __name__ == "__main__":
    main()
