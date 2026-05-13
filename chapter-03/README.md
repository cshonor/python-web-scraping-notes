# 第 3 章 编写网络爬虫：学习笔记

本章从处理单个静态页面转向现实中的复杂问题：如何编写能够**在网站内跳转**、发现新页面，并在需要时**跨站遍历**的网络爬虫。

---

## 1. 核心知识点与原理

### 1.1 遍历单个域名（以维基百科为例）

网络爬虫本质上常采用**递归或带队列的反复扩展**：获取一个 URL 的页面，解析出新的 URL，再请求、再解析，循环往复。

- **筛选特定链接**：为避免抓到侧栏、页脚等噪声链接，需要利用**链接模式**。以英文维基**词条页**为例，常见规则包括：链接出现在 `id` 为 `bodyContent` 的 `div` 内、路径以 `/wiki/` 开头，且**不包含冒号**（排除 `Special:`、`Help:` 等名字空间）。
- **正则实现**：可用如下模式匹配典型词条链接（与书中思路一致）：

```text
^(/wiki/)((?!:).)*$
```

含义简述：`/wiki/` 开头，且整段路径中不出现冒号（用 `(?!:).` 约束）。

### 1.2 抓取整个网站与链接去重

抓取整站常用于站点地图或大范围采集。

- **去重**：页面之间相互链接，若不记录已访问 URL，易出现**死循环**与重复抓取。常用 **`set`** 保存已发现的唯一路径（或规范化后的完整 URL）。
- **递归深度**：Python 默认递归深度有限（约 1000 层）；整站或深链结构更适合**显式队列/栈**（BFS/DFS）+ 去重，而不是无界递归。

### 1.3 在互联网上抓取（跨域）

此类爬虫不局限于站内，会跟随外链进入其他域名。

- **链接分类**：用 `urllib.parse.urlparse` 比较 `netloc`，区分**内链**与**外链**，并分别制定是否跟进、限速与存储策略。
- **重定向**：
  - **HTTP 重定向**：`urllib.request.urlopen` 通常会自动跟随 3xx（行为与配置有关，宜实测）。
  - **客户端重定向**（JavaScript、`meta refresh` 等）：纯 `urllib` 拿不到执行后的 URL，往往需要 **Selenium / Playwright** 等浏览器环境（见第 11 章）。

---

## 2. 关键建议与易错点

1. **服务器负载**：大规模抓取占用带宽与 CPU。应在请求间加入延迟（如 `time.sleep`）、控制并发，并遵守 `robots.txt` 与站点条款。
2. **异常与结构变更**：遍历中若 DOM 变化（如 `id` 改名），`find` 链可能得到 `None`，进而触发 **`AttributeError`**。应对「找不到容器」分支做判断，并记录失败 URL 便于重试。
3. **匿名性与法律**：跨站与高频抓取可能触发封禁或法律风险，需结合第 18 章评估授权与用途。

---

## 3. 示例代码：维基百科词条抓取器

以下演示从起始词条出发，**随机挑选**同页词条链接继续访问，并用 **`set` 去重**（书中经典写法）。

**实务建议（运行前必读）**：

- 维基媒体基金会要求请求携带**可识别、可联系的 User-Agent**（见 [User-Agent 政策](https://meta.wikimedia.org/wiki/User-Agent_policy)）。示例脚本使用 `urllib.request.Request` 设置 UA；请把其中的联系信息改成你自己的。
- 示例已改为 **`https://en.wikipedia.org`**，并加入**超时、礼貌延迟、最大词条数**，避免对服务器造成压力或本地无限运行。

可运行脚本：`chapter-03/wikipedia_random_walk.py`

书中原版风格（逻辑等价；生产环境请自行加上 UA、HTTPS 与限速）：

```python
from urllib.request import urlopen
from bs4 import BeautifulSoup
import re
import datetime
import random

random.seed(datetime.datetime.now())


def getLinks(articleUrl):
    try:
        html = urlopen("http://en.wikipedia.org{}".format(articleUrl))
        bs = BeautifulSoup(html, "html.parser")
        return bs.find("div", {"id": "bodyContent"}).find_all(
            "a", href=re.compile("^(/wiki/)((?!:).)*$")
        )
    except Exception as e:
        print(f"获取链接时出错: {e}")
        return []


pages = set()


def crawl(articleUrl):
    global pages
    links = getLinks(articleUrl)
    while len(links) > 0:
        newArticle = links[random.randint(0, len(links) - 1)].attrs["href"]
        if newArticle not in pages:
            print(f"发现新词条: {newArticle}")
            pages.add(newArticle)
            crawl(newArticle)
        else:
            continue


crawl("/wiki/Kevin_Bacon")
```

---

## 4. 学习贴士

- **API 优先**：若目标站提供公开 API（维基百科有 [MediaWiki API](https://www.mediawiki.org/wiki/API)），通常比只解析 HTML 更稳定、更省资源。
- **规范化**：多源抓取时，尽早把 URL、编码与字段格式**规范化**，便于去重与下游分析。

---

## 5. 与本仓库其他示例

同章另有基于 `requests` 的极简同域爬取示例：`chapter-03/simple_crawler.py`（`example.com`，适合练手）。

## 练习建议

1. 用 `urllib.parse.urljoin` 把 `/wiki/...` 拼成完整 URL 再写入 `set`，避免将来混用相对/绝对链接时去重失效。  
2. 用 `urllib.robotparser` 读取 `https://en.wikipedia.org/robots.txt`，思考你的脚本路径是否应被允许（教育用途仍应保守限速）。  
3. 将递归版改为「显式 `deque` + BFS」版，并设置最大深度与最大页面数。
