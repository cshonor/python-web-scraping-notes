# 第 4 章 网络爬虫模型：学习笔记

第 3 章的爬虫只能爬维基 —— 把站点名、`/wiki/` 前缀、`#bodyContent` 全写死在代码里了。多来两个站，就变成三个互相分叉的脚本，改一处忘两处。本章做的是**把「去哪取」和「怎么取」拆开**：解析规则变成配置，引擎只写一遍，新增站点只是多加一个配置对象。这套 **`Content` + `Website` + `Crawler`** 三层模型是后面所有工程化内容的地基：第 5 章 Scrapy 的 `Spider` + `Rule` 是它的框架版，第 6 章的存储落地消费的是它产出的统一字段。

**本章目标**

1. 编写**可复用、可扩展、跨网站**的通用爬虫思路
2. 理解 **数据模型 + 配置分离**：解析规则不进业务硬编码
3. 使用 **`Website` + `Crawler` + `Content`** 三层分工
4. **一套解析流程**适配多站：改配置为主、改引擎为辅
5. 避免「一站一脚本」导致的重复与分叉维护

---

## 1. 核心知识点与原理

### 1.1 三层模型与调用关系

把爬虫拆成三块，各管一件事：

| 部分 | 职责 | 变化频率 |
|---|---|---|
| **`Content`（数据模型）** | 统一存放结果：URL、标题、正文等 | 最低 —— 下游全靠它稳定 |
| **`Website`（配置模型）** | 每站的 **CSS 选择器**、名称、根 URL 等「抓取指令」 | 最高 —— 每加一个站多一个实例 |
| **`Crawler`（引擎）** | 请求、按 `Website` 抽取、组装为 `Content` | 中 —— 只随通用需求（限速、重试）演进 |

一次抓取的完整调用链：

```text
main
 └─ Crawler.parse(website, url)
     ├─ Crawler.get_page(url)          # Session 请求 + 重试 + 限速 → BeautifulSoup | None
     ├─ Crawler.safe_get(soup, sel)    # 标题/正文各调一次，永不抛异常
     ├─ Content(url, title, body)      # 组装统一数据模型
     └─ content.display()              # 打印摘要
```

关键洞察：**调用方向是单向的** —— `Crawler` 知道 `Website` 和 `Content`，反过来都不知道。`Website` 是纯数据，`Content` 也是纯数据，两者之间没有引用，这正是「配置可以随便换、引擎可以随便改」的结构前提。

### 1.2 三大核心类的生命周期

1. **`Website`**：出生即冻结。构造时收 `name / url / title_selector / body_selector` 四个字符串，之后只读不改。它描述的是「**去哪取**」：标题在 `h1`、正文在 `div.article p`。站点改版时优先改**配置**（换选择器字符串），而不是复制整段爬虫逻辑。一个 `Website` 实例可以被无数个 `parse` 调用复用。
2. **`Crawler`**：长生命周期。构造时建 `requests.Session()`、写入 User-Agent、记下 `delay_sec` 和 `timeout`，之后反复处理不同站点、不同 URL。Session 里的连接池和 Cookie 随实例一直存活，所以**一个任务一个 Crawler**，不要每抓一页 new 一个。
3. **`Content`**：短生命周期、不可变事实。各站最终都落到**同一字段集合**（`url / title / body`），便于入库、对比、分析。它是三层里最不该变的一层 —— 下游的存储、统计、管道全靠它稳定。产出一个 `Content` 就意味着「这一页抓完了」，接下来是 `display` 展示或 `save_to_txt` 落盘。

### 1.3 安全提取：`safe_get` 的防御设计

`safe_get(soup, selector)` 是整个模型的安全气囊，三层防御缺一不可：

| 防线 | 触发条件 | 行为 |
|---|---|---|
| 1. `if not soup` | `get_page` 失败返回 `None` | 返回 `""`，不碰 `None` 的方法 |
| 2. `if not elements` | 选择器无匹配（站点改版/写错） | 返回 `""`，不做空迭代 |
| 3. `"\n".join(...)` | 多节点命中（如多个 `<p>`） | 逐段 `get_text(strip=True)` 后换行合并 |

设计上它是**永不抛异常**的纯函数：配置错了、网络断了、页面结构变了，结果都只是空字符串，由上层（`parse` 里的 `if not title or not body`）决定要不要报警。这与第 2 章「先判断再 `.`」一脉相承，是稳健爬虫的标配。代价要清楚：`safe_get` 无法区分「这个页面本来就没有正文」和「选择器失效了」，所以上层必须对空结果打日志，否则错误会静默累积。

