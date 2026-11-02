# 第 2 章 复杂 HTML 解析：学习笔记

真实页面的 DOM 不会给你一个干净的 `h1`。本章解决的问题是：**在嵌套很深、class 满天飞、同一类标签重复出现几十次的 HTML 里，把目标那一个精准捞出来**，并且保证站点改版时不至于整段崩掉。第 1 章解决的是「怎么把 HTML 拿到手」，本章解决的是「拿到手之后怎么从中取数」；后续章节里无论是存储（第 6 章）还是清洗（第 8 章），输入都来自本章这套定位与取值动作，所以这章的基本功直接决定后面所有代码的稳定性。

全章的技术主线可以概括为一条决策链：**有 id 用 id，没 id 用 class，class 不够就拼属性组合，属性表达不了上正则，正则也不够再交给 lambda，最后才考虑按层级位置导航** —— 越靠前越稳定，越靠后越灵活也越脆。示例脚本 `complex_parse.py` 在一个文件里把这条链上的每一环都演示了一遍，并附带网络层异常收敛、https 回退 http、空值防御等工程化写法，是本章唯一也是足够完整的练习场。

**本章目标**

1. 学会在**复杂、嵌套深**的 HTML 中精准定位数据
2. 掌握 `find()` / `find_all()` 的高级用法
3. 学会用**标签层级、属性、正则、lambda** 做灵活过滤
4. 写出**更稳定、不易崩**的爬虫

---

## 1. 核心知识点与原理

### 1.1 `find()` 与 `find_all()`

- **`find(...)`**：返回**第一个**匹配节点（Tag 对象），找不到返回 `None`
- **`find_all(...)`**：返回**列表**（`ResultSet`，可能是空列表，永远不会是 `None`）

两者接受完全相同的过滤参数，区别只在「取一个还是取全部」。`find_all` 额外支持 `limit=N`（只取前 N 个）—— 其实 `find(x)` 等价于 `find_all(x, limit=1)` 取首元素。

**参数形态全表**（以 `find_all` 为例，`find` 同理）：

| 写法 | 含义 | 示例 |
|---|---|---|
| 位置参数：标签名 | 按标签名过滤 | `bs.find_all("span")` |
| 位置参数：列表 | 匹配任一标签名（OR） | `bs.find_all(["td", "th"])` |
| 第二位置参数：属性字典 | 属性键值对过滤 | `bs.find_all("span", {"class": "green"})` |
| 关键字参数 | 属性过滤的简写 | `bs.find_all(id="giftList")` |
| `class_` 关键字 | 按 class 过滤（避开关键字） | `bs.find_all("span", class_="green")` |
| 属性值用列表 | 该属性取任一值即匹配 | `bs.find_all("span", class_=["green", "red"])` |
| 属性值用正则 | 属性值匹配模式 | `bs.find_all("img", {"src": re.compile(r"img\d")})` |
| 属性值用 `True` | 只要求属性存在 | `bs.find_all("img", {"src": True})` |
| 标签名用函数 | 自定义任意规则 | `bs.find_all(lambda t: len(t.attrs) == 2)` |
| `string=` 关键字 | 按文本内容过滤 | `bs.find_all(string="Anna")` |

```python
bs.find_all("span")
bs.find_all("span", class_="green")
bs.find_all("span", {"class": "green", "id": "name"})
bs.find_all(id="giftList")
```

**`class` 是 Python 关键字**，所以 BeautifulSoup 的参数名是 **`class_`**（带下划线），或者把 `class` 放进属性字典里（`{"class": "green"}`）。两种写法完全等价，混用不会报错，但同一项目里建议固定一种风格。

一个容易忽略的细节：标签名位置参数和属性过滤是 **AND** 关系 —— `find_all("span", class_="green")` 要求「既是 `span` 又有 `class=green`」，不是「`span` 或 green」。想要 OR 语义，把候选放进**列表**：`find_all(["td", "th"])` 一次取回两种单元格，遍历顺序仍是文档顺序。

两个低频但关键场景很好用的参数：**`recursive=False`** 只在直接子节点里找（默认会递归整棵子树），当你已经导航到某个容器、只想看它的直属孩子时，比 `.children` 过滤更直白；**`string=`** 匹配的是文本节点而不是 Tag，返回的是 `NavigableString` 列表，适合「先按文字找到锚点，再 `.parent` 回到标签世界」的反向定位（见 1.2 末尾）。

