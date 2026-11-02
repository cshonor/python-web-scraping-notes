# 第 8 章 数据清洗：学习笔记

前几章解决的是「怎么把数据抓下来」，本章解决的是「抓下来的数据能不能直接用」。网页文本天然带噪声：引用角标、断行、多余空白、大小写不一致、全角半角混杂，直接喂给统计或 NLP 会得到失真的结论。本章的核心机制可以概括成一句话：**先对原始文本做归一化（裁噪声、统一表示），再做结构化统计（词表、n-gram、去重）**。在流程上它承上启下 —— 第 7 章的文档读取给了我们原始字符串，本章把它洗成干净词表，第 9 章的分词、词干化等 NLP 步骤才有可靠输入。清洗分两种姿势：**预防型清洗**（入库前在爬虫侧做）与**落库后标准化**（对已采集数据批量修正），本章两边都会碰到。

**本章目标**

1. 能对网页噪声做分类：结构性噪声（HTML 残留、断行、角标）与表示性噪声（大小写、全半角、Unicode 变体），并选对工具处理
2. 掌握文本归一化的常用手段：正则裁剪、空白压缩、`unicodedata` 规范化、大小写折叠
3. 理解 **n-gram** 模型，会用 `collections.Counter` 统计 2-gram 高频片段
4. 理解「去重」的时间语义，会用 pandas 的 `sort_values + drop_duplicates(keep=...)` 保留最新记录
5. 知道 `encode("utf-8").decode("ascii", "ignore")` 这类激进清洗的代价，能在多语言场景换用温和方案
6. 了解 OpenRefine 等「人机结合」工具与纯代码流水线的互补关系

---

## 1. 核心知识点与原理

### 1.1 噪声从哪里来：两类来源

清洗前先搞清楚噪声的来源，不同来源对应不同处理时机：

| 噪声类型 | 典型例子 | 产生环节 | 处理时机 |
|---|---|---|---|
| 结构性噪声 | `[12]` 引用角标、`\n` 断行、HTML 实体、页眉页脚残留 | 网页排版与标注 | 解析后、统计前（代码流水线） |
| 表示性噪声 | 大小写不一致、全角／半角、不间断空格、Unicode 兼容字符 | 录入习惯与编码差异 | 归一化阶段（入库前后均可） |
| 重复性噪声 | 同一 URL 多次抓取、同一实体多种拼写 | 增量抓取、多源合并 | 落库后用去重 / 聚类处理 |

一个工程上的重要区分：**预防型清洗**在爬虫入库前做，成本最低，但规则一旦定错会污染整批数据且不可逆；**落库后标准化**保留原始数据、随时重跑规则，代价是要存双份。实践中通常两者结合：入库前做「确定无损」的裁剪（去角标、压空白），入库后做「可能反复调整」的归一与去重。

### 1.2 文本归一化：统一表示形式

目标是在**业务含义不变**的前提下统一表示形式，让「同一个东西」在统计时只算一次。常见手段：

| 手段 | Python 工具 | 说明 |
|---|---|---|
| 大小写折叠 | `str.upper()` / `str.lower()` / `str.casefold()` | 减少「同一词」的多种写法；`casefold()` 比 `lower()` 更彻底（能处理德语 ß 等），但专有名词过度折叠会损失信息，应按字段策略选择 |
| Unicode 规范化 | `unicodedata.normalize("NFKC", s)` | 把全角字符、兼容字符折叠为等价的标准形式，中文站尤其重要 |
| 空白压缩 | `re.sub(r"\s+", " ", s)` | 把换行、制表、连续空格压成单个空格 |
| 正则裁剪 | `re.sub(r"\[\d+\]", " ", s)` | 去掉 `[12]` 这类引用角标 |

日期、电话、货币等结构化字段同理：先解析成标准类型（如 `pd.to_datetime`），再按统一格式输出，而不是在字符串层面做比较。

归一化的效果可以直接在解释器里验证，例如 NFKC 对全角字符的折叠：

```python
>>> import unicodedata
>>> unicodedata.normalize("NFKC", "ＡＢＣ　123")
'ABC 123'
```

全角字母变半角、全角空格变普通空格，但汉字等表意字符原样不动 —— 这就是它适合中文语料的原因。

### 1.3 清洗顺序：为什么先后有影响

清洗步骤不是可交换的，顺序错了会直接影响结果。本章示例遵循的顺序值得记住：

