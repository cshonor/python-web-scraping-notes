"""第5章：维基百科 CrawlSpider（Rule + LinkExtractor + Item）。"""
from __future__ import annotations

from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from wikiSpider.items import ArticleItem

# 正文预览最大字符数（mw-content-text 全量极大，不宜原样入库）
_TEXT_PREVIEW_LIMIT = 8000


class ArticleSpider(CrawlSpider):
    name = "articles"
    allowed_domains = ["en.wikipedia.org"]
    start_urls = ["https://en.wikipedia.org/wiki/Python_(programming_language)"]

    rules = [
        Rule(
            LinkExtractor(
                # 在完整绝对 URL 上做子串匹配：/wiki/ 路径段且无 : # ?
                allow=r"/wiki/[^:#?]+$",
                deny=r"/wiki/(Talk|User|User_talk|Wikipedia|File|Help|Category):",
            ),
            callback="parse_items",
            follow=True,
        ),
    ]

    def parse_start_url(self, response, **kwargs):
        """
        CrawlSpider 对 start_urls 的首次响应默认只跟链、不把正文交给 Rule.callback。
        若需要对起始词条也 yield Item，在此转发到 parse_items。
        """
        yield from self.parse_items(response)

    def parse_items(self, response):
        url = response.url
        # Vector 皮肤标题多在 h1 .mw-page-title-main
        title = (
            (response.css("h1 .mw-page-title-main::text").get() or "").strip()
            or (response.css("h1#firstHeading ::text").get() or "").strip()
            or "".join(response.css("h1 ::text").getall()).strip()
        )

        parts = [
            t.strip()
            for t in response.xpath(
                '//div[@id="mw-content-text"]//text()[not(ancestor::style) and not(ancestor::script)]'
            ).getall()
            if t and t.strip()
        ]
        text = "\n".join(parts)
        if len(text) > _TEXT_PREVIEW_LIMIT:
            text = text[:_TEXT_PREVIEW_LIMIT] + "\n…[truncated]"

        raw = "".join(
            t.strip()
            for t in response.css("li#footer-info-lastmod ::text").getall()
            if t.strip()
        )
        last_updated = raw
        prefix = "This page was last edited on "
        if last_updated.startswith(prefix):
            last_updated = last_updated[len(prefix) :].strip()
        last_updated = (
            last_updated.replace("(UTC).", "").replace("(UTC)", "").strip().rstrip(".")
        )

        self.logger.info("URL: %s", url)
        self.logger.info("Title: %s", title)

        yield ArticleItem(
            url=url,
            title=title,
            text=text,
            last_updated=last_updated,
        )
