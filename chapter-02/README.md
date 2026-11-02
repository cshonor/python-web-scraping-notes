# 第 2 章 复杂 HTML 解析：学习笔记

真实页面的 DOM 不会给你一个干净的 `h1`。本章解决的问题是：**在嵌套很深、class 满天飞、同一类标签重复出现几十次的 HTML 里，把目标那一个精准捞出来**，并且保证站点改版时不至于整段崩掉。

**本章目标**

1. 学会在**复杂、嵌套深**的 HTML 中精准定位数据
2. 掌握 `find()` / `find_all()` 的高级用法
3. 学会用**标签层级、属性、正则、lambda** 做灵活过滤
4. 写出**更稳定、不易崩**的爬虫

---

## 1. 核心知识点与原理

### 1.1 `find()` 与 `find_all()`

- **`find(...)`**：返回**第一个**匹配节点，找不到返回 `None`
- **`find_all(...)`**：返回**列表**（可能是空列表）

```python
bs.find_all("span")
bs.find_all("span", class_="green")
bs.find_all("span", {"class": "green", "id": "name"})
bs.find_all(id="giftList")
```

**`class` 是 Python 关键字**，所以 BeautifulSoup 的参数名是 **`class_`**（带下划线），或者把 `class` 放进属性字典里。

### 1.2 标签树导航（父子、兄弟、祖先）

当属性不足以定位时，用**相对位置**：

| 能力 | API |
|---|---|
| 直接子节点 | `.children` |
| 所有后代 | `.descendants` |
| 下一兄弟 | `.next_sibling` / `.next_siblings` |
| 上一兄弟 | `.previous_sibling` / `.previous_siblings` |
| 父节点 | `.parent` / `.parents` |

**典型场景：跳过表头读后续行**

```python
for sibling in table.tr.next_siblings:
    if sibling.name:
        print(sibling.get_text(strip=True))
```

`next_siblings` 会把**空白文本节点**也一起吐出来（换行、缩进在 bs4 眼里都是 `NavigableString`），所以必须用 `if sibling.name` 过滤 —— 只保留真正的 Tag。

### 1.3 正则表达式（模糊匹配）

属性值只是「部分固定」时，正则比全等匹配好用得多：

```python
import re
bs.find_all("img", {"src": re.compile(r"/img/gifts/.*\.jpg")})
```

适合图片 `src`、链接 `href`、class 片段这类有规律的字符串。

### 1.4 Lambda（自定义过滤）

静态参数表达不了的规则，交给函数：

```python
bs.find_all(lambda tag: len(tag.attrs) == 2)
bs.find_all(lambda tag: tag.get_text() and "关键词" in tag.get_text())
```

### 1.5 `get_text()` 的使用时机

- 会把**标签剥掉、只留拼接文本**，适合**最后一步输出**
- **解析过程中慎用** —— 一旦 `get_text()`，父子/兄弟关系全没了，后续再想导航就得回头重新解析

这条和上一条其实是同一个坑的两面：**导航靠 Tag 对象，取值才用 `get_text()`**。

---

## 2. 异常处理与最佳实践（易错点）

1. **只靠链式索引**：`bs.table.tr.td` 一改版就崩，优先用 **id / class / 选择器**
2. **不判空**：`find` 拿到 `None` 再 `.children` → `AttributeError`
3. **`class` 写成关键字**：必须写 **`class_`**
4. **过早 `get_text()`**：后续无法再导航
5. **`next_siblings` 含空白节点**：用 **`if sibling.name`**（或 `getattr(sibling, "name", None)`）过滤

---

## 3. 示例代码

主示例：**`chapter-02/complex_parse.py`**

要点：`get_soup()` 统一收敛网络异常；**`Request` + User-Agent + 超时**；**https 失败时回退 http**；遍历表格前先判断 **`table` 与 `table.tr`** 是否存在，再走 `next_siblings`。

**注意它抓了两个页面**，因为书里这两个示例本来就不在同一个页面上：

| 演示 | 页面 | 选择器 |
|---|---|---|
| 绿/红人物名 | `pages/warandpeace.html` | `span.green` |
| 产品表格 + 图片正则 | `pages/page3.html` | `table#giftList` / `img[src~=img/gifts/]` |

早期版本只在 `page3.html` 上找 `span.green`，而那页根本没有这个 class，输出永远是「未找到」—— 这是代码 bug，不是站点改版。现在两页分别请求。

```bash
cd chapter-02
pip install -r requirements.txt
python3 complex_parse.py
```

实测输出（2026-11 复核，节选）：

```text
===== 1. 所有绿色人物名称（warandpeace.html） =====
Anna
Pavlovna Scherer
Empress Marya
...

===== 2. 产品表格数据 =====
Vegetable Basket...$15.00
Russian Nesting Dolls...$10,000.52
```

注意第 4 段 `lambda tag: len(tag.attrs) == 2` 那部分：它会把整页所有恰好两个属性的标签都吐出来，数量几十上百是正常的 —— 这个例子要说明的是「lambda 能表达任意规则」，不是「这是个好的定位方式」。

---

## 4. 学习贴士

- **定位优先级**：`id` > `class` > 属性组合 > 层级位置。层级位置是最脆的一种，一旦上游插了个 `<div>` 就全错位。
- **改版是常态，不是意外**。写复杂页面前先问一句「如果这个 `class` 明天改名，我的代码会崩还是会返回空？」—— 后者可接受，前者不可接受。
- **`lxml` 能让同一套选择器更快，但不改变选择器是否选得对**。先保证选得对。

---

## 5. 与本仓库其他示例

本章只有 `complex_parse.py` 一个脚本，覆盖了 `find_all` 属性过滤、正则匹配、`next_siblings` 跳表头三类场景。依赖见同目录 `requirements.txt`。

---

## 练习建议

1. 把表格输出改成只提取**商品名 + 价格**（需要先分析子标签结构）。
2. 给所有关键 `find` 加上空值分支，做到改版不崩。
3. 把图片正则改写成你认为更易维护的形式。
4. 用 `.children` 遍历表格的 `<tr>`，与 `next_siblings` 写法对比差异。