### 1.4 CSS 选择器进阶

配置化的前提是选择器能用**一个字符串**表达足够复杂的定位 —— 这正是 `select` 相对 `find` / `find_all` 的优势：表达力更强、配置更短，且天然可序列化。本章用到的层级：

| 写法 | 含义 | 本章出处 |
|---|---|---|
| `h1` | 标签选择器 | 离线演示的标题 |
| `div.article p` | 后代组合：`.article` 里的所有 `<p>` | 离线演示的正文 |
| `"h1, title"` | **逗号组**：任一命中即返回，按文档顺序排列 | example.com 的标题 |
| `tr:nth-child(2)` | 结构伪类：父元素下第 2 个 `<tr>` | 进阶可用（本章未用） |

三条使用心得：后代选择器比一长串 class 更耐改版（中间层 class 变了也不影响）；逗号组是「多版本页面兼容」的杀手锏，一个字符串同时兜住新旧两版结构；`nth-child` 这类位置伪类最脆弱，页面加一个广告位就错位，只在结构极稳的页面用。浏览器 F12 里 `$$("选择器")` 可以即写即验，校对好再抄进 `Website`。

### 1.5 Session、限速与重试的实现细节

`Crawler.__init__` 里做三件事，每件都有讲究：

- **`requests.Session()`**：复用 TCP 连接（Keep-Alive）与 Cookie，比每次 `requests.get` 省一次握手；UA 在构造时写进 `session.headers`，之后每个请求自动携带，不会漏。
- **`time.sleep(delay_sec)` 放在成功之后**：`get_page` 里先 `raise_for_status()` 再 sleep —— 失败请求走重试分支的独立节奏，不会被礼貌延迟拖累；成功路径才「等一等再走下一页」。
- **重试节奏 `0.35 * (attempt + 1)`**：最多 3 次，失败后分别等 0.35s、0.70s、1.05s，线性退避。偶发断连通常在第一次重试就恢复；三次全挂说明不是抖动，打印 `请求失败: ...` 返回 `None`，把决定权交给上层。

只捕获 `requests.exceptions.RequestException`（连接错误、超时、HTTP 错误状态的公共父类），解析错误不在此列 —— 那是配置问题，重试无意义。

两个容易忽略的细节：`timeout=15` 是**单次请求**的超时，重试 3 次的最坏耗时是 `15*3 + 0.35 + 0.70 + 1.05 ≈ 47 秒`，批量任务要据此估算上限；`raise_for_status()` 把 4xx/5xx 也纳入重试，这对 503 这类临时过载是合理的，但对 404/403 是白费三次 —— 生产代码里应按状态码分流，教学代码为简洁做了合并。

### 1.6 `parse_from_soup` 与可测试性

`parse_from_soup(website, url, soup)` 与 `parse` 只差第一步：不发起网络请求，直接对传入的 `BeautifulSoup` 做 `safe_get` 抽取。这一刀切开了「取页面」和「解析页面」，价值在测试：

- **离线 fixture**：把目标页 HTML 存成本地文件，构造 soup 直接测解析逻辑，CI 上无网也能跑。
- **回归测试**：站点改版前先存一份旧版 HTML，改完选择器跑一遍，确认旧 fixture 抽不出、新 fixture 抽得出。
- **调试隔离**：解析出错时先存盘复现，排除网络变量，问题立刻缩小到选择器本身。

真正的工程化标志不是「能跑」，是「不联网也能测」。`main` 里的离线演示段就是最小示范：一段字符串 HTML + 一个 `Website` 配置，全程零请求。

与 `parse` 对比着记两者的分工：

| 维度 | `parse` | `parse_from_soup` |
|---|---|---|
| 网络请求 | 有（`get_page`，含重试限速） | 无 |
| 输入 | URL | URL + 现成的 `BeautifulSoup` |
| 典型场景 | 生产抓取 | 单测、离线 fixture、调试复现 |
| 解析半段 | `safe_get` × 2 + 空值检查 | 完全相同 |

解析半段一字不差是刻意为之：离线测试通过的逻辑，上线跑的就是同一份代码，不存在「测试版」和「生产版」两套解析分叉。

---

## 2. 异常处理与最佳实践（易错点）