| 步骤 | 动作 | 为什么要在这个位置 |
|---|---|---|
| 1 | 去角标 / 去标记 | 在分词前做，否则 `[1]` 会被拆成伪词或粘到前后的词上 |
| 2 | 空白归一（换行→空格、压缩） | 在分句分词前做，否则 `\n` 会干扰按空格切分 |
| 3 | 大小写折叠 | 在统计前做即可；做太早会让专有名词信息提前丢失，不便调试 |
| 4 | 编码 / Unicode 处理 | 在 strip 标点之前做，避免把「待剥除的字符集」算错 |
| 5 | 分句、分词、剥两端标点 | 依赖前面所有步骤产出的「干净字符串」 |

记忆口诀：**先删后换再切分** —— 先删掉确定不要的（角标），再把表示形式换统一（空白、大小写、编码），最后才做切分与统计。

### 1.4 n-gram 模型：从词表到片段

**n-gram** 指文本中 **n 个连续词**（或字符）组成的片段。2-gram（bigram）常用于语言模型、近似去重、简单特征与摘要候选。构造方式非常直白：对词表 `words`，取 `n` 个错位切片再 `zip`：

```python
def ngrams(words, n):
    return zip(*[words[i:] for i in range(n)])
```

`words[i:]` 表示「从第 i 个词开始的子序列」，`zip(*...)` 把 n 条错位序列按位置对齐，每个位置就是一个 n-gram。举例：`["A", "B", "C"]` 取 2-gram，即 `zip(["A","B","C"], ["B","C"])`，得到 `("A","B")` 和 `("B","C")` 两个片段。

与 **`collections.Counter`** 结合可统计高频片段，用于发现模板句、固定搭配或噪声模式 —— 比如某个 2-gram 频率异常高，往往说明页面里有没清掉的模板文本。`Counter` 的 `most_common(k)` 直接给出 Top-k，适合快速巡检清洗质量：高频片段里如果混着「CLICK HERE」「READ MORE」这类导航文本，就说明上游解析没剥干净。

### 1.5 去重与 pandas 工具链

抓取系统里「去重」通常不是简单的「删掉相同行」，而是带**时间语义**的：同一 URL 抓了多次，要保留**最新一次**的结果。pandas 的标准打法是两步：

1. `sort_values("scraped_at")`：按抓取时间排序，让「最新」的位置确定（升序时最新在最后）；
2. `drop_duplicates("url", keep="last")`：以 `url` 为键去重，`keep="last"` 配合上一步的排序，恰好留下最新记录。

这套「排序 + 保留策略」的组合比手写循环去重可靠：语义清晰、向量化执行，且 `keep` 参数（`"first"` / `"last"` / `False`）能覆盖「留最早」「留最新」「全删」三种常见需求。

### 1.6 常用工具速览

| 工具 | 定位 | 适用场景 |
|---|---|---|
| `collections.Counter` | 频次统计 | 词频、n-gram 频次，接口简单，一行出结果 |
| `re` 正则 | 模式裁剪 | 去角标、压空白、删异常分隔符 |
| `unicodedata` | Unicode 规范化 | 全半角、兼容字符折叠（多语言安全） |
| pandas | 表格级清洗 | 去重、缺失值、类型转换、分组统计 |
| OpenRefine | 人机结合清洗 | 开源桌面工具，用 GREL 表达式在表格上筛选、聚类、批量变换，适合拼写变体合并等「机器拿不准、人来拍板」的场景，与纯代码流水线互补 |

---

## 2. 代码示例：获取干净的词表与 2-gram

本章三个脚本都已在本地实测通过（Python 环境：requests/bs4/pandas 已装）。

### 2.1 `clean_ngrams.py`：清洗 + 2-gram 统计

这是书中的主示例，思路是「先 `clean_input` 得到干净词列表，再用 `Counter` 统计 2-gram」。`clean_input` 按固定顺序做四步裁剪：正则去 `[数字]` 角标 → 换行替换为空格 → 全文转大写 → 编码层面剔除非 ASCII；随后按 `. ` 分句、按空格分词，每个词再用 `string.punctuation + string.whitespace` 把两端的标点与空白剥掉，空串丢弃。`ngrams` 就是 1.4 节的错位 zip。注意两个易错点：其一，原稿正则 `'\n|[[\d+\]]'` 括号写错了，本章脚本已勘误为清晰的 `r"\[\d+\]"` 配合单独的 `replace("\n", " ")`；其二，`encode("utf-8").decode("ascii", "ignore")` 会**删除所有非 ASCII 字符，包括中文**，脚本注释里也明确标注了这一点 —— 多语言场景请改用 `casefold()` / `unicodedata` 等温和手段。

