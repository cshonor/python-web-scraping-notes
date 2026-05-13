# 第 2 章 复杂 HTML 解析：学习笔记

《Python 网络爬虫权威指南（第2版）》第 2 章的核心目标是：从**结构复杂**的网页中精准提取信息，并编写更健壮、不易因网页改版而失效的爬虫。

---

## 1. 核心知识点与原理

### 1.1 过滤器的艺术：CSS 属性与标签

- **不仅仅是标签**：如果只根据标签（如 `<table>`）提取数据，爬虫会非常脆弱。
- **利用 CSS 类和 ID**：现代网站广泛使用 CSS 来美化页面。通过 `class` 和 `id` 属性，可以区分具有相同标签但功能不同的元素（如不同样式区块）。
- **`find()` 与 `find_all()`**：
  - 这是 BeautifulSoup 最常用的两个函数。
  - `find_all` 可以接收多个标签作为**列表**参数，也可以接收**属性字典**（如 `{'class': 'green'}`，或多 class 场景下的多种写法）。
  - **关键字参数**：允许直接通过属性名搜索，例如 `bs.find_all(id='title')`。注意 `class` 是 Python 保留字，需使用 **`class_`** 或属性字典形式。

### 1.2 导航树（Navigating Trees）

当无法仅靠属性准确定位时，可以通过标签在文档中的**相对位置**来查找：

- **子节点与后代节点**：`children` 只遍历直接子节点；`descendants` 遍历所有下级节点。
- **兄弟节点**：`next_siblings` / `previous_siblings` 常用于表格、列表等「成块重复」的结构（例如跳过表头行再读数据行）。
- **父节点**：`parent` / `parents` 用于向上回溯。例如从 `<img>` 找到外层 `<td>`，再取相邻文字说明。

### 1.3 正则表达式与 Lambda 表达式

- **正则表达式**：在 `find_all` 等接口中，可将 **`re.compile(...)`** 作为参数传入，实现模糊匹配（例如匹配特定前缀的图片 `src`）。
- **Lambda 表达式**：BeautifulSoup 允许传入**接收一个标签、返回布尔值**的函数，用于自定义规则（例如「属性个数恰好为 2 的标签」）。

---

## 2. 关键建议与易错点

- **不要「一直用锤子」**：在处理复杂 HTML 之前，先看看是否有移动版页面、JavaScript/API 数据源，或能否从 URL 中直接得到所需信息。
- **保留标签结构**：除非是最后一步输出数据，否则不要轻易使用 `.get_text()`；尽量保留 DOM 层级，便于后续用父子、兄弟关系修正选择器。
- **代码的健壮性**：让选择器尽可能**具体**——多用 `class` / `id` / `data-*` 等稳定属性，少依赖「页面里第 N 个表格」这类顺序假设。

---

## 3. 示例代码：综合解析复杂 HTML

以下示例对应书中练习页 `page3.html`：**属性过滤、导航树、正则、`lambda` 综合使用**。

可运行脚本：`code/chapter02/page3_complex_parse.py`

```python
import re
from urllib.request import urlopen

from bs4 import BeautifulSoup

html = urlopen("http://www.pythonscraping.com/pages/page3.html", timeout=15)
raw = html.read()
bs = BeautifulSoup(raw, "html.parser")

# 1. 使用属性查找：获取所有绿色的名称
nameList = bs.find_all("span", {"class": "green"})
for name in nameList:
    print(f"人物名称: {name.get_text()}")

# 2. 导航树：处理产品表格，跳过标题行（利用 next_siblings）
print("\n产品列表：")
for sibling in bs.find("table", {"id": "giftList"}).tr.next_siblings:
    if sibling.name is not None:
        print(sibling.get_text().strip())

# 3. 正则表达式：获取所有产品图片路径
images = bs.find_all("img", {"src": re.compile(r"\.\.\/img\/gifts\/img.*\.jpg")})
for image in images:
    print(f"找到图片: {image['src']}")

# 4. Lambda：查找具有恰好 2 个属性的标签
tags = bs.find_all(lambda tag: len(tag.attrs) == 2)
print(f"\n具有2个属性的标签数量: {len(tags)}")
```

掌握这些技巧，可以更稳定地从复杂页面中「抠」出目标数据。

---

## 4. 与本仓库其他示例

本地小页面演示（不依赖外网）：`code/chapter02/css_and_lambda.py`

## 练习建议

1. 用 `select` 或 `class_` 重写「绿色名称」提取，与 `find_all` 版本对照。  
2. 为 `giftList` 表格增加空值判断：若找不到 `table` 或 `tr`，优雅退出并打印提示。  
3. 将正则中的图片路径改为从配置字符串拼接，便于在改版时只改一处。
