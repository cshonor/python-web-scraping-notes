# 第 5 章 Scrapy 框架：学习笔记

第 4 章手写了一个「配置 + 引擎」的爬虫模型，能跑，但调度、并发、重试、去重、导出、日志全得自己搭。Scrapy 就是把这套东西做成框架：调度器、下载器、中间件、Pipeline 全部现成，你只写「抓哪些链接」和「怎么解析」。它基于 **Twisted** 做异步调度 —— 等网络 I/O 的时候穿插执行解析和 Pipeline，因此在中大型、长期维护的项目里，吞吐明显优于同步 `requests` 循环。代价是心智成本：你不再「从上往下」读自己的代码，而是把逻辑拆成一个个回调交给引擎按事件触发，调试时必须先想清楚「这条数据此刻走到引擎的哪一环」。本章的 wikiSpider 工程就是这条思路的最小完整样本：一个 `CrawlSpider`、一条 `Rule`、两个 `Pipeline`、一份 `settings.py`，覆盖了框架约八成日常用法。

**本章目标**

1. 会用 **`scrapy startproject`** 建立标准工程结构，说清每个生成文件的职责
2. 理解 **`Spider` / `CrawlSpider` / `Rule` / `LinkExtractor`** 的分工，以及 **`cb_kwargs`** 的传参用法
3. 会用 **`Item` + `Pipeline`** 做结构化输出与后处理，理解 **`ITEM_PIPELINES` 优先级**
4. 能复述一个 `Request` 从 `yield` 出去到 `response` 回到回调的**完整链路**
5. 知晓**现代 Scrapy** 已废弃的 `scrapy.contrib.*`，新代码一律用 `scrapy.spiders`、`scrapy.linkextractors` 等顶层包

---

## 1. 核心知识点与原理

### 1.1 安装与项目骨架

- **环境**：Scrapy 依赖多（Twisted、lxml、pyOpenSSL 等），纯 `pip` 偶发与底层库版本冲突。可用 conda：`conda install -c conda-forge scrapy`，或直接 `pip install scrapy`。本章 `requirements.txt` 只锁定 `scrapy>=2.11.0`；本次笔记在本地环境实测装到的是 2.19.0，`scrapy list` 能正常发现爬虫。
- **初始化**：`scrapy startproject wikiSpider`，得到标准骨架。注意命令会在**当前目录**下再建一层同名目录，所以实际项目里常看到 `wikiSpider/wikiSpider/` 这种双层结构：外层是「工程根」（含 `scrapy.cfg`），内层是「Python 包」。

| 文件/目录 | 作用 | 本章是否用到 |
|---|---|---|
| **`scrapy.cfg`** | 部署配置；`[settings] default = wikiSpider.settings` 告诉命令行去哪找配置 | 有，运行命令的「定位锚点」 |
| **`items.py`** | 字段模型（`scrapy.Field`），定义 Item 有哪些键 | 有，`ArticleItem` |
| **`pipelines.py`** | Item 后处理（清洗、校验、入库），可注册多个 | 有，两个 Pipeline |
| **`settings.py`** | 全局配置（限速、并发、Pipeline 注册、日志） | 有，且是本章配置事实来源 |
| **`spiders/`** | 具体爬虫类，一个文件可放多个 Spider | 有，`articles.py` |
| `middlewares.py` | 下载器/爬虫中间件模板 | 生成后未改动（略） |

本仓库已包含可直接运行的 **`chapter-05/wikiSpider/`** 子项目，不需要再 `startproject`。

### 1.2 `scrapy.Spider` 的基本结构

- **唯一标识**：每个 Spider 必须定义唯一的 **`name`**（项目内不重复），`scrapy crawl <name>` 靠它定位类。
- **入口**：
  - **`start_urls`**：框架据此自动生成初始 `Request`，默认回调 **`parse`**。
  - **`start_requests()`**：需要 POST 登录、带 Cookie、或动态生成起始 URL 时**重写**它，`yield Request(...)` 自定义第一步。
- **域约束**：**`allowed_domains`** 列表外的 URL 会被引擎直接丢弃，是防止爬虫「跑出站」的第一道闸。本章 `articles.py` 里设为 `["en.wikipedia.org"]`，保证只在英文维基内遍历。
- **回调机制**：解析函数收到 **`response`**，可以 `yield` Item / dict 落盘或进 Pipeline，也可以 `yield Request(..., callback=...)` 继续跟链。**回调都是生成器**，忘了 `yield` 只 `return` 是新手最常见的「解析函数跑了但没产出」。