关键代码摘录：

```python
def clean_input(content: str) -> list[str]:
    content = re.sub(r"\[\d+\]", " ", content)
    content = content.replace("\n", " ")
    content = content.upper()
    content = content.encode("utf-8", errors="ignore").decode("ascii", errors="ignore")
    sentences = content.split(". ")
    out: list[str] = []
    for sentence in sentences:
        for word in sentence.split(" "):
            w = word.strip(string.punctuation + string.whitespace)
            if w:
                out.append(w)
    return out
```

运行：

```bash
cd chapter-08
python clean_ngrams.py
```

实测输出（示例文本含 `[2][3]` 角标，清洗后词表 18 个词，全大写）：

```text
词表长度: 18
前若干 2-gram: [('MONTY PYTHON', 1), ('PYTHON ALSO', 1), ('ALSO COLLECTIVELY', 1), ...]
```

因为示例文本短，每个 2-gram 都只出现 1 次；真实页面上跑就能看出高频模板的聚集效应。

### 2.2 `clean_text.py`：空白与 Unicode 规范化

这是 1.2 节归一化手段的最小演示，只有一个函数 `squash_spaces`：先 `unicodedata.normalize("NFKC", s)` 把全角字符和兼容字符折叠成 ASCII 等价形式，再 `re.sub(r"\s+", " ", s)` 把任意连续空白（含换行、制表、全角空格经 NFKC 转换后的普通空格）压成单个空格，最后 `strip()` 去首尾。它展示了和 `clean_ngrams.py` 截然不同的清洗哲学：**不伤内容字符，只统一表示形式**。测试输入里同时埋了三种坑 —— 全角字母 `ＡＢＣ`、全角空格 `\u3000`、`\n\t` 混合空白与连续空格，一个函数全部抹平。

关键代码摘录：

```python
def squash_spaces(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

raw = "  全角ＡＢＣ　\n\tfoo   bar  "
print(squash_spaces(raw))
```

运行：

```bash
cd chapter-08
python clean_text.py
```

实测输出：

```text
全角ABC foo bar
```

注意 NFKC 只折叠了拉丁字母部分（`ＡＢＣ` → `ABC`），汉字「全角」原样保留 —— 这正是它比 ASCII 剔除法安全的原因。但反过来也要警惕：NFKC 会改变某些有语义区别的字符（如上标、圈号），对这类字符敏感的字段不要用。

### 2.3 `pandas_dedupe.py`：带时间语义的去重

这是 1.5 节「排序 + 保留策略」的完整实现，模拟增量抓取场景：三条记录里 `https://a` 出现了两次，`t1`（01-02 抓）比 `t2`（01-01 抓）新。脚本先把 `scraped_at` 字符串列用 `pd.to_datetime` 转成真正的日期类型 —— 这一步不能省，字符串排序在跨月、跨年等场景会出错；然后 `sort_values("scraped_at")` 升序排，让同 key 的最新记录排到最后；最后 `drop_duplicates("url", keep="last")` 以 url 为键去重，留下的恰好是每个 URL 的最新一次抓取。脚本对 pandas 缺失做了优雅降级：`ImportError` 时向 stderr 打印安装提示并以退出码 1 结束，而不是抛一长串 traceback。

关键代码摘录：

```python
df["scraped_at"] = pd.to_datetime(df["scraped_at"])
out = df.sort_values("scraped_at").drop_duplicates("url", keep="last")
print(out)
```

运行（需先装依赖）：

```bash
cd chapter-08
pip install -r requirements.txt   # 只有 pandas>=2.0.0 一项
python pandas_dedupe.py
```

实测输出 —— `t2`（旧的那条 a）被丢弃，`t1`、`t3` 保留，行按时间升序：

```text
         url title scraped_at
2  https://b    t3 2026-01-01
0  https://a    t1 2026-01-02
```

容易踩的坑：`keep="last"` 的「last」指的是**排序后**的位置，不是原始行号；漏掉 `sort_values` 直接用默认顺序去重，留下的就是任意一条而不是最新的。

