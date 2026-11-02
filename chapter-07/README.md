# 第 7 章 读取文档：学习笔记

前几章处理的都是 HTML：结构规整、标签语义明确。但互联网上有大量数据根本不在网页里，而是躺在**纯文本、CSV、PDF、Word** 等「文档」格式的文件中。本章解决的核心问题是：**如何把远程或本地的非 HTML 文档变成 Python 里可处理的字符串 / 结构化数据**。机制上只有一句话——先用 HTTP 把字节拉下来（内存中的 `bytes`），再按格式选择对应的解码器或解析库：`decode()` 之于文本、`csv` 之于表格、`pdfminer.six` / `pypdf` 之于 PDF、`zipfile` + XML 解析之于 `.docx`。第 6 章讨论的「存储」解决的是抓到数据后怎么落库，本章则是把「数据源」从 HTML 扩展到文档；第 8 章将继续深入文本清洗与规范化，本章拿到的原始字符串正是它的输入。

**本章目标**

1. 理解**字符编码**的基本概念，能定位并解释乱码成因
2. 掌握用 **`urlopen` + `decode()`** 读取远程纯文本的正确姿势
3. 会用 **`io.StringIO` + `csv.DictReader`** 在内存中解析远程 CSV，不落盘
4. 区分 PDF 文本抽取的两条路线：**`pdfminer.six`**（高保真）与 **`pypdf`**（轻量）
5. 理解 `.docx` 本质是 **ZIP 包**，能手写 `ZipFile` + BeautifulSoup 抽 `<w:t>` 文本
6. 知道每条路线的常见坑与工程替代方案

---

## 1. 核心知识点与原理

### 1.1 文档编码（Document Encoding）

编码决定了「字节序列」如何解释为「字符」。同一段字节，用错编码解码就是乱码。

| 编码 | 特点 | 典型场景 |
|---|---|---|
| **ASCII** | 7 位、仅 128 字符 | 早期英文文本、协议字段 |
| **UTF-8** | Unicode 变长 1–4 字节，**向下兼容 ASCII** | 当前互联网绝对主流 |
| **ISO-8859-*** | 单字节区域编码（西欧、西里尔等） | 老站、旧系统导出文件 |
| **GBK / GB2312** | 中文双字节编码 | 国内老站、旧 Office 文档 |

排查乱码的优先级：

1. 先看 HTTP 响应头 **`Content-Type`** 中的 `charset=`（服务端显式声明，最可信）
2. 再看 HTML 的 `<meta charset="...">`（页面自称，可能与实际字节不符）
3. 都没有时用 **`chardet` / `charset-normalizer`** 统计猜测

`read_text_remote.py` 里的写法就是第 1 条的标准实现：

```python
charset = resp.headers.get_content_charset() or "utf-8"
text = raw.decode(charset, errors="replace")
```

`errors="replace"` 用 `` 替换无法解码的字节，保证程序不崩——对探索性抓取来说，「看到替换符」远比「抛异常中断」友好。

### 1.2 纯文本（Text）

远程 `.txt` 是最简单的文档：HTTP 拿到 `bytes` 后一次 `decode()` 就完事。但恰恰因为简单，两个细节容易被忽略：

- **必须显式解码**。`urlopen().read()` 返回 `bytes`，直接 `print` 或做字符串运算会得到 `b'...'` 字面量或 `TypeError`。
- **解码要在边界完成**。推荐「进系统即转 `str`，内部全程 Unicode，出系统再编码」的流水线，避免中间环节反复猜编码。
- **容错策略按场景选**：`errors="strict"`（默认）遇错即抛，适合数据质量要求高的场合；`errors="replace"` 用替换符占位，适合探索性抓取；`errors="ignore"` 直接丢弃坏字节，最省事但会悄悄丢信息。

### 1.3 CSV 文件

CSV 是纯文本的「结构化特例」：逗号分列、换行分行、首行常作表头。Python 标准库 **`csv`** 直接可用，关键搭档是 **`io.StringIO`**：

| 组件 | 作用 |
|---|---|
| **`io.StringIO`** | 把内存中的字符串包装成**类文件对象**，喂给只认文件接口的 API，**省去落盘** |
| **`csv.reader`** | 按行迭代，每行是 `list[str]`，靠下标取值 |
| **`csv.DictReader`** | 首行作字段名，每行映射为 `dict`，`row["Name"]` 语义清晰 |

