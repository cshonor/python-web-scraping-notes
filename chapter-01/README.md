# 第 1 章 初见网络爬虫：学习笔记

网络上的一切抓取，本质上都是**「模拟浏览器发一次 HTTP 请求 → 拿回 HTML 源码 → 从源码里抠出要的东西」**。本章把这条最小的闭环跑通：用标准库 `urllib` 发请求，用 `BeautifulSoup` 解析，再把「请求会失败、标签可能不存在」这两件事处理掉。后面 17 章的所有能力 —— Session 保持、表单提交、Scrapy 框架、JS 渲染、并发抓取 —— 都是在这个闭环上逐层加东西；把本章的「请求 / 解析 / 异常」三段式吃透，后面每一章都只是它的变体。

**本章目标**

1. 理解爬虫最基础的工作原理（请求 → 响应 → 解析）
2. 看懂一次 HTTP 请求的最小结构，知道程序到底「发」了什么出去
3. 会用 `urllib` 与 `requests` 两条路线发请求、抓取网页
4. 会用 BeautifulSoup 把 HTML 文本变成可遍历的对象树
5. 写出**稳定、带异常处理**的爬虫代码

---

## 1. 核心知识点与原理

### 1.1 爬虫的四步闭环

1. **发送请求**（Python 程序 → 服务器）：程序扮演浏览器的角色，向目标 URL 发起一次 HTTP GET。
2. **服务器返回 HTML 源码**：响应体是一串字节流，解码后就是浏览器「查看源代码」看到的那份文本。
3. **解析源码**：用 BeautifulSoup 把文本解析成标签树，按标签名、属性、层级取出标题、正文、链接。
4. **不会自动加载图片、CSS、JS**：只拿到本次请求返回的那一份 HTML 文本；要图片就再发一次请求去拉。

这四步里，前两步归「网络层」（`urllib` / `requests` 负责），后两步归「解析层」（BeautifulSoup 负责）。本章五个脚本无论如何变化，拆开看都是这两层的不同组合。

### 1.2 HTTP 请求的最小解剖

「发请求」不是一句空话。一次 HTTP GET 在 wire 上长这样：

```text
GET /pages/page1.html HTTP/1.1      <- 请求行：方法 + 路径 + 协议版本
Host: www.pythonscraping.com        <- 请求头：一堆 key: value
User-Agent: Chapter01GetTitle/1.0
Accept: */*
                                     <- 空行
(请求体：GET 通常为空)
```

服务器回包同样三段式：**状态行**（`HTTP/1.1 200 OK`）、**响应头**（`Content-Type: text/html` 等）、**响应体**（真正的 HTML 字节）。爬虫代码里能摸到的东西一一对应：`response.status_code` 来自状态行，`response.headers` 来自响应头，`html.read()` / `response.text` 来自响应体。理解这一点后，「为什么 404 要单独处理」「为什么 UA 写在 headers 里」就不再是死记硬背的规则。

### 1.3 urllib 与 requests：两条路线的选择时机

本章刻意并列了两种发请求的写法，它们不是新旧替代关系，而是各有适用面：

| 维度 | `urllib`（标准库） | `requests`（第三方） |
|---|---|---|
| 安装 | 零依赖，开箱即用 | `pip install requests` |
| 异常体系 | `HTTPError` / `URLError` 分开捕获 | 统一 `RequestException` 兜底 |
| 状态码处理 | 4xx/5xx 直接抛 `HTTPError` | 默认不抛，需手动 `raise_for_status()` |
| 读响应 | `urlopen(...).read()` 拿字节 | `response.text`（自动猜编码）/ `.content`（字节） |
| 高级能力 | Cookie、重定向要自己拼 handler | Session、表单、文件上传开箱即用 |
| 本章脚本 | `get_title.py`、`get_title_urllib.py` | `get_example.py`、`bs4_example.py`、`safe_get.py` |

**选择建议**：写一次性小工具、不想引依赖时用 `urllib`；要写多步交互（登录、翻页、保持 Cookie）或需要可读性时上 `requests`。第 4 章以后仓库基本全面转向 `requests`，原因就是 Session 与表单能力在标准库里要自己造轮子。

### 1.4 两个必备库的分工

| 库 | 来源 | 作用 |
|---|---|---|
| **`urllib`** | Python **标准库**，无需安装 | 打开网页、获取 HTML 内容（常用 `urllib.request.urlopen`） |
| **`BeautifulSoup4`** | 第三方库，需安装 | 把杂乱的 HTML 变成结构化对象，便于按标签/属性提取 |

```bash
pip install beautifulsoup4
```

注意导入名是 `bs4`（`from bs4 import BeautifulSoup`），安装名是 `beautifulsoup4`，两者不一致是新手第一个坎。