### 1.3 `CrawlSpider` 与规则驱动

普通 `Spider` 里你要手动 `yield Request(...)` 跟链；`CrawlSpider` 把这个动作声明化：用 **`rules = [Rule(...), ...]`** 描述「跟哪些链接、谁解析、是否继续跟」，框架自动完成「抽链接 → 过滤 → 去重 → 排队 → 下载 → 回调」。

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

`allow` 与 `deny` 的语义差异也值得记住：`allow` 是**白名单**（至少命中一条才放行），`deny` 是**黑名单**（命中即丢弃）。本章规则里两者并用：`allow` 圈定 `/wiki/` 词条页，`deny` 再剔除 `Talk:`、`User:`、`File:` 等命名空间 —— 白名单管「要什么」，黑名单管「在要的范围里排除什么」。

### 1.4 `cb_kwargs`：一个回调查两种页

书中的 `articlesMoreRules` 一类示例的思路：

- **规则 1**：匹配词条 URL，`cb_kwargs={"is_article": True}`
- **规则 2**：匹配其余站内 URL，`cb_kwargs={"is_article": False}`
- **同一回调**内按 `is_article` 分支抽取字段，避免写两个几乎一样的 Spider 类

`cb_kwargs` 的值会被原样合并进回调的 `**kwargs`，所以回调签名写成 `def parse_items(self, response, is_article):` 即可接到。它的适用边界：传的是**固定的、随规则而定的常量**；如果参数要随页面动态变化，应改用 `Request` 的 `meta` 字典（如 `Request(url, callback=..., meta={"page_no": n})`），在回调里用 `response.meta["page_no"]` 取回。

### 1.5 `Item` 与导出

- **`scrapy.Item`**：在 `items.py` 里用 `scrapy.Field()` 声明字段，比裸 `dict` 更易约束与协作 —— 字段名打错会在赋值时直接报 `KeyError`，而不是静默地把脏数据带进导出文件。
- **导出**：不用写任何文件逻辑，命令行直接落盘

  ```bash
  scrapy crawl articles -o results.json
  scrapy crawl articles -o results.csv -t csv
  ```

  `-o` 按扩展名自动推断格式（json / jsonlines / csv / xml 等），`-t` 可显式覆盖。框架内部走的是 **Feed Exporter**：Item 从 Pipeline 出来后由 Exporter 统一序列化，所以 Pipeline 与落盘格式完全解耦。
- **注意事项**：`-o results.json` 是整个数组一次性写出，进程被强杀可能得到一个残缺的 JSON；长时间任务更稳的选择是 **JSON Lines**（`-o results.jl`），每行一条、可断点追加。

### 1.6 异步调度与 Item Pipeline

- **并发模型**：Scrapy 跑在 **Twisted reactor** 上，单进程内靠**非阻塞 socket + 回调**重叠多路请求，而不是「一个请求一个线程」。等待下载时 CPU 去执行解析和 Pipeline（仍受 GIL 与单 reactor 约束，但比同步 `requests` 循环吞吐好得多）。
- **Pipeline**：校验、清洗、去重、写库。在 `settings.py` 的 **`ITEM_PIPELINES`** 中注册，**数值越小优先级越高**（越先执行）。约定俗成用 100–1000 的整数，留出插入空间。本章 `settings.py` 里 `LastUpdatedParsePipeline: 200` 先于 `WikiSpiderPipeline: 300` 执行。
- **生命周期钩子**：除 `process_item(item, spider)` 外，Pipeline 还可实现 `open_spider(spider)`（爬虫启动时开连接、建表）与 `close_spider(spider)`（结束时提交事务、关连接）—— 入库类 Pipeline 的标准结构就是「open 建连接 / process 写入 / close 提交并关闭」。
- **丢弃 Item**：`process_item` 里 `raise DropItem("原因")` 可让该 Item 不再流向后续 Pipeline 与导出，用于「标题为空就丢」这类过滤。

### 1.7 请求从 `yield` 到 `response` 的完整链路

