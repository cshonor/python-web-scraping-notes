# 第 1 章 初见网络爬虫：学习笔记

本章重点介绍了网页抓取的基本原理，即如何从服务器请求信息、对服务器响应进行基本处理，以及如何初步使用 BeautifulSoup 库解析 HTML 内容。

---

## 1. 核心知识点与原理

### 1.1 网络连接原理

网页抓取的过程其实是脱离了浏览器接口的遮挡，直接与网络连接层进行数据交换。其基本过程如下：

1. **发送请求**：客户端（你的 Python 程序）向服务器发送比特流信息，包含请求头（目标 IP 地址、MAC 地址等）和消息体（如 GET 请求的具体文件路径）。
2. **数据传输**：数据包通过中介服务器游历，最终到达目标服务器的特定端口（通常是 80 端口）。
3. **服务器响应**：服务器读取请求，找到对应的 HTML 文件，将其打包成数据包发回客户端。
4. **解析数据**：客户端接收到 HTML 源码。**注意**：Python 程序通常只读取直接请求的单个文件，而不会像浏览器那样自动加载图片、CSS 或 JavaScript 等关联资源。

### 1.2 常用库：urllib 与 BeautifulSoup

- **urllib**：Python 标准库，包含 `urlopen` 函数。它不仅可以读取 HTML 文件，还可以读取图像或任何文件流。
- **BeautifulSoup**：第三方库，通过定位 HTML 标签来格式化和组织复杂的网页信息，将 XML/HTML 结构转化为简单易用的 Python 对象。

### 1.3 HTML 解析器对比

创建一个 `BeautifulSoup` 对象时，需要指定解析器：

- **`html.parser`**：Python 3 自带，无需额外安装，适合基础使用。
- **`lxml`**：需额外安装。优点是解析「杂乱」或有语法错误的 HTML 性能更优，速度更快，但依赖 C 语言库，可移植性稍差。
- **`html5lib`**：容错性极高，甚至能处理语法极其糟糕的 HTML，但速度较慢。

安装示例：

```bash
pip install beautifulsoup4
pip install lxml        # 可选
pip install html5lib    # 可选
```

---

## 2. 异常处理与可靠性（易错点）

网页抓取中最常见的错误在于忽略了网络的不确定性。必须处理以下几类异常以保证爬虫的稳健性：

1. **`HTTPError`**：网页在服务器上不存在或获取出错（如 404、500）。使用 `urllib.request.urlopen` 时可能抛出此异常。
2. **`URLError`**：服务器本身不存在或连接失败。
3. **`AttributeError`**：这是解析时的常见「坑」。如果你尝试调用一个不存在的标签的子标签（即在 `None` 对象上调用属性），程序会崩溃。
   - *例*：`bs.nonExistentTag` 会返回 `None`，但 `bs.nonExistentTag.someChild` 就会抛出 `AttributeError`。

---

## 3. 可直接运行的 Python 示例代码

以下代码整合了本章提到的请求、解析以及**完备的异常处理**逻辑。

仓库内可执行脚本：`code/chapter01/get_title_urllib.py`

```python
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from bs4 import BeautifulSoup


def getTitle(url: str):
    """
    一个稳健的网页标题获取函数
    集成了网络连接异常处理和标签解析异常处理
    """
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

    return title


if __name__ == "__main__":
    target_url = "http://www.pythonscraping.com/pages/page1.html"
    title = getTitle(target_url)
    if title is None:
        print("未能找到标题")
    else:
        print(f"网页标题为: {title}")
```

---

## 4. 学习贴士

- **虚拟环境**：由于 BeautifulSoup 是第三方库，建议使用虚拟环境（如 `venv` / `virtualenv`）来管理项目依赖，避免版本冲突。
- **代码习惯**：编写通用函数（如上面的 `getTitle`）并包含周密的异常处理，会让你的爬虫更加稳定易读。
- **GitHub 参考**：本书配套代码示例可在作者仓库浏览：[REMitchell/python-scraping](https://github.com/REMitchell/python-scraping)。

---

## 5. 与本仓库其他示例（补充）

若你已熟悉 **`requests`**，也可对照阅读 `code/chapter01/get_example.py`、`bs4_example.py`、`safe_get.py`，二者与 `urllib` 路线互补，后续章节中 `requests` 出现频率更高。

## 练习建议

1. 将 `getTitle` 改为返回 `h1` 的纯文本（`get_text(strip=True)`），并处理 `h1` 不存在的情况。  
2. 对 `target_url` 故意写错域名或路径，观察 `HTTPError` / `URLError` 的输出差异。  
3. 尝试把解析器从 `html.parser` 换成 `lxml`（需安装），对比解析同一页是否有差异。
