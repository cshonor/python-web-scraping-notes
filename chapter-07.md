# 第 7 章 读取文档：学习笔记

本章介绍如何抓取并解析 **HTML 以外**的常见格式。网上大量数据还存在于**纯文本、CSV、PDF、Word** 等文件中，掌握读取方法能显著扩展数据来源。

---

## 1. 核心知识点与原理

### 1.1 文档编码（Document Encoding）

编码决定字节如何解释为字符。

- **ASCII**：早期 7 位编码，仅 128 个字符，适合英文。
- **Unicode（UTF-8）**：当前主流；变长 1–4 字节，**兼容 ASCII**。
- **ISO-8859-* 等**：历史遗留单字节区域编码，老站或导出文件中仍会遇到。
- **易错点**：非英语内容出现**乱码**，多为「声明编码 ≠ 实际字节」或 HTTP 头与 `<meta charset>` 不一致。应优先看响应头 **`Content-Type`** 里的 `charset=`，再结合 HTML 的 `<meta charset="utf-8">` 推断；必要时用 **`chardet` / `charset-normalizer`** 猜测。

### 1.2 纯文本（Text）

在线 `.txt` 可用 **`urlopen` + `read().decode(...)`** 拉取。务必显式 **`decode`**（或按字节交给上层统一解码），并对未知字节流使用 **`errors="replace"`** 等策略避免崩溃。

示例脚本：`code/chapter07/read_text_remote.py`

### 1.3 CSV 文件

- **`io.StringIO`**：把内存中的字符串当作「类文件对象」，**无需先落盘**即可交给 **`csv.reader` / `csv.DictReader`**。
- **`csv.DictReader`**：首行当字段名，每行映射为 **`dict`**，可读性优于纯下标索引。

### 1.4 PDF 文件

PDF 强调版式一致，**文本抽取**比 HTML 粗糙。

- 书中常提 **PDFMiner** 系工具；在 Python 3 环境请使用维护中的 **`pdfminer.six`**（`pip install pdfminer.six`）。高层 API 常用 **`extract_text`**；旧版基于 **`process_pdf` / `TextConverter`** 的流程仍可在官方文档中找到对应写法。
- 另可选用 **`pypdf`**（轻量、易上手），见 `code/chapter07/read_pdf.py`（本地文件）。

### 1.5 微软 Word（`.docx`）

`.docx` 实为 **ZIP 包**，核心 XML 在 **`word/document.xml`**。

- **手工思路**：`ZipFile` 解压内存中的字节 → 读 `word/document.xml` → 用 **BeautifulSoup（`xml` 解析器）** 找 **`<w:t>`** 文本节点（与书中一致）。
- **工程替代**：生产环境更常用 **`python-docx`** 直接访问段落/样式（见学习贴士）。

---

## 2. 可直接运行的 Python 示例代码

以下与书中示例对齐；原站若失效，仓库脚本内带有**离线回退数据**或本地文件路径说明。

### 2.1 读取 CSV（无需本地下载）

可运行脚本：`code/chapter07/csv_stringio_remote.py`

```python
from io import StringIO
import csv
from urllib.request import Request, urlopen

url = "http://pythonscraping.com/files/MontyPythonAlbums.csv"
req = Request(url, headers={"User-Agent": "DocReader/1.0"})
raw = urlopen(req, timeout=20).read().decode("ascii", errors="ignore")
data_file = StringIO(raw)
dict_reader = csv.DictReader(data_file)

print("列标题:", dict_reader.fieldnames)
for row in dict_reader:
    print(f"专辑名称: {row['Name']}, 发行年份: {row['Year']}")
```

### 2.2 读取 PDF 文本

书中使用 **PDFMiner 流式转换**；现代等价写法推荐使用 **`pdfminer.six`** 的 **`extract_text`**（见 `read_pdf_remote.py`）。若仅需简单抽取，也可用 **`pypdf`**。

可运行脚本：`code/chapter07/read_pdf_remote.py`（远程 PDF + `pdfminer.six`）

### 2.3 解析 Word（`.docx`）正文

可运行脚本：`code/chapter07/read_docx_zip_bs4.py`

```python
from io import BytesIO
from urllib.request import Request, urlopen
from zipfile import ZipFile

from bs4 import BeautifulSoup

url = "http://pythonscraping.com/pages/AWordDocument.docx"
req = Request(url, headers={"User-Agent": "DocReader/1.0"})
word_file = BytesIO(urlopen(req, timeout=20).read())
document = ZipFile(word_file)
xml_content = document.read("word/document.xml")
word_obj = BeautifulSoup(xml_content.decode("utf-8"), "xml")
for text_elem in word_obj.find_all("w:t"):
    print(text_elem.text)
```

---

## 3. 学习贴士

- **统一 UTF-8**：多语言流水线中尽量在边界处完成解码，内部统一用 **`str`（Unicode）** 处理。
- **区分 Word 样式**：若需区分标题与正文，可结合 **`<w:pStyle>`** 等属性过滤，或改用 **`python-docx`** 的段落样式 API。
- **扫描版 PDF**：以图片为主的 PDF 需 **OCR**（第 13 章）。

---

## 4. 与本仓库其他示例

- **`code/chapter07/read_pdf.py`**：本地 PDF + **`pypdf`**，适合离线实验。

## 练习建议

1. 把 `decode('ascii', 'ignore')` 改为先检测编码再解码，比较输出差异。  
2. 用 **`python-docx`** 重写 `.docx` 读取，与 ZIP+BS4 版本对照段落数。  
3. 对同一远程 PDF 分别用 **`pypdf`** 与 **`pdfminer.six`** 抽取，比较前 500 字差异。
