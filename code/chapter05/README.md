# 第 5 章配套：Scrapy

## 维基 `CrawlSpider` 完整示例

本目录下 **`wikiSpider/`** 为可运行最小项目（与 `chapter-05.md` 对应）。

```bash
pip install scrapy
cd wikiSpider
scrapy crawl articles
```

可选导出：

```bash
scrapy crawl articles -o sample.json
```

`wikiSpider/settings.py` 中已开启 **`ROBOTSTXT_OBEY`**、**限速**、**`CLOSESPIDER_PAGECOUNT`**（演示用自动停）。请将 **`USER_AGENT`** 中的联系信息改为你可收信地址（维基 [User-Agent 政策](https://meta.wikimedia.org/wiki/User-Agent_policy)）。

---

## 从零创建项目（备忘）

```bash
scrapy startproject demo_scrapy
cd demo_scrapy
```

最简 `scrapy.Spider`：

```python
import scrapy

class ExampleSpider(scrapy.Spider):
    name = "example"
    start_urls = ["https://example.com/"]

    def parse(self, response):
        yield {"title": response.css("title::text").get()}
```

```bash
scrapy crawl example
```