把第 4 章的 `Crawler` 放大成工业级，一个 `Request` 在 Scrapy 里的生命周期是：

```text
Spider.yield Request
  → Scheduler（入队、按域/按优先级排队，指纹去重）
  → Downloader Middlewares（process_request：改头、代理、重试）
  → Downloader（Twisted 异步发请求，受 CONCURRENT_REQUESTS / DOWNLOAD_DELAY 约束）
  → Downloader Middlewares（process_response / process_exception）
  → Spider Middlewares（process_spider_input）
  → Spider 回调（parse / Rule.callback）
  → 回调 yield 的 Item → Spider Middlewares（process_spider_output）→ Item Pipeline 链
  → 回调 yield 的新 Request → 回到 Scheduler，循环
```

三个工程含义：

1. **去重在 Scheduler**：默认按 `request.fingerprint`（URL + 方法 + body 的哈希）去重，所以环形链接不会导致死循环；要允许重复请求需显式 `Request(..., dont_filter=True)`。
2. **限速在 Downloader**：`DOWNLOAD_DELAY`、`CONCURRENT_REQUESTS_PER_DOMAIN` 都作用在这一层，改 Pipeline 并不能降低对站压力。
3. **异常在中间件**：下载失败（超时、5xx）默认由 `RetryMiddleware` / `HttpErrorMiddleware` 处理，非 2xx 响应通常**不会**进你的回调；想自己处理状态码要在 `Request` 的 `meta` 里加 `handle_httpstatus_list`。

---

## 2. 关键配置与避坑（易错点）

1. **最容易踩的坑：`CrawlSpider` 与起始 URL**。框架对 `start_urls` 的首次响应走 **`parse_start_url`**（默认实现只 `yield` 自 Rule 抽取、本身不产出 Item），**不会**自动调用你在 `Rule` 里写的 `callback`。所以如果只写了 `Rule`，`-o` 导出的可能长时间是个空数组 —— 起始页自己反而没被解析。想两者都要，就**重写 `parse_start_url`** 转发到你的解析函数：

   ```python
   def parse_start_url(self, response):
       yield from self.parse_items(response)
   ```

   本仓库 `articles.py` 已按此处理；实测时起始词条 Python 页的 Item 正是经这条路径产出的。

2. **`LinkExtractor` 的 `allow` 匹配整串 URL**（对应 1.3 节的大坑）。正则里的 `^` 会锚到 `https://` 的行首而不是路径起点，照抄 `requests` 时代的 `^(/wiki/)` 必然颗粒无收。排障套路：先 `scrapy shell "https://en.wikipedia.org/wiki/Python_(programming_language)"`，在里面手动 `LinkExtractor(allow=...).extract_links(response)`，看返回列表是不是空 —— 比整跑一遍爬虫快得多。

3. **日志太吵**：默认输出很冗长。在 `settings.py` 设 `LOG_LEVEL = "WARNING"`（本章已设），或运行时 `scrapy crawl articles -s LOG_FILE=wiki.log` 再 `tail -f` 实时看；调试期则可 `-L INFO` / `-L DEBUG` 临时提高级别。注意 `-s NAME=VALUE` 是**运行时覆盖 settings.py** 的通用机制，不必为一两次实验改文件。

4. **爬虫礼仪与限速配置**：`DOWNLOAD_DELAY`（相邻请求最小间隔）、`CONCURRENT_REQUESTS_PER_DOMAIN`（单域并发）控制对单站压力；`ROBOTSTXT_OBEY` 默认 `True`，应保留为常态。本章 `settings.py` 的取值是 `DOWNLOAD_DELAY = 1.0`、`CONCURRENT_REQUESTS_PER_DOMAIN = 2`、`CONCURRENT_REQUESTS = 4`，属于「演示友好型」；另外 `CLOSESPIDER_PAGECOUNT = 30` 是演示保险丝 —— 抓够页数自动停止，防止忘关终端把维基刷一夜。正式环境按目标站政策调整，且**运行前请把 `USER_AGENT` 里的 `mailto` 改成你的真实联系方式**。

