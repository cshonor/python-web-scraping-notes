# 第5章配套：Scrapy 项目骨架说明

Scrapy 需要项目目录结构，不能单文件直接 `python spider.py` 运行整站流程。

## 创建项目

```bash
pip install scrapy
scrapy startproject demo_scrapy
cd demo_scrapy
```

在 `demo_scrapy/spiders/example.py` 中新建 Spider，例如：

```python
import scrapy

class ExampleSpider(scrapy.Spider):
    name = "example"
    start_urls = ["https://example.com/"]

    def parse(self, response):
        yield {"title": response.css("title::text").get()}
```

运行：

```bash
scrapy crawl example
```

建议先在 `demo_scrapy/settings.py` 中设置：

- `ROBOTSTXT_OBEY = True`
- `DOWNLOAD_DELAY = 1`

详见 `chapter-05.md`。