1. **配置与代码搅在一起，换站就要动引擎**。这是本章要解决的头号问题：选择器写死在 `parse` 函数里，加第二个站就得复制整份脚本再改几行，两份代码从此各自漂移，修 bug 修一处忘一处。判断标准很直接 —— 新增站点如果只该改一个配置文件，你的代码里却动了引擎，说明抽象漏了。本章的答案是让选择器成为 `Website` 的构造参数，引擎里一个具体字符串都不出现。

2. **不做安全抽取，选择器失效即崩**。裸写 `soup.select_one("h1").get_text()` 的脚本，站点一改版就是 `AttributeError: 'NoneType' object has no attribute 'get_text'`，而且往往在凌晨的定时任务里爆。`safe_get` 把「查无此节点」从异常降级为空字符串，配合上层的空值检查打日志，故障从「程序崩溃」变成「一条可追踪的告警」，排查成本低一个数量级。

3. **各站字段不一致，下游无法统一分析**。A 站存 `{headline, text}`，B 站存 `{title, paragraphs}`，写到同一个 CSV 就傻眼了。`Content` 的价值正在于强制对齐：所有站点的产出都必须能塞进 `url / title / body` 三个字段，塞不进就说明该站需要单独的清洗逻辑 —— 但那也应该是「清洗后仍产出 `Content`」，而不是发明第五种字段名。

4. **`parse(site, url)` 传错参数**。第二个参数必须是**当前要抓的页面 URL**（字符串），不是把 `Website` 列表或站点根 URL 当参数糊进去。`Website.url` 只是站点的入口/标识，真正抓哪页由调用方决定 —— 同一个 `Website` 配置要服务该站下的成千上万篇文章页。概念上记牢：**`Website` 是规则，`url` 是这次要处理的目标**。

5. **迷信线上示例的选择器长期有效**。新闻站改版最快，书中 Reuters / NYTimes 等的 class 名**很可能早已变化**，照抄必抽不到。正确姿势永远是打开浏览器开发者工具，用 `$$("选择器")` 在实况页面上验证后再写进配置。本章 example.com 的例子（见 §3）就是一次真实的「站点变了、配置跟着变」。

6. **把限速放在错误的位置**。在循环里「每抓一页 sleep 一次」看似礼貌，但如果 sleep 放在请求之前或失败分支里，重试会被拖成几分钟，超时排查时你会分不清是网络慢还是自己睡多了。本章的做法是**成功响应之后才 sleep**，失败重试走独立的短退避 —— 礼貌给站点，效率留给自己。

7. **以为配置化能免于改版**。要正面理解：**配置化并不能让你免于改版，只是把「改版」的代价从「改引擎 + 重测所有站」降到「改一个字符串」**。选择器仍然是会过期的外部依赖，长期项目需要配合 §1.6 的离线 fixture 做回归，改版发生时第一时间知道「哪个站的哪个字段抽空了」。

---

## 3. 示例代码

主示例：**`chapter-04/crawler_model.py`**（160 行，requests + BeautifulSoup，依赖见同目录 `requirements.txt`）。下面按类逐块走读，所有行为描述均与源码逐函数核对；文末附 2026-11-02 的真实运行输出。

```bash
cd chapter-04
pip install -r requirements.txt
python3 crawler_model.py
```

**运行前建议**：把脚本里的 **`DEFAULT_UA`** / `mailto:you@example.com` 改成你自己的标识与联系方式（礼貌抓取，也让对方站点能联系到你）。

### 3.1 `Content`：统一数据模型与落盘

`__init__` 只收 `url / title / body` 三个字符串，纯数据、零逻辑 —— 连默认值都没给，强迫上游把三个字段凑齐才许构造，空值问题在 `parse` 里就被拦下，不会带进 `Content`。两个方法各有细节：

**`display(body_preview=120)`** —— 打印摘要，避免长正文刷屏。注意方法**不能叫 `print`**（会遮蔽内建函数）。截断逻辑：正文超过 120 字符时取前 120 字加省略号 `…`，正文为空串时预览也是空串。输出用 `"=" * 50` 分隔线包夹，多页连抓时一眼分清边界。

**`save_to_txt(directory=".")`** —— 写入 UTF-8 文本，返回 `Path`。路径处理是本节最密的细节：

```python
d = Path(directory)
d.mkdir(parents=True, exist_ok=True)
stem = re.sub(r"[^\w\-.]+", "_", self.title.strip())[:80] or "untitled"
path = d / f"{stem}.txt"
```