5. **选择器的坑**：`response.css()` 与 `response.xpath()` 并存。XPath 适合「带内嵌标签的一整段文本」与 `not(ancestor::...)` 这类结构排除。注意维基 **`mw-content-text`** 体量极大（一个长词条全部 text 节点可达几十万字符），实战要截取子树或像本章一样做长度截断，而不是整页抽正文原样入库 —— 否则一条 Item 几 MB，导出文件很快失控。

6. **废弃 API**：旧书常见的 `scrapy.contrib.spiders.CrawlSpider` 等**已被移除**，现代写法是

   ```python
   from scrapy.spiders import CrawlSpider, Rule
   from scrapy.linkextractors import LinkExtractor
   ```

   同理 `scrapy.contrib.pipeline`、`scrapy.contrib.loader` 也都拆了包。在网上抄代码时先核对导入路径，能省掉一半的 `ImportError`。

7. **运行目录与模块名**：`scrapy crawl` 必须在**含 `scrapy.cfg` 的那一层**执行，否则报 `Error: scrapy.cfg not found`；`settings.py` 里的 `SPIDER_MODULES = ["wikiSpider.spiders"]` 是 Python 导入路径，改了内层包名或挪动目录要同步改这里。另外 Spider 的 `name` 与文件名无关，`scrapy list` 列的是类属性 `name`，改名后旧命令会静默报 `KeyError: Spider not found`。

---

## 3. 示例代码

完整工程：**`chapter-05/wikiSpider/`**，共四个实质源文件。以下逐个走读（行号以仓库当前版本为准）。本节结果**已实测**：在 `CLOSESPIDER_PAGECOUNT=5` 下实跑，产出 7 个 Item / 8 个响应，7/7 的 `last_updated_iso` 被 Pipeline 成功解析（2026-11-02，本机 Scrapy 2.19.0）。

### 3.1 `items.py`：字段模型

只有 12 行，定义 `ArticleItem(scrapy.Item)`，五个字段：`url`、`title`、`text`（注释明确说明由爬虫截断、避免单条 Item 过大）、`last_updated`（页脚原始时间串）、`last_updated_iso`（由 Pipeline 尝试解析，**失败则不写入**）。这份文件的价值不在代码量而在「契约」：Spider 只承诺填前四个字段，第五个是否出现取决于 Pipeline —— 下游消费者必须用 `item.get("last_updated_iso")` 而不是 `item["last_updated_iso"]`，否则会遇到偶发 `KeyError`。

```python
class ArticleItem(scrapy.Item):
    url = scrapy.Field()
    title = scrapy.Field()
    # 正文区域文本（由爬虫截断，避免单条 Item 过大）
    text = scrapy.Field()
    last_updated = scrapy.Field()
    # 由 Pipeline 尝试解析；失败则不写入
    last_updated_iso = scrapy.Field()
```

### 3.2 `pipelines.py`：透传 + 时间解析

两个类。`WikiSpiderPipeline` 是占位用的透传（`process_item` 直接 `return item`），注释提示「可在此做去重、丢弃空标题」—— 骨架先立住，逻辑后补。`LastUpdatedParsePipeline` 是实质逻辑：先用 `_prefix` 正则剥掉 `This page was last edited on` 前缀（不区分大小写），再用 `_footer_re` 匹配 `13 May 2026, at 13:35` 这类页脚格式（兼容历史页面末尾的 `(UTC).`），分组补零后交给 `datetime.strptime` 按 `"%d %B %Y, at %H:%M."` 解析，成功则写入 `last_updated_iso = dt.isoformat() + "Z"`；任何一步不匹配都**静默跳过**而不是抛异常 —— 不同语言皮肤的页脚格式差异很大，「解析不了就留空」比「解析不了就报错」更符合抓取的容错哲学。

```python
def process_item(self, item, spider):
    raw = item.get("last_updated")
    if not raw:
        return item
    s = self._prefix.sub("", str(raw)).strip()
    m = self._footer_re.match(s)
    if not m:
        return item
    day, rest, hh, mm = m.groups()
    padded = f"{int(day):02d} {rest}, at {int(hh):02d}:{int(mm):02d}."
    try:
        dt = datetime.strptime(padded, "%d %B %Y, at %H:%M.")
        item["last_updated_iso"] = dt.isoformat() + "Z"
    except ValueError:
        pass
    return item
```

实测中起始页 `Python (programming language)` 的页脚 `1 November 2026, at 10:22` 被解析为 `2026-11-01T10:22:00Z`，验证了这条链路。

