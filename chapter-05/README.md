# 第 5 章 Scrapy 框架：学习笔记

第 4 章手写了一个「配置 + 引擎」的爬虫模型，能跑，但调度、并发、重试、去重、导出、日志全得自己搭。Scrapy 就是把这套东西做成框架：调度器、下载器、中间件、Pipeline 全部现成，你只写「抓哪些链接」和「怎么解析」。它基于 **Twisted** 做异步调度 —— 等网络 I/O 的时候穿插执行解析和 Pipeline，因此在中大型、长期维护的项目里，吞吐明显优于同步 `requests` 循环。

**本章目标**

1. 会用 **`scrapy startproject`** 建立标准工程结构
2. 理解 **`Spider` / `CrawlSpider` / `Rule` / `LinkExtractor`** 的分工
3. 会用 **`Item` + `Pipeline`** 做结构化输出与后处理
4. 理解 **`ITEM_PIPELINES` 优先级**、`settings.py` 里与礼貌抓取相关的选项
5. 知晓**现代 Scrapy** 已废弃的 **`scrapy.contrib.*`**，新代码一律用 `scrapy.spiders`、`scrapy.linkextractors` 等顶层包

---

## 1. 核心知识点与原理

### 1.1 安装与项目骨架

- **环境**：Scrapy 依赖多（Twisted、lxml、pyOpenSSL 等），纯 `pip` 偶发与底层库版本冲突。可用 conda：`conda install -c conda-forge scrapy`，或直接 `pip install scrapy`。
- **初始化**：`scrapy startproject wikiSpider`，得到标准骨架：

| 文件/目录 | 作用 |
|---|---|
| **`items.py`** | 字段模型（`scrapy.Field`） |
| **`pipelines.py`** | Item 后处理（清洗、校验、入库） |
| **`settings.py`** | 全局配置（限速、并发、Pipeline 注册、日志） |
| **`spiders/`** | 具体爬虫类 |

本仓库已包含可直接运行的 **`chapter-05/wikiSpider/`** 子项目，不需要再 `startproject`。

### 1.2 `scrapy.Spider` 的基本结构

- **唯一标识**：每个 Spider 必须定义唯一的 **`name`**（项目内不重复）。
- **入口**：
  - **`start_urls`**：框架据此自动生成初始 `Request`，默认回调 **`parse`**。
  - **`start_requests()`**：需要 POST 登录、带 Cookie、或动态生成起始 URL 时**重写**它，`yield Request(...)` 自定义第一步。
- **回调机制**：解析函数收到 **`response`**，可以 `yield` Item / dict 落盘或进 Pipeline，也可以 `yield Request(..., callback=...)` 继续跟链。

### 1.3 `CrawlSpider` 与规则驱动

`CrawlSpider` 用 **`Rule`** 描述「跟哪些链接、谁解析、是否继续跟」：

- **`LinkExtractor`**：用 **`allow` / `deny`**（正则或正则列表）约束 URL。
  **这里有个大坑**：`allow` 匹配的是**规范化后的绝对 URL 整串**，不是路径片段。所以维基词条应写

  ```python
  LinkExtractor(allow=r"/wiki/[^:#?]+$")
  ```

  在完整 `https://en.wikipedia.org/wiki/...` 上做**子串匹配**。如果照抄第 3 章的 `^(/wiki/)...$`（带 `^` 锚定行首），会**永远匹配不上**，表现是「爬虫跑起来了但一条都没抓到」。
- **`Rule`**：
  - **`callback`**：链接下载完成后调用的解析函数（字符串名或 callable）
  - **`follow`**：是否从当前页继续用本规则抽新链接；无 `callback` 时默认 `follow=True`
  - **`cb_kwargs`**：向回调传固定额外参数

### 1.4 `cb_kwargs`：一个回调查两种页

书中的 `articlesMoreRules` 一类示例的思路：

- **规则 1**：匹配词条 URL，`cb_kwargs={"is_article": True}`
- **规则 2**：匹配其余站内 URL，`cb_kwargs={"is_article": False}`
- **同一回调**内按 `is_article` 分支抽取字段，避免写两个几乎一样的 Spider 类

### 1.5 `Item` 与导出

- **`scrapy.Item`**：在 `items.py` 里用 `scrapy.Field()` 声明字段，比裸 `dict` 更易约束与协作。
- **导出**：不用写任何文件逻辑，命令行直接落盘

  ```bash
  scrapy crawl articles -o results.json
  scrapy crawl articles -o results.csv -t csv
  ```

### 1.6 异步调度与 Item Pipeline

- **并发模型**：Scrapy 跑在 **Twisted reactor** 上，单进程内靠**非阻塞 socket + 回调**重叠多路请求，而不是「一个请求一个线程」。等待下载时 CPU 去执行解析和 Pipeline（仍受 GIL 与单 reactor 约束，但比同步 `requests` 循环吞吐好得多）。
- **Pipeline**：校验、清洗、去重、写库。在 `settings.py` 的 **`ITEM_PIPELINES`** 中注册，**数值越小优先级越高**（越先执行）。

