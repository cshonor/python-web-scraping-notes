# BeautifulSoup 基础

## 何时使用

页面 HTML 在首次响应里已经完整（或主要数据在 HTML 中），用 `requests` 取回文本后，用 BeautifulSoup 做结构化解析即可。

## 安装

```bash
pip install beautifulsoup4 lxml
```

`lxml` 作为解析器通常更快；也可使用内置的 `html.parser`。

## 常用模式

### 创建对象

```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "lxml")
```

### 按标签与属性

```python
soup.find("a", href=True)
soup.find_all("div", class_="item")
```

注意：`class` 在 Python 里是关键字，参数写作 `class_`。

### CSS 选择器

```python
soup.select("article h2")
soup.select_one("#main .title")
```

### 文本与属性

```python
tag.get_text(strip=True)
tag["href"]
```

## 注意点

1. **编码**：若乱码，检查响应 `response.encoding` 或从 `Content-Type` / 页面 `<meta charset>` 推断。
2. **容错**：`find` 可能为 `None`，访问子节点前先判断。
3. **反爬**：仅换解析器无法绕过封 IP、验证码、登录态；需换策略（头、Cookie、浏览器自动化或合法 API）。

更多细节见官方文档：<https://www.crummy.com/software/BeautifulSoup/bs4/doc/>
