# 第 1 章 初见网络爬虫：学习笔记

网络上的一切抓取，本质上都是**「模拟浏览器发一次 HTTP 请求 → 拿回 HTML 源码 → 从源码里抠出要的东西」**。本章把这条最小的闭环跑通：用标准库 `urllib` 发请求，用 `BeautifulSoup` 解析，再把「请求会失败、标签可能不存在」这两件事处理掉。后面 17 章的所有能力，都是在这个闭环上加东西。

**本章目标**

1. 理解爬虫最基础的工作原理
2. 学会用 Python 发请求、抓取网页
3. 学会用 BeautifulSoup 解析 HTML
4. 写出**稳定、带异常处理**的爬虫代码

---

## 1. 核心知识点与原理

### 1.1 爬虫的四步闭环

1. **发送请求**（Python 程序 → 服务器）
2. **服务器返回 HTML 源码**
3. **解析源码**，取出标题、文本、链接等内容
4. **不会自动加载图片、CSS、JS** —— 只拿到本次请求返回的那一份 HTML 文本；要图片就再发一次请求去拉

第 4 点是最容易误解的地方：`urlopen()` 拿到的是单次响应的字节流，浏览器后续发出的几十个静态资源请求、以及 JS 渲染过程，它一概不参与。这也直接决定了第 11 章「为什么 requests 只看到空壳 HTML」的答案。

### 1.2 两个必备库

| 库 | 来源 | 作用 |
|---|---|---|
| **`urllib`** | Python **标准库**，无需安装 | 打开网页、获取 HTML 内容（常用 `urllib.request.urlopen`） |
| **`BeautifulSoup4`** | 第三方库，需安装 | 把杂乱的 HTML 变成结构化对象，便于按标签/属性提取 |

```bash
pip install beautifulsoup4
```

### 1.3 HTML 解析器：三选一

创建 `BeautifulSoup` 时必须显式指定解析器，否则会拿到 warning 并按默认行为处理：

| 解析器 | 安装 | 特点 |
|---|---|---|
| **`html.parser`** | 自带 | 稳定、够用，**入门推荐** |
| **`lxml`** | `pip install lxml` | 速度快，容错一般 |
| **`html5lib`** | `pip install html5lib` | 容错最强，速度最慢 |

同一份 HTML 用不同解析器，补全出来的树结构可能有细微差别 —— 所以「换解析器后选择器失效」是正常的，不是你的 bug。

---

## 2. 异常处理与最佳实践（易错点）

请求与解析这两步各有各的崩法，必须分段处理：

| 失败点 | 异常类型 | 典型原因 |
|---|---|---|
| 请求 | **`HTTPError`** | 页面不存在（404）、服务器报错（500） |
| 请求 | **`URLError`** | 连不上、断网、DNS/域名错误、证书问题 |
| 解析 | **`AttributeError`** | `find` 返回 `None`，再链式 `.children` / `.get_text()` |

工程上的三条硬要求：

1. **`find` 结果先判空再取值** —— `if h1_tag:` 之后才 `.get_text()`，这是全仓 18 章反复出现的一条。
2. **请求必须带 `timeout`** —— 否则一个不响应的站点能把脚本永久挂住。
3. **请求必须带可识别的 `User-Agent`** —— 裸 `urlopen` 的默认 UA 会被大量站点直接拒绝（403）或投毒返回假页面。

---

## 3. 示例代码

主示例：**`chapter-01/get_title.py`** —— 网络异常 + 解析后安全取 `h1`；请求带 `User-Agent` 与 `timeout`，减少被站点直接拒绝或长时间卡住。

```python
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


def get_h1_text(url: str):
    try:
        req = Request(url, headers={"User-Agent": "Chapter01GetTitle/1.0 (educational)"})
        html = urlopen(req, timeout=15)
    except (HTTPError, URLError, OSError) as e:
        print(f"访问失败：{e}")
        return None

    bs = BeautifulSoup(html.read(), "html.parser")
    h1_tag = bs.find("h1")
    if h1_tag:
        return h1_tag.get_text(strip=True)
    return "页面没有 h1 标签"


if __name__ == "__main__":
    for demo_url in (
        "https://www.pythonscraping.com/pages/page1.html",
        "http://www.pythonscraping.com/pages/page1.html",
    ):
        result = get_h1_text(demo_url)
        if result is not None:
            print("网页 H1 标题：", result)
            break
```

运行：

```bash
cd chapter-01
pip install -r requirements.txt
python3 get_title.py
```

实测输出（2026-11 复核）：

```text
网页 H1 标题： An Interesting Title
```

---

## 4. 学习贴士

- **解析器选择不是性能问题，是兼容问题**。先用 `html.parser` 把逻辑跑通，等真的遇到畸形 HTML 再换 `html5lib`；追求速度才换 `lxml`。
- **`https` 失败回退 `http` 只适合教学演示**。示例里之所以写了两条 URL，是因为个别网络环境下 TLS 握手会被拦；生产代码应当去修证书/代理，而不是降级到明文。
- **`strip=True` 很关键**：不加的话 `get_text()` 会把标签间的换行和缩进一起带出来，后续做字符串匹配会莫名失败。

---

## 5. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `get_title.py` | 本章主示例：`urllib` + bs4，含完整异常分支 |
| `get_title_urllib.py` | 书中风格 `getTitle` + `body.h1` 与异常分支 |
| `get_example.py` | `requests` 最简 GET，只打印状态码与前 500 字符 |
| `bs4_example.py` | `requests` + BeautifulSoup，抓 `example.com` 标题 |
| `safe_get.py` | `requests` 与 `RequestException` 的最小封装 |

依赖见同目录 `requirements.txt`（`lxml` 为可选解析器）。

---

## 练习建议

1. 运行 `get_title.py`，确认能输出标题。
2. 故意写错域名或路径，分别观察 `URLError` 与 `HTTPError` 的提示差异。
3. 把解析器换成 **`lxml`**（需安装），对比速度与输出是否一致。
4. 把 `get_example.py` 改成循环抓 5 个 URL，任一个失败都不中断。