### 1.2 标签树导航（父子、兄弟、祖先）

当属性不足以定位时，用**相对位置**：

| 能力 | API | 返回类型 |
|---|---|---|
| 直接子节点 | `.children` | 迭代器（含空白文本节点） |
| 所有后代 | `.descendants` | 迭代器（递归展开整棵子树） |
| 下一兄弟 | `.next_sibling` / `.next_siblings` | 单个节点 / 迭代器 |
| 上一兄弟 | `.previous_sibling` / `.previous_siblings` | 单个节点 / 迭代器 |
| 父节点 | `.parent` / `.parents` | 单个 Tag / 迭代器（一直走到根） |
| 下一个任意节点 | `.next_element` | 按文档顺序的下一个节点（不限兄弟） |

**真实 DOM 例子**（来自本章示例页 `page3.html` 的 `giftList` 表格）：`bs.find("table", id="giftList")` 拿到表格后，`table.tr` 是它的第一行（表头，内容是空的 `th`）。要读后面的 5 行商品数据，不能 `table.find_all("tr")` 之外再跳第一行那么绕 —— 直接从 `table.tr.next_siblings` 走：第一个兄弟是换行符（`NavigableString`，`.name` 为 `None`），第二个才是 `<tr id="gift1">`，然后又是换行、`<tr id="gift2">`……如此交替直到表格结束。所以遍历模板固定为：

```python
for sibling in table.tr.next_siblings:
    if sibling.name:  # 跳过空白文本节点，只留真正的 Tag
        print(sibling.get_text(strip=True))
```

`next_siblings` 会把**空白文本节点**也一起吐出来（换行、缩进在 bs4 眼里都是 `NavigableString`），所以必须用 `if sibling.name` 过滤 —— 只保留真正的 Tag。同理，`.children` 里混着的空白节点也要这样过滤；`.descendants` 因为会把每个文本节点都吐出来，遍历时几乎必然要做类型判断。

**`.parent` 的反向用途**：有时候目标本身没有可定位属性，但它旁边有。比如想找「那张包含 `img1.jpg` 的表格行」，可以先 `bs.find("img", {"src": "../img/gifts/img1.jpg"})`，再 `.parent` 拿到 `<td>`、再 `.parent` 拿到 `<tr id="gift1">`。自下而上走两步，往往比自上而下写一长串选择器更稳。

### 1.3 正则表达式（模糊匹配）

属性值只是「部分固定」时，正则比全等匹配好用得多：

```python
import re
bs.find_all("img", {"src": re.compile(r"/img/gifts/.*\.jpg")})
```

适合图片 `src`、链接 `href`、class 片段这类有规律的字符串。

**贪婪与非贪婪**：`.*` 是贪婪匹配 —— 默认尽可能多吃字符；`.*?` 是非贪婪 —— 吃到能满足整体匹配的最少字符就停。本章脚本用的模式是 `r"\.\.\/img\/gifts\/img.*\.jpg"`：对一个 `src` 里只出现一次 `.jpg` 的场景，贪婪与否结果相同；但如果属性值是 `../img/a.jpg?backup=.jpg` 这种形式，`.*\.jpg` 会一路吃到最后一个 `.jpg`，而 `.*?\.jpg` 只到第一个。写属性匹配正则时，优先想清楚「这个值里模式片段可能出现几次」，出现多次时显式选 `.*?` 往往更符合直觉。另外注意 `re.compile` 的对象会被 bs4 拿去做**搜索**（`search` 语义），不是全等匹配，所以模式两端的锚点（`^` / `$`）要不要加，取决于你想不想允许前后有杂字符。

**书写细节**：Python 的原始字符串里 `/` 不需要转义，`r"\.\.\/img\/gifts\/img.*\.jpg"` 与 `r"\.\./img/gifts/img.*\.jpg"` 完全等价 —— 前者只是沿用了原书从 JavaScript 风格带来的习惯，自己写时用后者更清爽。真正必须转义的是 `.`（否则它匹配任意字符）。正则同样可以按 class 过滤：`find_all("span", class_=re.compile(r"^(green|red)$"))` 能一次捞两种颜色的人名，这正是「红绿人物名」练习的常用解法。

