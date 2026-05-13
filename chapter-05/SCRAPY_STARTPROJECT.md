# Scrapy：`startproject` 备忘（第 5 章补充）

```bash
pip install scrapy
scrapy startproject demo_scrapy
cd demo_scrapy
```

最简 Spider：

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

`settings.py` 建议：`ROBOTSTXT_OBEY = True`，`DOWNLOAD_DELAY` 合理设置。