### 3.3 `settings.py`：全局配置

25 行，每一项都有明确意图，可对照下表记忆：

| 配置项 | 取值 | 意图 |
|---|---|---|
| `BOT_NAME` / `SPIDER_MODULES` / `NEWSPIDER_MODULE` | `wikiSpider` 相关 | 工程标识与 Spider 发现路径 |
| `ROBOTSTXT_OBEY` | `True` | 遵守 robots.txt，礼仪底线 |
| `USER_AGENT` | 含 bot 名、仓库地址与 `mailto:you@example.com` | 合规 UA，用前须改联系方式 |
| `CONCURRENT_REQUESTS` | `4` | 全局并发上限 |
| `DOWNLOAD_DELAY` | `1.0` | 相邻请求最小间隔（秒） |
| `CONCURRENT_REQUESTS_PER_DOMAIN` | `2` | 单域并发上限 |
| `LOG_LEVEL` | `"WARNING"` | 默认安静，调试改 `INFO` |
| `CLOSESPIDER_PAGECOUNT` | `30` | 演示保险丝，抓 30 页自动停 |
| `ITEM_PIPELINES` | `LastUpdatedParsePipeline: 200`、`WikiSpiderPipeline: 300` | 数值小的先执行 |

注意 `CLOSESPIDER_PAGECOUNT` 统计的是**响应数**而非 Item 数（重定向、robots.txt 之外的不合规页也会计入），所以「页数 5」不代表「Item 5 条」—— 实测 5 页上限产出 7 条 Item（起始页由 `parse_start_url` 补齐），正因为统计口径不同。

### 3.4 `spiders/articles.py`：核心爬虫

`ArticleSpider(CrawlSpider)`，`name = "articles"`，`allowed_domains = ["en.wikipedia.org"]`，起始页是 Python 编程语言词条。唯一一条 `Rule`：`LinkExtractor(allow=r"/wiki/[^:#?]+$", deny=r"/wiki/(Talk|User|User_talk|Wikipedia|File|Help|Category):")` 圈定词条页并排除讨论/用户/文件等命名空间，`callback="parse_items"`、`follow=True`。`parse_start_url` 显式 `yield from self.parse_items(response)`，把起始页也纳入产出（对应第 2 节第 1 条大坑）。`parse_items` 内部：标题选择器做了三级回退（Vector 皮肤的 `h1 .mw-page-title-main` → 旧皮肤的 `h1#firstHeading` → 兜底 `h1` 全部文本拼接）；正文用 XPath `//div[@id="mw-content-text"]//text()[not(ancestor::style) and not(ancestor::script)]` 抽取并排除 `style`/`script`，拼接后按 `_TEXT_PREVIEW_LIMIT = 8000` 截断（超长追加 `\n…[truncated]`，实测单条 `text` 长 8013 字符，截断生效）；`last_updated` 从 `li#footer-info-lastmod` 抽取后剥前缀与 `(UTC)` 尾巴。最后 `yield ArticleItem(...)`。

```python
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
    yield from self.parse_items(response)
```

运行（必须进入含 `scrapy.cfg` 的那一层）：

```bash
cd chapter-05
pip install -r requirements.txt
cd wikiSpider
scrapy list                                  # 应输出: articles
scrapy crawl articles -o sample.json         # 完整跑（受 CLOSESPIDER_PAGECOUNT=30 限制）
scrapy crawl articles -s CLOSESPIDER_PAGECOUNT=5 -o sample.json -L INFO   # 小流量试跑
```

**已实测**：`scrapy list` 输出 `articles`；小流量试跑日志可见逐条 `URL: ... / Title: ...`，收尾统计 `item_scraped_count: 7`、`response_received_count: 8`。其中 `BlueBream` 词条的标题解析为 `Zope`，是目标页发生重定向、回调收到的是最终落地页的 `response` —— 说明 `response.url` 与 `title` 永远反映**最终响应**而非最初请求的 URL。

---

## 4. 学习贴士