### 1.5 HTML 解析器：三选一

创建 `BeautifulSoup` 时最好显式指定解析器，否则会收到警告并按默认行为处理：

| 解析器 | 安装 | 特点 |
|---|---|---|
| **`html.parser`** | 自带 | 稳定、够用，**入门推荐** |
| **`lxml`** | `pip install lxml` | 速度快，容错一般 |
| **`html5lib`** | `pip install html5lib` | 容错最强，速度最慢 |

同一份 HTML 用不同解析器，补全出来的树结构可能有细微差别 —— 缺失的 `<tbody>` 补不补、属性大小写归不归一，各解析器策略不同 —— 所以「换解析器后选择器失效」是正常的，不是你的 bug。本章脚本里两种都有实例：`get_title.py` 用 `html.parser`，`bs4_example.py` 用 `lxml`（本机环境已装，实测可跑）。

### 1.6 不自动加载图片 / JS：第 11 章的伏笔

第 1.1 节第 4 点是最容易误解的地方，值得单独展开：`urlopen()` 拿到的是**单次响应**的字节流。真实浏览器打开一个页面后会继续发出几十个请求（图片、CSS、字体、JS 文件），最后还要执行 JS 把数据填进 DOM；而爬虫程序对这些后续动作一概不参与，它看到的永远是「第一口」HTML。

这直接埋下两条线索：

- 想要页面上的图片？解析出 `<img src>` 后再发一次请求下载（第 6 章媒体存储正是干这个）。
- 页面数据是 JS 异步渲染的、HTML 里只有空壳？`requests` 无能为力，需要分析 AJAX 接口或上 Selenium —— 这正是**第 11 章**要解决的问题。到那时再回头想「为什么 requests 只看到空壳 HTML」，答案就是本节这一句。

---

## 2. 异常处理与最佳实践（易错点）

请求与解析这两步各有各的崩法，必须分段处理：

| 失败点 | 异常类型 | 典型原因 |
|---|---|---|
| 请求 | **`HTTPError`** | 页面不存在（404）、服务器报错（500） |
| 请求 | **`URLError`** | 连不上、断网、DNS/域名错误、证书问题 |
| 解析 | **`AttributeError`** | `find` 返回 `None`，再链式 `.children` / `.get_text()` |

1. **`find` 结果先判空再取值**。现象：页面改版或抓错页面后，`bs.find("h1")` 返回 `None`，紧接着 `.get_text()` 抛出 `AttributeError: 'NoneType' object has no attribute 'get_text'`，traceback 指向的却是取值那行而不是查找那行，极具迷惑性。原因：`find` / 链式属性访问在找不到时不会抛错，而是安静返回 `None`。对策：`if h1_tag:` 之后再取值，或像 `get_title_urllib.py` 那样把整段解析包进 `try ... except AttributeError`。这是全仓 18 章反复出现的一条。

2. **请求必须带 `timeout`**。现象：脚本卡在 `urlopen` / `requests.get` 上一动不动，Ctrl+C 才能退出。原因：网络对端接受连接后不响应，TCP 层面没有默认超时，Python 会一直等。对策：所有请求显式传 `timeout=15`（本章脚本全部如此）；批量抓取时宁可失败重试，也不要无限等待。

3. **请求必须带可识别的 `User-Agent`**。现象：同一个 URL 浏览器能开、脚本却拿到 403，或者拿到一份内容完全不同的「假页面」。原因：裸 `urlopen` 的默认 UA（`Python-urllib/3.x`）在大量站点的拦截名单上。对策：用 `Request(url, headers={"User-Agent": "..."})` 或 `requests.get(url, headers=...)` 带上有辨识度的 UA；`get_title.py` 的 `Chapter01GetTitle/1.0 (educational)` 就是合规范例 —— 写明身份与用途，而不是伪装成浏览器。

4. **混淆 `HTTPError` 与 `URLError` 的覆盖范围**。现象：明明只捕获了 `URLError`，404 时程序还是崩了。原因：`HTTPError` 是 `URLError` 的子类但语义不同 —— 前者表示「连上了，服务器拒绝」，后者表示「根本没连上」。对策：两个都列进 `except` 元组（`except (HTTPError, URLError, OSError)`），需要区分处理时把 `HTTPError` 写在前面（子类先捕获）。

5. **`raise_for_status()` 不是默认行为**。现象：用 `requests` 抓一个不存在的路径，程序不报错，继续把 404 的错误页 HTML 当正常数据解析，产出莫名其妙的「脏数据」。原因：`requests.get` 对 4xx/5xx **不会**自动抛异常，这与 `urllib` 的行为相反。对策：像 `safe_get.py` 与 `bs4_example.py` 那样，拿到响应后立刻 `response.raise_for_status()`，让错误在请求层暴露，别流到解析层。