### 1.4 Lambda 与函数式过滤（及其边界）

静态参数表达不了的规则，交给函数。`find_all` 的第一个位置参数可以是一个可调用对象，bs4 会把文档里**每一个 Tag** 依次传进去，返回真值即入选：

```python
bs.find_all(lambda tag: len(tag.attrs) == 2)
bs.find_all(lambda tag: tag.get_text() and "关键词" in tag.get_text())
```

**能力边界要清楚**：

- 函数**每次只看到一个孤立的 Tag**，看不到它在树里的上下文。想表达「父亲是谁」「前面一个兄弟是什么」，得在函数体内现场调 `.parent` / `.previous_sibling`，可以做但可读性会迅速变差 —— 那种规则更适合先定位锚点再导航（见 1.2），而不是塞进 lambda。
- 函数会被调用 **N 次（N = 全文档 Tag 数）**，函数体里别放重操作（比如正则编译要提到外面）。
- 函数体里访问属性要防缺：tag.attrs 一定存在，但 `tag["src"]` 在无 src 的标签上会抛 `KeyError`，lambda 里应写 `tag.get("src")` 或先判断。
- lambda 写不下就**定义普通函数再传名**，效果完全一样，还能加 docstring 和单测。

### 1.5 `get_text()` 的使用时机与参数

- 会把**标签剥掉、只留拼接文本**，适合**最后一步输出**
- **解析过程中慎用** —— 一旦 `get_text()`，父子/兄弟关系全没了，后续再想导航就得回头重新解析

**`strip` 与 `separator` 两个参数**（本章实测输出正好暴露了它们的价值）：

| 参数 | 作用 | 不加会怎样 |
|---|---|---|
| `strip=True` | 剥掉每段文本首尾空白 | 输出里满是缩进和换行 |
| `separator=" "` | 各段文本之间用指定串连接 | 相邻单元格的文字**直接粘在一起** |

`complex_parse.py` 第 2 段对整行 `<tr>` 调 `get_text(strip=True)`，四个 `<td>` 的文本被**无缝拼接**成一长串（商品名、描述、价格全粘在一起，见 §3 实测输出）。想要可读的逐字段输出，应该 `get_text(separator="|", strip=True)`，或者干脆 `row.find_all("td")` 逐格取 —— 后者还能保留「哪段文字来自哪一列」的信息。

这条和上一条其实是同一个坑的两面：**导航靠 Tag 对象，取值才用 `get_text()`**。解析阶段的每一步都应尽量留在 Tag 世界里，把「变成字符串」推迟到确实要输出的那一刻。

**相关 API**：`.string` 只在「标签内有且仅有一个文本节点」时返回值，否则是 `None` —— 对含子标签的节点（比如带 `<span class="excitingNote">` 的商品描述格）必然拿到 `None`，不如 `get_text()` 可靠；`.stripped_strings` 返回「逐段剥好空白」的生成器，等价于把 `get_text(separator=..., strip=True)` 拆开遍历，适合想把每段文本单独处理的场景（比如逐段写入 CSV 的不同列）。日常取值优先级：`get_text(strip=True)` > `.stripped_strings` > `.string`。

---

## 2. 异常处理与最佳实践（易错点）

1. **只靠链式索引定位**：`bs.table.tr.td` 这种写法把「第一层 table、第一个 tr、第一个 td」全写死了，页面只要在任意一层前面插一个同类标签，取到的就是另一个元素，而且不报错、静悄悄地取错数据。优先用 **id / class / 属性组合**定位，链式访问只用于「定位锚点之后的一两步导航」，并且每一步都要意识到它可能返回 `None`。

2. **不判空就连着调**：`find` 找不到时返回 `None`，紧接着 `.children` / `.tr` / `.get_text()` 都会抛 `AttributeError`，而且这种异常只在目标缺失时才出现 —— 本地测试页面齐全时根本暴露不了。`complex_parse.py` 的写法是标准模板：`table = bs.find("table", id="giftList")` 之后用 `if table and table.tr:` 把两级空值一次性挡掉，失败分支打印一句说明而不是让 traceback 糊一脸。