- **不要滥用速度**。异步调度下 QPS 很容易冲高，不加限制就是 429 / 403 或违反条款。`DOWNLOAD_DELAY` 与单域并发不是「性能参数」而是「准入资格」，先调礼貌再调性能。
- **什么时候不该用 Scrapy**：单页、低频、逻辑简单时，`requests` + BeautifulSoup 就够，上 Scrapy 只是多了十几个要理解的配置项。判断标准：你要不要「跟链 + 去重 + 并发 + 导出」中的至少三样？不要就别上。
- **什么时候该用**：需要多 Spider、规则遍历、Pipeline、长期调度、断点续爬（`scrapy crawl articles -s JOBDIR=crawls/job1`）时，Scrapy 才划算。
- **用 `scrapy shell` 调选择器**：`scrapy shell <url>` 进入交互环境，直接对 `response` 试 `css` / `xpath`，比改代码再整跑快一个数量级；本章标题三级回退与正文 XPath 都适合先在 shell 里验证。
- **写 Scrapy 的心态**：它不帮你「抓对」，只帮你「抓得稳」。选择器仍然要自己调，框架替你兜住的是并发、重试、去重这些「脏活」。

---

## 5. 与本仓库其他示例

本章只有一个 Scrapy 工程，结构与各文件职责如下：

| 文件 | 说明 | 实测情况 |
|---|---|---|
| `chapter-05/requirements.txt` | 本章依赖：`scrapy>=2.11.0` | 已装（2.19.0） |
| `chapter-05/wikiSpider/scrapy.cfg` | `[settings] default = wikiSpider.settings`，运行命令的定位锚点 | — |
| `chapter-05/wikiSpider/wikiSpider/items.py` | `ArticleItem` 五字段契约 | 字段与实测导出一致 |
| `chapter-05/wikiSpider/wikiSpider/pipelines.py` | 透传 Pipeline + 页脚时间解析 Pipeline | 7/7 解析成功 |
| `chapter-05/wikiSpider/wikiSpider/settings.py` | 限速、日志、`CLOSESPIDER_PAGECOUNT`、`ITEM_PIPELINES` | 见 §3.3 表 |
| `chapter-05/wikiSpider/wikiSpider/spiders/articles.py` | `CrawlSpider` + `Rule` + `parse_start_url` 转发 | 5 页上限产出 7 Item |

对比第 4 章的 `crawler_model.py` 看：`Website` ↔ `Rule` + `LinkExtractor`，`Content` ↔ `Item`，`Crawler` ↔ `Spider` + 引擎。同一套分层，Scrapy 把引擎那半边替你写完了。再往第 6 章看：本章 `process_item` 里 `return item` 的位置，换成 `csv.writer` / `sqlite3` / `pymysql` 的写入逻辑，就是第 6 章「存储数据」的落库姿势 —— 两章拼起来正好是一条「抓得到、存得下」的完整链路。

---

## 练习建议

1. **验证 `parse_start_url`**：先把它注释掉跑一次（配合 `-s CLOSESPIDER_PAGECOUNT=5`），确认起始词条的 Item 从导出中消失；再放开对比 —— 一次就能记住「起始页不走 Rule 的 callback」这个坑。
2. **LinkExtractor 实验**：在 `scrapy shell` 里分别用 `allow=r"^/wiki/"` 与 `allow=r"/wiki/"` 抽链接，观察前者为何为空；再试 `deny` 单独存在（不带 `allow`）时规则匹配哪些 URL。
3. **限速实验**：临时 `scrapy crawl articles -s DOWNLOAD_DELAY=0.1 -s CONCURRENT_REQUESTS_PER_DOMAIN=8 -s CLOSESPIDER_PAGECOUNT=10`，观察日志中是否出现 `HttpError` / 429，体会礼貌爬取的意义（实验完恢复默认）。
4. **Pipeline 加去重**：在 `WikiSpiderPipeline.process_item` 里维护 `self.seen = set()`，按 `item["url"]` 去重，重复时 `raise DropItem(...)`，验证闭环。
5. **`cb_kwargs` 改造**：新增一条 `Rule` 匹配 `/wiki/Category:` 页面并 `cb_kwargs={"page_type": "category"}`，在 `parse_items` 里按 `page_type` 分支只记标题不记正文。
6. **断点续爬**：连续两次运行 `scrapy crawl articles -s JOBDIR=/tmp/wiki-job`（第二次前删掉导出文件），观察第二次启动时 Scheduler 如何从 JOBDIR 恢复去重指纹与请求队列。