- `mkdir(parents=True, exist_ok=True)`：目录不存在则连带父级创建，已存在不报错 —— 幂等，可反复调用。
- 文件名由标题派生：正则把**非**字母数字下划线连字符点号的字符全部替换为 `_`（中文按 `\w` 保留），再截断到 80 字符；标题清洗后为空则回退 `untitled`，避免写出 `.txt` 这种无名词。
- 文件体固定四段：`URL:`、空行、`标题:`、空行、`正文:` —— 人可读，也好被简单脚本二次解析。

### 3.2 `Website`：纯配置对象

四个字段（`name / url / title_selector / body_selector`），没有任何方法。它是**值对象**：构造完就不再变，可以被任意多个 `Crawler` 的任意多次调用共享。新增一个站点 = new 一个 `Website`，引擎代码一行不动 —— 这就是本章标题「爬虫模型」的全部含义。

### 3.3 `Crawler`：引擎的实现细节

**`__init__(delay_sec=0.5, timeout=15, user_agent=DEFAULT_UA)`**：建 `Session`，UA 写入 `session.headers["User-Agent"]`（后续请求自动携带），`delay_sec` 与 `timeout` 存为实例属性。默认延迟 0.5 秒、超时 15 秒是教学级稳妥值。

**`get_page(url)`** —— 请求 + 重试 + 限速，返回 `BeautifulSoup | None`：

```python
for attempt in range(3):
    try:
        resp = self._session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        if self.delay_sec > 0:
            time.sleep(self.delay_sec)
        return BeautifulSoup(resp.text, "html.parser")
    except requests.exceptions.RequestException as e:
        last_err = e
        time.sleep(0.35 * (attempt + 1))
print(f"请求失败: {last_err}")
return None
```

逐行核对要点：重试上限 **3 次**；**先 `raise_for_status()` 后 sleep**（限速只在成功路径生效，`delay_sec <= 0` 可整体关闭）；失败退避为 **0.35s → 0.70s → 1.05s** 的线性节奏；三次全败打印最后一次异常并返回 `None`。解析器用标准库 `html.parser`，零额外依赖。

**`safe_get(soup, selector)`**：§1.3 的三层防御逐条对应源码 —— `if not soup: return ""`、`if not elements: return ""`、`"\n".join(e.get_text(strip=True) for e in elements)`。注意它对**所有命中节点**取文本并换行合并，所以正文选择器 `div.article p` 命中两段 `<p>` 时，得到的是两行文本而不是只取第一段。

**`parse(website, url)`**：`get_page` 失败直接返回 `None`；`safe_get` 抽标题和正文，**任一为空**打印 `标题或正文为空（请检查选择器）: 站点名 -> URL` 并返回 `None`；都拿到才组装 `Content`、`display()` 并返回。空值检查放在这里而不是 `safe_get` 内部，是因为「空」是否算错误是业务决策，引擎只负责报告。

**`parse_from_soup(website, url, soup)`**：除不联网外与 `parse` 完全同构（同样做空值检查、同样 `display`），用途见 §1.6。两个方法的解析半段保持一致是刻意设计 —— 离线测的就是在线跑的同一份逻辑。

### 3.4 `main`：离线 + 在线两段式演示

**离线段**：内嵌一段 6 行 HTML 字符串，配 `Website(name="离线演示", title_selector="h1", body_selector="div.article p")`，走 `parse_from_soup`。全程零网络，验证模型与选择器语法正确 —— 脚本能不能跑通，这一段 1 秒内见分晓。

**在线段**：抓 `https://example.com/`，配置为 `title_selector="h1, title"`、`body_selector="p"`，走完整 `parse`（真实请求 + 0.5s 延迟），成功后 `save_to_txt(Path(__file__).resolve().parent)` 把结果写到脚本同目录。用 `Path(__file__).resolve().parent` 而不是 `"."` 定位，保证从任何工作目录运行，产物都落在脚本旁边 —— 这个写法值得抄进所有会写文件的脚本。

两段之间没有耦合：离线段挂了不影响在线段，在线段没网也不影响离线段的结果 —— 这正是「把不可靠的外部依赖隔离在最后一步」的编排方式。

**逗号选择器的修复记录（保留）**：脚本里 example.com 那段的 `title_selector` 写的是 **`"h1, title"`**，不是单个 `h1` —— 因为 IANA 早年给的 example.com 有 `<h1>Example Domain</h1>`，后来简化成只剩 `<title>`，单写 `h1` 会抽到空串、触发「标题或正文为空」告警。逗号是 **CSS 选择器组**，按文档顺序返回所有命中项，新旧两版页面都能兜住。这正好是 §1.2「改版时改配置、不改引擎」的实例：站点变了，只动了一个字符串。2026-11-02 实测确认：当前 example.com **已无 `<h1>`**，`soup.select("h1, title")` 实际只命中 `<title>` —— 若把选择器改回 `"h1"`，标题必为空。