`DictReader` 相比 `reader` 的实质收益：**列顺序变化不破坏代码**，且 `fieldnames` 属性可直接检查表头。注意 `csv` 模块只做「分行分列」，编码问题必须在构造 `StringIO` 之前由 `decode()` 解决——`csv` 不接受 `bytes`。

另外两点使用常识：字段内含逗号或换行时，合规的 CSV 会用双引号包裹整字段，`csv` 模块会自动正确处理，不要自己写 `split(",")`；`DictReader` 对「值比表头多/少」的脏行会归入 `None` 键或补 `None` 值，正式管线应检查并计数这类行。

### 1.4 PDF 文件的两条抽取路线

PDF 的设计目标是**版式一致**（在哪打印都一样），而非「语义可提取」。文本在 PDF 内部按绘制指令存储，段落、顺序都可能被打散，因此抽取天然比 HTML 粗糙。Python 生态有两条主流路线：

| 维度 | **`pdfminer.six`** | **`pypdf`** |
|---|---|---|
| 定位 | 高保真布局分析 | 轻量、API 简单 |
| 高层入口 | `pdfminer.high_level.extract_text(fileobj)` | `PdfReader(path).pages[i].extract_text()` |
| 输入 | 文件对象（`BytesIO` 亦可） | 文件路径或流 |
| 适用 | 对文本顺序、版式有要求 | 快速抽取、页级操作（合并/拆分） |
| 安装 | `pip install pdfminer.six` | `pip install pypdf` |

书中旧示例基于 PDFMiner 的 `process_pdf` / `TextConverter` 流式 API；在 Python 3 环境请直接用维护中的 **`pdfminer.six`** 及其高层 `extract_text`，一行等价。本仓库两条路线各占一个脚本：`read_pdf_remote.py`（远程 + pdfminer.six）与 `read_pdf.py`（本地 + pypdf）。

**共性限制**：两类库都只对「文字型 PDF」有效。扫描件本质是图片，需要 OCR（第 13 章）。

### 1.5 微软 Word（`.docx`）本质是 ZIP

`.docx`（OOXML 格式）不是二进制黑盒，而是一个**标准 ZIP 压缩包**：

```text
AWordDocument.docx
├── [Content_Types].xml
├── _rels/
├── word/
│   ├── document.xml   <- 正文全部在这里
│   └── styles.xml     <- 样式定义
└── ...
```

因此「手工路线」完全不需要第三方 Word 库：

1. `urlopen` 拿到 `.docx` 字节 → 包一层 **`BytesIO`**（`ZipFile` 需要可 seek 的文件对象）
2. **`ZipFile.read("word/document.xml")`** 取出正文 XML
3. 用 **BeautifulSoup 的 `xml` 解析器** 解析，**`find_all("w:t")`** 即得全部文本节点

关键认知：Word 里**一个单词可能被拆进多个 `<w:t>`**（每次编辑、拼写检查都可能切断 run）。实测本章示例文档中 "Unfortunately" 被拆成 `Unfortuna` / `t` / `ly` 三个节点——所以逐节点打印会看到碎词，做正式抽取时应拼接同段落的文本。工程上若还要区分标题/正文样式，更推荐 **`python-docx`** 直接读段落对象（见「学习贴士」）。

---

## 2. 可直接运行的 Python 示例代码

以下 5 个脚本均位于 `chapter-07/`，运行前按需安装依赖：

```bash
cd chapter-07
pip install -r requirements.txt   # beautifulsoup4 / pypdf / pdfminer.six
```

所有远程脚本都自带 `User-Agent` 与超时设置；本节标注「实测」的输出均为 2026-11-02 在本机（Python 3）运行的真实结果。

### 2.1 读取远程纯文本：`read_text_remote.py`

演示编码意识的标准写法：从响应头取 `charset`，取不到回退 UTF-8，再 `decode(..., errors="replace")`，只打印前 800 字符避免刷屏。脚本逻辑最短，却是「边界处完成解码」原则的最小范例。

```python
with urlopen(req, timeout=20) as resp:
    raw = resp.read()
    charset = resp.headers.get_content_charset() or "utf-8"
text = raw.decode(charset, errors="replace")
print(text[:800])
```

运行命令：

```bash
python read_text_remote.py
```

