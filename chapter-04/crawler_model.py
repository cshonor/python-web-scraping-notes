"""第4章：Content + Website + Crawler 通用模型（requests + BeautifulSoup）。"""
from __future__ import annotations

import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# 建议改为可联系到你的邮箱或项目页（礼貌抓取）
DEFAULT_UA = "Chapter04CrawlerModel/1.0 (educational; mailto:you@example.com)"


class Content:
    """统一数据模型：各站解析结果映射到同一结构。"""

    def __init__(self, url: str, title: str, body: str) -> None:
        self.url = url
        self.title = title
        self.body = body

    def display(self, body_preview: int = 120) -> None:
        """打印摘要，避免正文过长刷屏。"""
        tail = "…" if len(self.body) > body_preview else ""
        preview = (self.body[:body_preview] + tail) if self.body else ""
        print("=" * 50)
        print(f"URL: {self.url}")
        print(f"标题: {self.title}")
        print(f"正文预览:\n{preview}")
        print("=" * 50 + "\n")

    def save_to_txt(self, directory: str | Path = ".") -> Path:
        """将本条写入 UTF-8 文本文件，文件名由标题派生（已做简单清洗）。"""
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        stem = re.sub(r"[^\w\-.]+", "_", self.title.strip())[:80] or "untitled"
        path = d / f"{stem}.txt"
        text = f"URL: {self.url}\n\n标题: {self.title}\n\n正文:\n{self.body}\n"
        path.write_text(text, encoding="utf-8")
        return path


class Website:
    """网站配置：解析规则与站点元信息（不含抓取结果）。"""

    def __init__(
        self,
        name: str,
        url: str,
        title_selector: str,
        body_selector: str,
    ) -> None:
        self.name = name
        self.url = url
        self.title_selector = title_selector
        self.body_selector = body_selector


class Crawler:
    """通用引擎：请求 + 按 Website 选择器抽取 + 产出 Content。"""

    def __init__(
        self,
        delay_sec: float = 0.5,
        timeout: int = 15,
        user_agent: str = DEFAULT_UA,
    ) -> None:
        self.delay_sec = delay_sec
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers["User-Agent"] = user_agent

    def get_page(self, url: str) -> BeautifulSoup | None:
        last_err: BaseException | None = None
        for attempt in range(3):
            try:
                resp = self._session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                if self.delay_sec > 0:
                    time.sleep(self.delay_sec)
                return BeautifulSoup(resp.text, "html.parser")
            except requests.exceptions.RequestException as e:
                last_err = e
                time.sleep(0.35 * (attempt + 1))
        print(f"请求失败: {last_err}")
        return None

    def safe_get(self, soup: BeautifulSoup | None, selector: str) -> str:
        """选择器安全抽取：无节点或 soup 为空时返回空串，不抛异常。"""
        if not soup:
            return ""
        elements = soup.select(selector)
        if not elements:
            return ""
        return "\n".join(e.get_text(strip=True) for e in elements)

    def parse(self, website: Website, url: str) -> Content | None:
        soup = self.get_page(url)
        if soup is None:
            return None
        title = self.safe_get(soup, website.title_selector)
        body = self.safe_get(soup, website.body_selector)
        if not title or not body:
            print(f"标题或正文为空（请检查选择器）: {website.name} -> {url}")
            return None
        content = Content(url, title, body)
        content.display()
        return content

    def parse_from_soup(self, website: Website, url: str, soup: BeautifulSoup) -> Content | None:
        """不发起网络请求，便于本地 HTML 或单测（与书中「纯解析」思路一致）。"""
        title = self.safe_get(soup, website.title_selector)
        body = self.safe_get(soup, website.body_selector)
        if not title or not body:
            return None
        content = Content(url, title, body)
        content.display()
        return content


if __name__ == "__main__":
    print("开始抓取（含请求间隔 delay_sec）…\n")

    crawler = Crawler(delay_sec=0.5, timeout=15)

    # 离线小页：不依赖外网，验证模型与选择器
    offline_html = """
    <html><body>
      <h1>离线演示标题</h1>
      <div class="article"><p>第一段。</p><p>第二段。</p></div>
    </body></html>
    """
    offline_site = Website(
        name="离线演示",
        url="https://demo.local/news/1",
        title_selector="h1",
        body_selector="div.article p",
    )
    crawler.parse_from_soup(
        offline_site,
        offline_site.url,
        BeautifulSoup(offline_html, "html.parser"),
    )

    # 线上稳定页：example.com
    example = Website(
        name="Example",
        url="https://example.com/",
        title_selector="h1",
        body_selector="p",
    )
    result = crawler.parse(example, "https://example.com/")
    if result:
        out = result.save_to_txt(Path(__file__).resolve().parent)
        print(f"已保存: {out}")
