# 第 5 章 Scrapy：学习笔记

Scrapy 是 Python 爬虫生态里**功能强、使用广**的框架之一。它不仅覆盖「找链接、区分域、发请求」等基础能力，还提供清晰的项目结构，适合**大型、可扩展、可维护**的抓取工程。

---

## 1. 核心知识点与原理

### 1.1 安装与初始化

- **安装建议**：Scrapy 依赖较多，除 `pip install scrapy` 外，在科学计算环境中也可用 **Anaconda**：`conda install -c conda-forge scrapy`，有时能减少底层依赖冲突。
- **项目初始化**：`scrapy startproject <projectName>`。生成常见骨架：`items.py`（字段模型）、`pipelines.py`（后处理）、`settings.py`（全局配置）、`spiders/`（爬虫类）。

### 1.2 爬虫的基本结构

- **`scrapy.Spider` 子类**：必须定义 **`name`**（项目内唯一）。
- **入口请求**：通常配置 **`start_urls`**，框架会据此生成初始 `Request`；若需动态构造入口，可重写 **`start_requests`**（二者二选一或组合使用，并非必须手写 `start_requests`）。
- **回调**：普通 Spider 默认回调为 **`parse`**，在回调里解析 `response`、**`yield` Item / dict / Request**。

### 1.3 自动遍历：`CrawlSpider` 与规则

- **`CrawlSpider`**：在基础 Spider 之上，用 **`Rule`** 描述「跟哪些链接、由谁解析、是否继续跟」。
- **`LinkExtractor`**：用 `allow` / `deny` 等（可为正则）描述 URL 模式。
- **`Rule` 常用参数**：`link_extractor`（必选）、`callback`（解析函数名或引用）、`cb_kwargs`、`follow`（是否继续从该页抽取链接再跟进）等。

### 1.4 数据模型与持久化

- **Item**：在 `items.py` 中声明字段，比裸 `dict` 更易约束与文档化。
- **导出**：`scrapy crawl myspider -o out.csv -t csv` 或 `-o out.json` 等，将 `yield` 的结构化结果落盘。

### 1.5 Item Pipeline

- **并发模型**：Scrapy 基于 Twisted，请求与回调高度重叠；Pipeline 中可做清洗、校验、去重、入库，与下载并行（仍受 Twisted reactor 调度）。
- **启用方式**：在 `settings.py` 的 **`ITEM_PIPELINES`** 中注册类路径，**数值越小越早执行**。

---

## 2. 关键配置与管理（易错点）

1. **日志**：默认较啰嗦。可在 `settings.py` 设 **`LOG_LEVEL = "WARNING"`**（或 `"ERROR"`），或使用 `--logfile`。
2. **速度与礼仪**：框架默认并发不低，务必配置 **`DOWNLOAD_DELAY` / `AUTOTHROTTLE`**、**`CONCURRENT_REQUESTS_PER_DOMAIN`** 等，并遵守 `robots.txt`（**`ROBOTSTXT_OBEY`**）。
3. **XPath 与 CSS**：XPath 适合复杂层级与文本切片；CSS 在简单结构上更直观。`response.css(...)` 与 `response.xpath(...)` 可混用。

---

## 3. 示例代码：基于规则的维基百科 `CrawlSpider`

以下演示用 **`Rule` + `LinkExtractor`** 在 `en.wikipedia.org` 上按词条 URL 模式跟进，并抽取标题与页脚「最后编辑」信息（选择器可能随维基改版变化，以开发者工具为准）。

**仓库内完整项目路径**：本章目录下的 **`wikiSpider/`** 子目录（Scrapy 项目）。  

核心爬虫文件：`wikiSpider/spiders/articles.py`

```python
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


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
        title = response.css("h1::text").get()
        last_updated = response.css("li#footer-info-lastmod::text").get()
        if last_updated:
            last_updated = last_updated.replace("This page was last edited on ", "")

        print(f"URL: {url}")
        print(f"Title: {title}")
        print(f"Last updated: {last_updated}")
```

运行（需已 `pip install scrapy`，并在项目根目录执行）：

```bash
cd wikiSpider
scrapy crawl articles
```

本仓库在 **`settings.py`** 中为示例增加了 **`CLOSESPIDER_PAGECOUNT`**、`DOWNLOAD_DELAY`、`USER_AGENT` 等，避免演示时压力过大；正式项目请按目标站政策调整。

---

## 4. 学习贴士

- **Scrapy 不替你猜站点结构**：URL 模式、选择器、字段含义仍由你定义，框架负责调度与工程组织。
- **复杂性与收益**：功能面宽、概念多，小任务可继续用 `requests`；多 Spider、多 Pipeline、长期运行时再上 Scrapy 更划算。

---

## 5. 与本仓库其他说明

补充备忘见同目录 **`SCRAPY_STARTPROJECT.md`**；维基示例以 **`wikiSpider/`** 子目录为准（进入该目录后执行 `scrapy crawl`）。

## 练习建议

1. 把 `print` 改为 **`yield` 字典或 Item**，并用 `-o wiki_sample.json` 导出。  
2. 新建一个 Pipeline：丢弃 `title` 为空的条目。  
3. 阅读 `robots.txt` 中与 `/wiki/` 相关的规则，思考 `Rule` 的 `allow` 是否应再收紧。