6. **异常处理别包太大**。现象：把整个函数体塞进一个 `try`，出了错不知道是哪一步挂的。对策：本章脚本的标准分段是「请求一个 try、解析一个 try」—— `get_title_urllib.py` 里网络异常打印 `网络连接异常`、解析异常打印 `标签解析异常`，定位一眼即明；外层用返回 `None` 表示失败，由调用方决定是跳过还是终止。

工程上的三条硬要求汇总：**判空、超时、UA**。新写一个爬虫脚本时先检查这三项，再谈别的。

---

## 3. 示例代码

五个脚本按「稳健 urllib → 书中风格 urllib → requests 最简 → requests + bs4 → requests 安全封装」的路线排列。全部已在本地用 Python（requests / bs4 / lxml 已装）实际运行验证，以下为 2026-11-02 的真实输出。

### 3.1 `get_title.py`：主示例，urllib + bs4 稳健取 h1

本章主示例。网络层用 `Request` 带自定义 `User-Agent` 与 `timeout=15`，异常一次性捕获 `HTTPError / URLError / OSError`；解析层用 `html.parser` 建树后 `find("h1")`，**判空再取文本**，页面没有 h1 时返回说明性字符串而不是 `None`。主流程准备了 `https` 与 `http` 两条 URL，第一条成功即 `break`，演示了「失败后换地址重试」的最简形态。

```python
req = Request(url, headers={"User-Agent": "Chapter01GetTitle/1.0 (educational)"})
html = urlopen(req, timeout=15)
...
bs = BeautifulSoup(html.read(), "html.parser")
h1_tag = bs.find("h1")
if h1_tag:
    return h1_tag.get_text(strip=True)
return "页面没有 h1 标签"
```

运行：

```bash
cd chapter-01
pip install -r requirements.txt
python3 get_title.py
```

实测输出（2026-11-02）：

```text
网页 H1 标题： An Interesting Title
```

### 3.2 `get_title_urllib.py`：书中风格的 getTitle 函数

与主示例同源但风格不同：函数名用书中惯用的 `getTitle`，异常处理分两段 —— 请求段只捕获 `HTTPError / URLError`，解析段专门捕获 `AttributeError`（应对 `bs.body.h1` 链式访问中任一环节为 `None` 的情况）。注意它返回的是**标签对象本身**而不是文本，所以调用方拿到的是带尖括号的完整 `<h1>` 节点；也没有自定义 UA，是五个脚本里最「裸」的一个，适合用来对比 UA 与分段异常的价值。

```python
try:
    html = urlopen(url, timeout=15)
except (HTTPError, URLError) as e:
    print(f"网络连接异常: {e}")
    return None
try:
    bs = BeautifulSoup(html.read(), "html.parser")
    title = bs.body.h1
except AttributeError as e:
    print(f"标签解析异常: {e}")
    return None
```

```bash
python3 get_title_urllib.py
```

实测输出（2026-11-02）：

```text
网页标题为: <h1>An Interesting Title</h1>
```

### 3.3 `get_example.py`：requests 最简 GET

requests 路线的「Hello World」：三行核心代码完成「GET → 看状态码 → 看内容前 500 字符」。它刻意不做任何异常处理，目的是让你看清 `requests.get` 的默认行为 —— 返回的 `response` 对象上 `status_code` 与 `text` 随手可取，且**状态码非 200 也不抛异常**。把它和 3.5 的 `safe_get.py` 对照读，就能理解 `raise_for_status()` 到底补上了哪块空白。

```python
url = "https://example.com"
response = requests.get(url, timeout=15)
print(f"状态码: {response.status_code}")
print(response.text[:500])
```

```bash
python3 get_example.py
```

实测输出（2026-11-02，截取首尾）：

```text
状态码: 200
响应内容前500字符:
<!doctype html><html lang=en><head><meta charset=utf-8>...<title>Example Domain</title>...
```

### 3.4 `bs4_example.py`：requests + BeautifulSoup 完整链路

「请求 → 校验状态 → 解析 → 取多个标签」的完整最小闭环。请求后先 `raise_for_status()` 把 4xx/5xx 挡在解析之外；解析器用的是 **`lxml`**（本机已装，没装的话换成 `html.parser` 即可）。提取部分演示了两种姿势：`soup.title` 直接属性访问取单个标签（并双重判空：标签存在且 `.string` 非空），`soup.find_all("p")` 循环取全部段落文本 —— 后者是后续章节批量抓取的雏形。