**实测输出**（2026-11-02，macOS，python3，`requests`/`bs4` 已装，退出码 0）：

```text
开始抓取（含请求间隔 delay_sec）…

==================================================
URL: https://demo.local/news/1
标题: 离线演示标题
正文预览:
第一段。
第二段。
==================================================

==================================================
URL: https://example.com/
标题: Example Domain
正文预览:
This domain is for use in documentation examples without needing permission. This is not a service; avoid relying on it …
==================================================

已保存: .../chapter-04/Example_Domain.txt
```

与源码逐点对得上：离线段正文是两个 `<p>` 经 `"\n".join` 合并的两行；在线段标题来自 `<title>`（逗号组的唯一命中）；正文 180 字符超过 120 上限，预览以 `…` 结尾；落盘文件名由标题 `Example Domain` 清洗为 `Example_Domain.txt`（空格变 `_`），文件共 216 字节，内容为 `URL:` / `标题:` / `正文:` 四段格式。

---

## 4. 学习贴士

- **判断一个爬虫设计好不好，看「加一个站要改几个文件」**。答案应该是 1 个（配置文件），而不是 3 个。任何需要动引擎才能接入的新站点，都说明抽象还没拆干净。
- **`safe_get` 是这套设计的关键零件**。没有它，配置写错就崩；有了它，配置写错只是返回空字符串 —— 前者要紧急修，后者可以慢慢修。防御写在最底层，上层所有代码都受益。
- **`parse_from_soup` 是为了可测试性**。真正的工程化标志不是「能跑」，是「不联网也能测」。养成习惯：每接一个新站，先存一份 HTML fixture，再写选择器。
- **重试和限速是两条独立的时间轴**。礼貌延迟（`delay_sec`）给成功的请求，退避（`0.35*(attempt+1)`）给失败的请求，混在一起必然两头不讨好 —— 要么对站点不礼貌，要么对自己不利索。
- **选择器是配置，不是代码**。写进 `Website` 的字符串应该能放进 JSON/YAML 里不违和；如果你发现自己在选择器里拼接 Python 变量才能定位，说明该站的适配逻辑应该进清洗层，而不是污染配置层。

---

## 5. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-04/crawler_model.py` | 本章唯一示例：三层模型完整实现 + 离线/在线双演示（已实测，退出码 0） |
| `chapter-04/requirements.txt` | 本章依赖：`requests>=2.31.0`、`beautifulsoup4>=4.12.0` |
| `chapter-03/`（维基爬虫） | 本章的「问题来源」：站点信息硬编码的对照组 |
| `chapter-05/`（Scrapy） | 本章思路的框架版：`Spider` + `Rule` ≈ 手写的 `Crawler` + `Website` |
| `chapter-06/`（存储数据） | 本章 `Content` 的下游：CSV / SQLite / MySQL 落地消费的就是 `url / title / body` |

本章只有 `crawler_model.py`，但它同时是第 5 章 Scrapy「配置驱动」思路的手写版对照 —— 看完这章再看 Scrapy 的 `Spider` + `Rule`，会发现后者只是把你手写的这套东西做成了框架。

---

## 练习建议

1. 运行 `crawler_model.py`，确认离线块与 **example.com** 两段都有输出，并核对生成的 `Example_Domain.txt` 四段格式。
2. 新增一个 **`Website`**，自选一篇结构简单的新闻或博客页，用浏览器 F12（`$$("选择器")`）校对 `title_selector` / `body_selector`。
3. 为多条 URL 循环调用 `parse`，适当增大 **`delay_sec`**，观察总耗时与失败率的变化。
4. 只用 **`parse_from_soup`**，用本地保存的 `.html` 做回归测试（完全无需联网）；再故意写错一个选择器，观察「标题或正文为空」告警是否如期出现。
5. 把 example.com 段的 `title_selector` 临时改回 `"h1"` 运行一次，亲手复现 §3.4 的改版故障，再改回 `"h1, title"` 修复 —— 体会「改一个字符串」的代价。
6. 给 `save_to_txt` 设计一个冲突策略：当两篇不同文章清洗出同名文件时（如标题相同），在文件名后追加短哈希或时间戳，避免互相覆盖。
