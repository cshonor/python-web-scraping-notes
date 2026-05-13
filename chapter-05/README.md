# 第 5 章 Scrapy 框架

## 本章入口

- **完整学习笔记**：[笔记.md](笔记.md)  
- **Scrapy 工程**：[`wikiSpider/`](wikiSpider/)（内含 `scrapy.cfg`）

```bash
pip install scrapy
cd chapter-05/wikiSpider
scrapy crawl articles -o sample.json
```

运行前可将 `wikiSpider/wikiSpider/settings.py` 中的 **`USER_AGENT`** / **`mailto`** 改为你的标识。示例含 **`CLOSESPIDER_PAGECOUNT`** 与 **`DOWNLOAD_DELAY`**，避免对维基施压。