```python
response = requests.get(url, timeout=15)
response.raise_for_status()
soup = BeautifulSoup(response.text, "lxml")
title_tag = soup.title
if title_tag and title_tag.string:
    print("网页标题:", title_tag.string.strip())
for p in soup.find_all("p"):
    print(p.get_text(strip=True))
```

```bash
python3 bs4_example.py
```

实测输出（2026-11-02）：

```text
网页标题: Example Domain
This domain is for use in documentation examples without needing permission. This is not a service; avoid relying on it for testing and monitoring purposes.
```

### 3.5 `safe_get.py`：requests 异常的最小封装

把「发请求 + 校验状态 + 捕获异常」收敛成一个可复用函数 `safe_get_url`：成功返回 HTML 文本，任何环节失败（连接超时、DNS、404、500……）都由 `requests.exceptions.RequestException` 这个**公共基类**一网打尽，打印原因后返回 `None`。调用方只需判断返回值真假，不必关心异常类型。这个「函数内部消化异常、对外只给 None/结果」的模式，是后面多页抓取循环里「单页失败不中断」的标准写法。

```python
def safe_get_url(url: str, timeout: float = 10) -> str | None:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except RequestException as e:
        print(f"请求出错: {e}")
        return None
```

```bash
python3 safe_get.py
```

实测输出（2026-11-02）：

```text
获取成功，长度: 577
```

---

## 4. 学习贴士

- **解析器选择不是性能问题，是兼容问题**。先用 `html.parser` 把逻辑跑通，等真的遇到畸形 HTML 再换 `html5lib`；追求速度才换 `lxml`。入门阶段三个解析器的速度差根本感知不到。
- **`https` 失败回退 `http` 只适合教学演示**。`get_title.py` 里之所以写了两条 URL，是因为个别网络环境下 TLS 握手会被拦；生产代码应当去修证书/代理，而不是降级到明文 —— 明文 HTTP 意味着内容可被中间人篡改。
- **`strip=True` 很关键**：不加的话 `get_text()` 会把标签间的换行和缩进一起带出来，后续做字符串匹配会莫名失败。养成「取文本必 strip」的肌肉记忆。
- **先跑通再加固**。学习顺序建议：先跑 `get_example.py` 感受 requests 的直白，再跑 `get_title.py` 理解为什么要加异常分支，最后自己给 `get_example.py` 补上 `try/except` 并和 `safe_get.py` 对照 —— 亲手踩一遍坑比直接抄稳健版印象深刻得多。
- **打印中间结果是最好的调试器**。`status_code`、`len(response.text)`、`bs.find("h1") is None`，这三个值打印出来，90% 的「抓取失败」能在一分钟内定位到是网络层还是解析层的问题。

---

## 5. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-01/get_title.py` | 本章主示例：`urllib` + bs4，带 UA / timeout / 完整异常分支（已实测） |
| `chapter-01/get_title_urllib.py` | 书中风格 `getTitle`：`bs.body.h1` 链式取值 + 分段异常（已实测） |
| `chapter-01/get_example.py` | `requests` 最简 GET，只打印状态码与前 500 字符（已实测） |
| `chapter-01/bs4_example.py` | `requests` + BeautifulSoup（lxml），`raise_for_status` + `find_all`（已实测） |
| `chapter-01/safe_get.py` | `requests` 与 `RequestException` 的最小封装（已实测） |
| `chapter-01/requirements.txt` | 本章依赖：`requests>=2.31.0`、`beautifulsoup4>=4.12.0`（`lxml` 为可选解析器） |

本章是「单页抓取」的原点：第 2 章开始在同一份 HTML 上玩更复杂的定位（属性、正则、Lambda），第 3 章开始从单页走向多页遍历，第 11 章则回来解决本章 1.6 节埋下的「JS 渲染空壳」问题。

---

## 练习建议

1. 依次运行五个脚本，确认都能输出预期结果；再把 `bs4_example.py` 的解析器从 `lxml` 换成 `html.parser`，对比输出是否一致。
2. 故意把 `get_title.py` 的域名写错（如 `www.pythonscraping.example`）、路径写错（如 `/pages/nope.html`），分别观察 `URLError` 与 `HTTPError` 的提示差异。
3. 把 `get_example.py` 改造成循环抓 5 个 URL（可混入一个 404 地址），要求任一失败都不中断 —— 完成后与 `safe_get.py` 对照自己的封装差距。
4. 给 `get_title_urllib.py` 补上自定义 `User-Agent`，并用 `response.getcode()`（urlopen 返回对象的方法）打印状态码，体会 urllib 与 requests 在状态码处理上的差异。
5. 修改 `bs4_example.py`，把抓到的所有 `<p>` 文本写入一个本地 `output.txt`（每段一行），为第 6 章「存储数据」热身。