3. **`class` 写成关键字**：`find_all("span", class="green")` 是语法错误，必须写 **`class_`**（bs4 约定的下划线后缀），或者放进属性字典 `{"class": "green"}`。类似地，`for`、`type` 等 Python 关键字做属性过滤时也必须走字典写法。

4. **过早 `get_text()`**：文本一旦取出来，标签结构就没了 —— 不能再找子标签、不能再读属性、不能再导航。常见翻车形态是「先 `get_text()` 存进列表，后面又想按里面的链接分组」，只能回头重解析。规则很简单：**所有过滤、导航都在 Tag 上完成，`get_text()` 只出现在 print / 写文件的上一行**。

5. **`next_siblings` 含空白节点**：HTML 源码里的换行缩进会被解析成 `NavigableString` 混在兄弟节点里，对它们调 `.get_text()` 不报错但吐空白，调 `.find()` 直接 `AttributeError`。遍历兄弟或子节点时固定加 **`if sibling.name`**（或 `getattr(sibling, "name", None)`，即 `complex_parse.py` 第 67 行的写法）过滤，只处理真正的 Tag。

6. **把「没找到」当「抓到空」**：`find_all` 返回空列表时循环体一次都不执行，程序「正常跑完」却什么都没抓到 —— 这比抛异常更危险，因为下游可能把空结果当成「今天就是没有新数据」写进库里。对关键数据加一句 `if not names: print("(未找到，页面结构可能已变)")`（`complex_parse.py` 第 58–59 行正是这么做的），让静默失败变成显式信号。

7. **把正则写成普通字符串**：`find_all("img", {"src": "../img/gifts/img1.jpg"})` 传字符串时做的是**全等匹配**，一个字符都不能差；想模糊匹配必须传 `re.compile(...)` 编译后的对象（bs4 会对属性值调它的 `search`）。新手常犯的错误是写了 `{"src": "img1"}` 指望它当子串匹配 —— 不会，只会什么都匹配不到，而且这种「正则忘编译」的错误不抛任何异常，只是安静地返回空列表，排错时先检查属性值参数的类型。

8. **在 lambda 里直接取下标**：`lambda tag: tag["src"].endswith(".jpg")` 对没有 `src` 的 `img`（或任何被遍历到的无该属性标签）会抛 `KeyError`，而 lambda 会被应用到**全文档每一个 Tag**，中招概率极高。安全写法是 `tag.get("src", "").endswith(".jpg")` 或先判断 `tag.has_attr("src")`；规则稍复杂就换普通函数，别硬挤进一行 lambda。

---

## 3. 示例代码

主示例：**`chapter-02/complex_parse.py`**（依赖仅 `beautifulsoup4`，见同目录 `requirements.txt`）。

基础设施两个函数：`get_soup(url)` 统一收敛网络异常 —— `Request` 带自定义 User-Agent（`Chapter02ComplexParse/1.0 (educational)`）、`urlopen` 设 **20 秒超时**，`except (HTTPError, URLError, OSError)` 打印原因并返回 `None`；`first_soup(urls)` 按顺序尝试 **https → http** 两个地址，返回第一个成功的 soup，全失败返回 `None`。`main()` 一上来就是 `bs = first_soup(URLS); if bs is None: return 1` —— 主页面拿不到就直接非零退出，不硬撑。

**注意它抓了两个页面**，因为书里这两个示例本来就不在同一个页面上：

| 演示 | 页面 | 选择器 |
|---|---|---|
| 绿/红人物名 | `pages/warandpeace.html` | `span.green` |
| 产品表格 + 图片正则 + lambda | `pages/page3.html` | `table#giftList` / `img[src~=img/gifts/]` / 属性计数 |

早期版本只在 `page3.html` 上找 `span.green`，而那页根本没有这个 class，输出永远是「未找到」—— 这是代码 bug，不是站点改版。现在两页分别请求（`URLS` 与 `WAR_URLS` 两组地址），warandpeace 失败时也只是打印跳过提示、不影响后面三段。

### 3.1 四个演示段逐段走读