**实测（未成功，值得记录）**：示例站该 URL 当前返回 **404**，脚本按预期走异常分支，`stderr` 打印 `请求失败: HTTP Error 404: Not Found` 并以退出码 1 结束。这本身就是一课：远程资源会失效，脚本把异常限定在 `HTTPError / URLError / OSError` 三类并给出可读提示，是文档抓取脚本的及格线。想看到成功输出，把 `URL` 换成任一现存 `.txt`（如 Project Gutenberg 的纯文本）即可。

### 2.2 内存解析远程 CSV：`csv_stringio_remote.py`

核心技巧是 **`StringIO` 免落盘**：远程 CSV 文本直接在内存里交给 `csv.DictReader`。脚本还带一份内置 `FALLBACK` 四行数据——远程失败时降级用本地样例，保证教学演示永远有输出。`row.get("Name", "")` 的写法对缺列也安全。

```python
data_file = StringIO(fetch_csv_text())
dict_reader = csv.DictReader(data_file)
print("列标题:", dict_reader.fieldnames)
for row in dict_reader:
    print(f"专辑名称: {row.get('Name', '')}, 发行年份: {row.get('Year', '')}")
```

运行命令：

```bash
python csv_stringio_remote.py
```

**实测**：远程获取成功，表头为 `['Name', 'Year']`，输出 15 张专辑（从 1970 年 *Monty Python's Flying Circus* 到 2014 年 *Monty Python Sings Again*）。注意真实数据里有个拼写彩蛋 `Cotractual Obligation`——源数据如此，不要替它「纠错」，抓取侧应忠实保留。

### 2.3 本地 PDF + pypdf：`read_pdf.py`

最轻量的 PDF 路线：脚本在**自身同目录**找 `sample.pdf`，用 `pypdf.PdfReader` 打开，只抽**前 3 页**并打印文本总长度。找不到文件时打印放置提示并正常退出（返回 0），适合离线实验。`extract_text()` 可能返回 `None`（空白页），脚本用 `or ""` 兜底——这是 pypdf 使用中最常见的 `TypeError` 来源。

```python
reader = PdfReader(str(pdf_path))
text = ""
for page in reader.pages[:3]:
    text += page.extract_text() or ""
print("前3页文本长度:", len(text))
```

运行命令：

```bash
python read_pdf.py   # 需先在 chapter-07/ 放入 sample.pdf
```

**实测**：用第 2.4 节同款《战争与和平》第一章 PDF 作为 `sample.pdf` 验证（在临时目录运行，未污染仓库），输出 `前3页文本长度: 5294`。

### 2.4 远程 PDF + pdfminer.six：`read_pdf_remote.py`

高保真路线：`urlopen` 下载 PDF 字节 → 包 `BytesIO` → 交给 `pdfminer.high_level.extract_text` 一次抽完，打印前 500 字符与总字符数。`extract_text` 直接接受文件对象，**无需临时文件**，这与 `StringIO` 之于 CSV 是同一思路。

```python
from pdfminer.high_level import extract_text
text = extract_text(BytesIO(data)) or ""
print(text[:500].strip())
print("\n... 总字符数:", len(text))
```

运行命令：

```bash
python read_pdf_remote.py
```

**实测**：成功抽出《战争与和平》第一章全文，开头为 `CHAPTER I "Well, Prince, so Genoa and Lucca are now just family estates..."`，总字符数 **11476**。可以观察到 pdfminer 的断词现象（如 `theBuonapartes` 处空格丢失、行尾连字符残留）——PDF 抽取的「脏」是常态，后接第 8 章的清洗流程正是为此准备的。

### 2.5 解析 `.docx` 正文：`read_docx_zip_bs4.py`

把 1.5 节的原理落成代码：远程字节 → `BytesIO` → `ZipFile` → 取 `word/document.xml` → BeautifulSoup（`xml` 解析器）→ `find_all("w:t")`。脚本健壮性做得较全：远程失败回退读同目录 `sample.docx`；ZIP 里缺 `document.xml`（比如误传 `.doc` 老格式）会明确报错而非崩溃。

```python
zf = ZipFile(BytesIO(raw))
xml_content = zf.read("word/document.xml")
word_obj = BeautifulSoup(xml_content.decode("utf-8", errors="replace"), "xml")
for text_elem in word_obj.find_all("w:t"):
    if text_elem.text:
        print(text_elem.text)
```