### 2.4 三个脚本的对照

三个脚本分别代表三种清洗哲学，放在一起看更清楚：

| 脚本 | 清洗对象 | 激进度 | 内容字符会丢吗 | 典型用途 |
|---|---|---|---|---|
| `clean_ngrams.py` | 角标、换行、大小写、非 ASCII | 高 | 会（中文等非 ASCII 被剔除） | 英文语料的词表 / n-gram 统计 |
| `clean_text.py` | 全半角、连续空白 | 低 | 不会（NFKC 只折叠兼容字符） | 多语言正文的表示归一 |
| `pandas_dedupe.py` | 重复抓取记录 | 不涉及字符 | 不涉及（行级操作） | 落库后的增量去重 |

选型建议：统计前想「我要算什么」，算词频可以激进，存档备查必须保守；行级去重与字符级清洗是正交的两件事，别混在一步里做。

---

## 3. 学习贴士

以下几条来自本章脚本实测与常见踩坑，工程化时优先检查：

- **清洗要可逆**。尽量保留原始字段副本，清洗结果写入新列（如 `title` / `title_clean`），规则改错了能重跑，而不是回头重新抓一遍。
- **先排序再去重，顺序不能反**。`drop_duplicates(keep="last")` 的正确性完全依赖前置的 `sort_values`；时间字段先 `pd.to_datetime` 转类型再排，别在字符串上比大小。
- **激进清洗前先问「会不会误伤」**。ASCII 剔除、NFKC 折叠、大小写折叠各有代价，按字段决定用不用 —— 正文可以折叠大小写，人名、缩写词字段就别折。
- **正则越简单越好**。能 `replace` 解决的不用正则（如换行），能一个字符类说清的别堆分支；写完用边界样例（空串、全噪声、无噪声）各测一遍。
- **用频次统计反哺清洗**。清洗不是一次性的：先跑一遍 `Counter.most_common()`，看高频词 / n-gram 里有没有残留的导航文本、模板句，再回头补规则，迭代两三轮比一次写「完美正则」更现实。
- **与 NLP 衔接**：第 9 章的分词、词干化之前，务必先完成本章的噪声裁剪，避免垃圾进垃圾出；反过来，本章的 ASCII 剔除在中文语料上本身就是「垃圾制造机」，多语言项目请直接跳过这一步。

---

## 4. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-08/clean_ngrams.py` | 主示例：`clean_input` 清洗 + `Counter` 统计 2-gram（正则已勘误，已实测） |
| `chapter-08/clean_text.py` | 温和路线示范：NFKC 规范化 + 空白压缩，不伤中文（已实测） |
| `chapter-08/pandas_dedupe.py` | 带时间语义的去重：`to_datetime` + `sort_values` + `drop_duplicates(keep="last")`（已实测） |
| `chapter-08/requirements.txt` | 本章依赖，仅 `pandas>=2.0.0` 一项；只读代码不跑脚本可不装 |
| `chapter-07/`（前置） | 提供原始文本输入：网页 / 文档内容读出后交给本章清洗 |
| `chapter-09/`（后续） | NLP 入口：本章的干净词表是分词、词干化的直接输入 |

---

## 练习建议

1. 把「去角标」规则改成同时支持 `[12]` 与 `(2024)` 两种引用样式，并为每种样式各写一条边界测试（如角标出现在行首、连续两个角标）。
2. 用 pandas 对一列文本做 `str.lower().str.strip()` 后再 `value_counts()`，对比归一化前后的词频 Top 10，体会「统一表示」对统计结果的影响。
3. 改造 `clean_ngrams.py`：把 ASCII 剔除换成 `casefold()` + `unicodedata.normalize`，用一段中英混合文本验证中文不再被误删。
4. 在 `pandas_dedupe.py` 上实验 `keep` 参数：分别用 `"first"`、`"last"`、`False` 跑一次，解释三种输出各自对应的业务语义。
5. 在 OpenRefine 中导入一份 CSV，试用 **facet + cluster** 合并拼写变体（记录操作步骤即可），思考哪些步骤可以反向固化成代码流水线。
6. 给 `clean_input` 补一组单元测试：输入空串、纯角标串（如 `"[1][2][3]"`）、无标点的正常句各一条，断言输出的词表符合预期 —— 体会「先删后换再切分」每一步在边界输入下的行为。
