# 第 4 章 网络爬虫模型：学习笔记

本章讨论如何设计**可扩展、稳健且易于维护**的爬虫架构。相比为每个站点各写一套脚本，更强调用**数据模型**与**通用爬虫类**消化不同页面布局。

---

## 1. 核心知识点与原理

### 1.1 规划与定义对象

网页抓取的一个常见陷阱是完全基于「当前页面上有什么」来定义字段。

- **原则**：少问「网页上存在什么？」，多问「**业务上我需要什么？**」。
- **数据规范化**：从多个源抓相似实体时，应映射到**同一套字段**（可比、可合并、可校验），而不是长期保留各站原生结构。
- **稀疏属性**：若某些字段（如面料、页码）只在少数条目出现，可用 **键值列表/字典**（EAV 思路）或 JSON 列存储，避免为每个稀疏字段硬加一列表结构。

### 1.2 处理不同的网站布局

若每个站点单独一个解析函数，站点数上百时维护成本会陡增。

- **`Website` 类（配置模型）**：通常不存抓取结果，而存**抓取指令**——例如标题、正文的 **CSS 选择器**（或解析规则），而不是标题文字本身。
- **`Crawler` 类（执行引擎）**：接收 `Website` 配置，用统一的 `getPage` + `select`/`find` 流程产出结构化对象（如 `Content`）。

### 1.3 结构化爬虫模式

1. **通过搜索抓取**：利用搜索 URL 的参数模式（如 `?q=topic`）批量生成入口，再进入列表页与详情页流水线。
2. **通过链接抓取**：用正则或规则描述「要跟进的 URL 形状」（如 `^/article/`），在站内自动发现与去重（与第 3 章衔接）。
3. **多页面类型抓取**：按 URL 模式、页面特征标签或字段缺失情况区分类型（如「文章」与「产品」），用 **继承/组合**（子类扩展 `Website` 或独立 `Parser` 策略对象）组织代码，避免巨型 `if-else`。

---

## 2. 关键建议与易错点

- **负载均衡**：多主题、多站点批跑时，宜**外循环主题、内层交错站点**或带全局限速的队列，避免短时间对同一主机上万请求（与第 3、16 章呼应）。
- **灵活性 vs 稳健性**：通用模板扩展性强，但依赖**选择器稳定**；改版后往往是配置层改一行，而不是全项目复制粘贴。
- **过度工程化**：先评估稀疏元数据对业务的边际价值，再决定要不要为极冷门字段建复杂模型。

---

## 3. 示例代码：多网站布局与通用 `Crawler`

以下展示「`Website` 存选择器 + `Crawler` 统一解析」的思路（与书中类名一致；为符合 Python 习惯，将 `Content.print` 改为 **`display`**，避免遮蔽内置 `print`）。

**易错点勘误（原书片段常见笔误）**：

- `parse` 的第二个参数应是**单条 URL**；第一个参数应是**一个 `Website` 实例**，而不是把整个 `websites` 列表传进去。应对「每条 URL」选用匹配站点配置，再调用 `crawler.parse(site, url)`。
- 书中 Reuters / Brookings / NYTimes 的 **class 名会随改版失效**，仅作模式参考；线上练习时请用开发者工具重新确认选择器。

可运行脚本（含**离线双站**演示 + **example.com** 一次线上探测）：`chapter-04/scraper_model_demo.py`

```python
import requests
from bs4 import BeautifulSoup


class Content:
    """所有网页的共同基类"""

    def __init__(self, url, title, body):
        self.url = url
        self.title = title
        self.body = body

    def display(self):
        print(f"URL: {self.url}")
        print(f"TITLE: {self.title}")
        print(f"BODY:\n{self.body}\n")


class Website:
    """描述网站结构（选择器配置）"""

    def __init__(self, name, url, titleTag, bodyTag):
        self.name = name
        self.url = url
        self.titleTag = titleTag
        self.bodyTag = bodyTag


class Crawler:
    def getPage(self, url):
        try:
            req = requests.get(url, timeout=20)
            req.raise_for_status()
        except requests.exceptions.RequestException:
            return None
        return BeautifulSoup(req.text, "lxml")

    def safeGet(self, pageObj, selector):
        selectedElems = pageObj.select(selector)
        if len(selectedElems) > 0:
            return "\n".join([elem.get_text(strip=True) for elem in selectedElems])
        return ""

    def parse(self, site, url):
        bs = self.getPage(url)
        if bs is not None:
            title = self.safeGet(bs, site.titleTag)
            body = self.safeGet(bs, site.bodyTag)
            if title != "" and body != "":
                content = Content(url, title, body)
                content.display()


# 配置多个站点（选择器需按实际页面维护）
brookings = Website(
    "Brookings",
    "http://www.brookings.edu",
    "h1",
    "div.post-body",
)
nyt = Website("New York Times", "http://nytimes.com", "h1", "p.story-content")

crawler = Crawler()
crawler.parse(
    brookings,
    "https://www.brookings.edu/blog/techtank/2016/03/01/idea-to-retire-old-methods-of-policy-education/",
)
crawler.parse(
    nyt,
    "https://www.nytimes.com/2018/01/28/business/energy-environment/oil-boom.html",
)
```

---

## 4. 学习贴士

- **GitHub 参考**：书中结构化爬虫的更多变体可见作者仓库：[REMitchell/python-scraping](https://github.com/REMitchell/python-scraping)。
- **提前规划**：先画数据流（入口 URL → 列表 → 详情 → 规范化记录），再写类与模块边界，能显著降低后期返工。

---

## 5. 与本仓库其他示例

`chapter-04/crawler_model.py` 演示 **`PageRecord` 数据类 + `fetch`/`parse`/`run` 分层**，可与本课的 `Website`/`Crawler` 模式对照阅读。

## 练习建议

1. 为 `Crawler` 增加 `parse_soup(site, url, soup)`，便于单元测试不传网络。  
2. 写一个函数：根据 `urlparse(url).netloc` 从 `list[Website]` 中挑选默认配置（找不到则返回 `None`）。  
3. 任选一新闻页，用开发者工具更新 `titleTag`/`bodyTag`，观察 `safeGet` 输出变化。