运行命令：

```bash
python read_docx_zip_bs4.py
```

**实测**：成功读出标题 `A Word Document on a Website` 及正文。输出中清楚可见 `Unfortuna` / `t` / `ly` 被拆成三行——这正是 1.5 节说的「一个单词跨多个 `<w:t>` run」的实证，正式使用需按段落拼接而非逐节点收集。另一个易错点：解析器必须指定 `"xml"`，用默认 HTML 解析器会错误处理自闭合标签与命名空间。

---

## 3. 学习贴士

- **边界解码，内部统一 Unicode**：所有 `decode()` 集中在「数据进系统」的那一刻完成（并优先用响应头的 `charset`），内部只传 `str`；等出了乱码再在中间层补救，往往已丢失原始字节。
- **内存文件对象是通用钥匙**：`StringIO`（文本）与 `BytesIO`（二进制）让「只认文件」的库直接吃网络字节流，CSV、PDF、ZIP 全适用，省去临时文件管理的麻烦。
- **先分清 PDF 类型再选工具**：文字型用 `pdfminer.six` / `pypdf`；扫描件是图片，别在文本抽取上浪费时间，直接上 OCR（第 13 章）。判断方法：用阅读器框选，选不出文字的基本就是扫描件。
- **Word 抽取按需求分层**：只要纯文本，`zipfile + <w:t>` 够用且零依赖；要段落、样式、表格结构，换 `python-docx`（`document.paragraphs` 自带样式属性），不要自己硬解析 `styles.xml`。
- **远程示例一定会过期**：本章 5 个脚本里 1 个已 404。写教学/演示脚本时内置回退数据（如 `csv_stringio_remote.py` 的 `FALLBACK`），写生产脚本时把 URL 失效纳入监控告警。

---

## 4. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-07/read_text_remote.py` | 远程纯文本 + 响应头 `charset` 解码（示例站已 404，脚本优雅报错） |
| `chapter-07/csv_stringio_remote.py` | `StringIO` + `csv.DictReader` 内存解析远程 CSV，含离线回退数据 |
| `chapter-07/read_pdf.py` | 本地 `sample.pdf` + `pypdf`，抽前 3 页统计长度 |
| `chapter-07/read_pdf_remote.py` | 远程 PDF + `pdfminer.six` 的 `extract_text`，打印前 500 字 |
| `chapter-07/read_docx_zip_bs4.py` | `.docx` 手工路线：`ZipFile` 取 `document.xml`，BS4 抽 `<w:t>` |
| `chapter-07/requirements.txt` | 本章依赖清单（bs4 / pypdf / pdfminer.six），`python-docx` 为注释掉的可选项 |

第 6 章的存储示例解决「抓到之后写哪」，本章解决「从哪抓非 HTML 数据」；两者组合即可构成「文档 → 数据库」的最小流水线。第 8 章的文本清洗将接管本章输出的原始字符串。

---

## 练习建议

1. **编码对比实验**：修改 `read_text_remote.py` 指向一个 GBK 编码的中文文本，分别用「响应头 charset」「强制 UTF-8」「chardet 探测」三种方式解码，对比乱码差异。
2. **CSV 双写法**：把 `csv_stringio_remote.py` 的 `DictReader` 换成 `csv.reader` 实现同样输出，体会下标取值在列顺序变化时的脆弱性；再给远程失败分支加断网测试，验证 `FALLBACK` 生效。
3. **PDF 双库对照**：对同一份 PDF（如《战争与和平》第一章）分别跑 `pypdf` 与 `pdfminer.six`，比较两者前 500 字的空格、断行与连字符处理差异。
4. **docx 拼接修复**：改写 `read_docx_zip_bs4.py`，按 `<w:p>` 段落聚合其中的 `<w:t>` 文本，把被拆碎的单词（如 `Unfortuna`+`t`+`ly`）拼回完整词，对比逐节点打印的旧输出。
5. **python-docx 重写**：安装 `python-docx`，用 `Document(paragraphs)` 重写 `.docx` 读取，与 ZIP+BS4 版本对照段落数与文本一致性。
6. **健壮性加固**：任选一脚本，补充对「Content-Type 与实际格式不符」的防御（如响应声明 PDF 但内容是 HTML 错误页），思考应在哪一层校验魔数（magic bytes）。
