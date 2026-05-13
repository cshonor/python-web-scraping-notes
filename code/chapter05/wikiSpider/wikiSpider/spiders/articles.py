"""第5章：维基百科 CrawlSpider 示例（Rule + LinkExtractor）。"""
from __future__ import annotations

from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from wikiSpider.items import ArticleItem


class ArticleSpider(CrawlSpider):
    name = "articles"
    allowed_domains = ["en.wikipedia.org"]
    start_urls = ["https://en.wikipedia.org/wiki/Python_(programming_language)"]

    rules = [
        Rule(
            LinkExtractor(allow=r"^(/wiki/)((?!:).)*$"),
            callback="parse_items",
            follow=True,
        ),
    ]

    def parse_items(self, response):
        url = response.url
        title = (response.css("h1::text").get() or "").strip()

        # 页脚「最后编辑」结构可能改版；多取一层文本以兼容
        raw = "".join(
            t.strip()
            for t in response.css("li#footer-info-lastmod ::text").getall()
            if t.strip()
        )
        last_updated = raw
        prefix = "This page was last edited on "
        if last_updated.startswith(prefix):
            last_updated = last_updated[len(prefix) :].strip()

        self.logger.info("URL: %s", url)
        self.logger.info("Title: %s", title)
        self.logger.info("Last updated: %s", last_updated)

        yield ArticleItem(url=url, title=title, last_updated=last_updated)