**第 1 段：`war.find_all("span", class_="green")`（complex_parse.py:57）**。证明「标签名 + `class_`」这对最常用组合在真实页面上一次命中几十处同名结构 —— 《战争与和平》页面里所有绿色人名共用一个 class，一次调用全部捞出。同时演示空列表保护：`if not names` 时打印「页面结构可能已变」而不是静默通过。

**第 2 段：`table.tr.next_siblings` 遍历（complex_parse.py:64–70）**。证明「先 id 锚定、再兄弟导航」的两段式定位：`find("table", id="giftList")` 锁定表格，首行是表头，数据全在它的兄弟节点里。`getattr(sibling, "name", None)` 过滤空白文本节点，正是 §1.2 的标准模板。防御写法 `if table and table.tr:` 一次挡住两级空值。为什么不用 `table.find_all("tr")[1:]`？也能工作，但 `next_siblings` 版本把「从表头之后开始」这个意图写进了代码结构里，且不需要先物化整个行列表 —— 表格行数很大时差别会体现出来。

**第 3 段：`img` 的 `src` 正则（complex_parse.py:73）**。模式 `r"\.\.\/img\/gifts\/img.*\.jpg"` 匹配「`../img/gifts/img` 开头、`.jpg` 结尾」的路径。证明正则能把「前缀固定的同族资源」一网打尽 —— 实测抓到 img1、img2、img3、img4、**img6**（注意没有 img5，站点本来就没这张图，正则照实反映了页面，而不是凑齐编号）。

**第 4 段：`lambda tag: len(tag.attrs) == 2`（complex_parse.py:77）**。把整页所有「恰好两个属性」的标签全捞出来，脚本只打印前 10 个并附总数。实测这页一共只有 **6 个**：5 个 `<tr class="gift" id="giftN">` 加 1 个带 `src` + `style` 的 logo `<img>`。这个例子要说明的是「lambda 能表达任意规则」，不是「这是个好的定位方式」—— 属性计数这种规则和页面内容毫无语义关联，改版时死得最快。注意打印出来的 `<tr>` 标签是**带完整子树的**（`print(t)` 输出整个 Tag 的 HTML），终端里一刷一大片属正常现象；`tags[:10]` 这个切片也顺带演示了 `find_all` 返回的 `ResultSet` 就是个列表，切片、`len()`、`for` 全都可用。

### 3.2 运行方式与实测输出

### 3.2 运行方式与实测输出

```bash
cd chapter-02
pip install -r requirements.txt
python3 complex_parse.py
```

实测输出（2026-11-02 复核，节选；完整输出 46 行人物名 + 5 行表格 + 5 行图片路径 + 6 个标签）：

```text
===== 1. 所有绿色人物名称（warandpeace.html） =====
Anna
Pavlovna Scherer
Empress Marya
Fedorovna
Prince Vasili Kuragin
...（共 46 个 span.green）

===== 2. 产品表格数据 =====
Vegetable BasketThis vegetable basket is the perfect gift ... $15.00
Russian Nesting DollsHand-painted by trained monkeys, ... $10,000.52
...（共 5 行，注意各列文本被无缝拼接）

===== 3. 图片路径（正则） =====
../img/gifts/img1.jpg
../img/gifts/img2.jpg
../img/gifts/img3.jpg
../img/gifts/img4.jpg
../img/gifts/img6.jpg

===== 4. 恰好含 2 个属性的标签（前 10 个） =====
<img src="../img/gifts/logo.jpg" style="float:left;"/>
<tr class="gift" id="gift1">...
... 共 6 个
```

第 2 段输出里「商品名描述价格全粘在一起」不是 bug，是 `get_text(strip=True)` 对整行调用的必然结果 —— 想分列打印，改用 `separator="|"` 或逐 `<td>` 取（见 §1.5 与练习 1）。

整段运行退出码为 0（2026-11-02 实测）：两个页面均一次 https 命中，未触发 http 回退分支；若想验证回退逻辑，可临时把 https 地址改成一个必然失败的域名再观察 `first_soup` 的行为。

---

## 4. 学习贴士