---

## 2. 关键配置与避坑（易错点）

1. **日志太吵**：默认输出很冗长。在 `settings.py` 设 `LOG_LEVEL = "WARNING"`，或运行时 `scrapy crawl articles -s LOG_FILE=wiki.log`，再 `tail -f wiki.log` 实时看。
2. **爬虫礼仪**：`DOWNLOAD_DELAY`、`AUTOTHROTTLE`、`CONCURRENT_REQUESTS_PER_DOMAIN` 控制对单站压力；`ROBOTSTXT_OBEY` 默认 `True`，应保留为常态。
3. **选择器**：`response.css()` 与 `response.xpath()` 并存。XPath 适合「带内嵌标签的一整段文本」。注意维基 **`mw-content-text`** 体量极大，实战要截取子树而不是整页抽正文。
4. **废弃 API**：旧书常见的 `scrapy.contrib.spiders.CrawlSpider` 等**已被移除**，现代写法是
   ```python
   from scrapy.spiders import CrawlSpider, Rule
   from scrapy.linkextractors import LinkExtractor
   ```
5. **最容易踩的坑：`CrawlSpider` 与起始 URL**
   框架对 `start_urls` 的首次响应走 **`parse_start_url`**（默认返回空），**不会**自动调用你在 `Rule` 里写的 `callback`。所以如果只写了 `Rule`，`-o` 导出的可能长时间是个空数组 —— 起始页自己反而没被解析。想两者都要，就**重写 `parse_start_url`**：

   ```python
   def parse_start_url(self, response):
       yield from self.parse_items(response)
   ```

   本仓库 `articles.py` 已按此处理。

---

## 3. 示例代码

完整工程：**`chapter-05/wikiSpider/`**，核心爬虫 **`wikiSpider/wikiSpider/spiders/articles.py`**。

要点：`CrawlSpider` + `Rule(LinkExtractor(allow=...), callback="parse_items", follow=True)`；解析中 `yield ArticleItem(...)`（类名见 `items.py`，与书中 `Article` 等价）；正文用 XPath 抽取并排除 `style` / `script`；`parse_start_url` 转发使起始页也产出 Item。

运行（必须进入含 `scrapy.cfg` 的那一层）：

```bash
cd chapter-05
pip install -r requirements.txt
cd wikiSpider
scrapy crawl articles -o sample.json
```

`settings.py` 中已配置 `USER_AGENT`、`DOWNLOAD_DELAY`、`CLOSESPIDER_PAGECOUNT`，便于演示；正式环境按目标站政策调整。**运行前请把 `USER_AGENT` 里的 `mailto` 改成你的真实联系方式。**

---

## 4. 学习贴士

- **不要滥用速度**。异步调度下 QPS 很容易冲高，不加限制就是 429 / 403 或违反条款。
- **什么时候不该用 Scrapy**：单页、低频、逻辑简单时，`requests` + BeautifulSoup 就够，上 Scrapy 只是多了十几个要理解的配置项。
- **什么时候该用**：需要多 Spider、规则遍历、Pipeline、长期调度、断点续爬时，Scrapy 才划算。
- **写 Scrapy 的心态**：它不帮你「抓对」，只帮你「抓得稳」。选择器仍然要自己调。

---

## 5. 与本仓库其他示例

本章只有一个 Scrapy 工程，结构如下：

```text
chapter-05/
├── README.md
├── requirements.txt
└── wikiSpider/          # Scrapy 项目根（含 scrapy.cfg）
    └── wikiSpider/
        ├── items.py
        ├── pipelines.py
        ├── settings.py
        └── spiders/
            └── articles.py
```

对比第 4 章的 `crawler_model.py` 看：`Website` ↔ `Rule` + `LinkExtractor`，`Content` ↔ `Item`，`Crawler` ↔ `Spider` + 引擎。同一套分层，Scrapy 把引擎那半边替你写完了。

---

## 练习建议

1. **Pipeline**：在 `pipelines.py` 里把 `last_updated` 的英文时间串解析成 `datetime`（维基格式随语言/皮肤变化，解析失败要优雅降级）。
2. **日志**：用 `-s LOG_FILE=...` 重定向日志，观察输出级别与 `CLOSESPIDER_PAGECOUNT` 的停止行为。
3. **限速实验**：临时调高并发、压低 `DOWNLOAD_DELAY`，观察是否出现 `HttpError` / 429，体会礼貌爬取的意义。
4. **验证 `parse_start_url`**：先把它注释掉跑一次，确认导出文件为空；再放开，对比结果 —— 一次就能记住「起始页不走 Rule 的 callback」这个坑。