- **定位优先级**：`id` > `class` > 属性组合 > 层级位置。层级位置是最脆的一种，一旦上游插了个 `<div>` 就全错位。lambda / 属性计数这类「和内容无语义关联」的规则排在最后，只适合做一次性探索。
- **改版是常态，不是意外**。写复杂页面前先问一句「如果这个 `class` 明天改名，我的代码会崩还是会返回空？」—— 后者可接受，前者不可接受。把每个关键 `find` 的空分支写出来，等于提前把「改版告警」埋进代码里。
- **先用浏览器开发者工具验证选择器，再写代码**。在 Elements 面板里 Ctrl+F 直接搜 `span.green` 或正则，能立刻看到命中数量；命中数和预期不符时先怀疑选择器，再怀疑代码。
- **`lxml` 能让同一套选择器更快，但不改变选择器是否选得对**。先保证选得对（`html.parser` 零依赖、容错好），确有性能瓶颈再换解析器；requirements.txt 里 lxml 被注释掉，就是这个取舍。
- **正则先在 REPL 里试**。`re.compile(pattern).search(真实属性值)` 一行就能验证贪婪/非贪婪和转义是否写对，比改完脚本整跑一遍快得多。
- **探索期多用交互式环境，成型后再落成脚本**。把抓回来的 HTML 存个副本，在 IPython / Jupyter 里反复试选择器，命中数、文本形态都确认了再写进 `.py` —— 反复整跑脚本去调选择器，既慢又会给目标站点造成多余请求。
- **把网络层和解析层分开测**。`get_soup()` 返回 `None` 是网络问题，返回了 soup 但 `find` 为空是解析/选择器问题 —— 排错时先确认属于哪一层再动手。`complex_parse.py` 把这两层拆成 `get_soup` / `first_soup` / `main` 三段，就是为了这个定位效率；你自己写爬虫时也值得照抄这个结构，而不是把请求、解析、取数揉在一个函数里。

---

## 5. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-02/complex_parse.py` | 本章唯一脚本：`find_all` 属性过滤、兄弟导航跳表头、正则匹配、lambda 过滤四个演示（已实测，2026-11-02） |
| `chapter-02/requirements.txt` | 本章依赖：`beautifulsoup4>=4.12.0`（`lxml` 为可选解析器，注释状态） |
| `chapter-01`（对照） | 第 1 章解决「把 HTML 拿下来」，本章解决「从 HTML 里取数」，两章的 `Request` + 超时 + 异常收敛写法一脉相承 |
| `chapter-06`（下游） | 本章 `get_text()` 取出的字符串，正是第 6 章 CSV / JSONL / 数据库落地的输入 |

本章只有 `complex_parse.py` 一个脚本，但覆盖了 `find_all` 属性过滤、正则匹配、`next_siblings` 跳表头三类高频场景，加上 lambda 这个「兜底表达力」，足以应付绝大多数静态页面的取数需求。后续章节的示例凡涉及解析，默认你已经掌握本章这套 API；遇到动态渲染的页面（JavaScript 生成内容），则属于第 10–11 章 Selenium 的范畴，本章的纯静态解析不再适用。

---

## 练习建议

1. 把表格输出改成只提取**商品名 + 价格**两列：对每行 `row.find_all("td")`，取第 0、2 格分别 `get_text(strip=True)`，对比与整行 `get_text()` 的可读性差异。
2. 给所有关键 `find` 加上空值分支，做到改版不崩：把 `warandpeace.html` 的 `class_="green"` 故意改成不存在的值，观察程序是打印提示还是抛异常。
3. 把图片正则改写成你认为更易维护的形式（如 `r"\.\./img/gifts/img\d+\.jpg"`），并用 REPL 验证它对 `img6.jpg` 命中、对 `logo.jpg` 不命中。
4. 用 `.children` 遍历表格的 `<tr>`，与 `next_siblings` 写法对比差异：起点不同（`table` vs `table.tr`）、空白节点处理方式相同，哪种更易读懂？
5. 给第 4 段的 lambda 换成「属性里含 `id` 且 id 以 `gift` 开头」的规则，验证抓到的恰好是 5 个 `<tr>`；再想一种静态参数写法达到同样效果（提示：`id=re.compile(r"^gift")`），比较两种写法的可读性。
6. 把 `warandpeace.html` 的绿色人名去重后按出现次数排序输出（`collections.Counter`），观察「the prince」「Anna Pavlovna」各出现多少次 —— 体会 `get_text(strip=True)` 输出的文本如何直接变成可统计的数据。
