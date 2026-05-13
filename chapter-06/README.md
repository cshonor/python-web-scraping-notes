# 第 6 章 存储数据：学习笔记

本章介绍抓取结果落地后的常见做法：**媒体文件**、**CSV**、**关系型数据库（MySQL）**，以及如何用 **Email** 做简单自动化通知。

---

## 1. 核心知识点与原理

### 1.1 存储媒体文件

两种常见策略：

- **只存 URL**：省空间、省带宽、对源站压力小，但可能遇到**盗链限制**、链接失效或权限变更。
- **下载到本地**：更接近真实浏览，**持久性**更好，但占磁盘、下载未知文件有**安全风险**（勿用管理员权限乱下可执行文件）。

**常用工具**：标准库 **`urllib.request.urlretrieve`** 可把远程资源保存到本地路径（新版本 Python 中更推荐 **`Request` + `urlopen` + 写文件** 的可控写法，便于设置超时与请求头）。

### 1.2 存储为 CSV

CSV 通用、轻量，适合表格交换与快速分析。

- **标准库 `csv`**：`csv.writer` / `csv.reader` 处理引号、逗号、换行。
- **进阶**：**`csv.DictReader` / `DictWriter`** 按字段名访问列，可读性更好。
- **编码**：写入中文建议 `encoding="utf-8"` 或 **`utf-8-sig`**（便于 Excel 识别 BOM）。

### 1.3 MySQL 数据库存储

中大型项目常用关系型库做聚合与查询。

- **连接方式**：常用 **`PyMySQL`**（纯 Python）或 `mysqlclient`。采用 **Connection + Cursor**：连接管理事务与网络，游标执行 SQL 并取结果集。
- **字符集**：库与表建议使用 **`utf8mb4`**，覆盖完整 Unicode（含 emoji 等四字节字符）。
- **设计习惯**：主键（常为自增 `id`）、合理索引、规范化减少冗余字符串。

### 1.4 Email 通知（SMTP）

通过 **SMTP**，可在任务完成、异常、或命中规则时发送邮件（需邮箱服务商开启 SMTP、使用应用专用密码等）。注意别把账号密码写进公开仓库，宜用**环境变量**或密钥管理。

---

## 2. 异常处理与最佳实践（易错点）

1. **文件下载安全**：未知来源的二进制可能有害；限制保存目录、校验类型、在低权限环境运行。
2. **连接泄漏**：数据库连接与文件句柄用完后**必须关闭**；优先 **`with conn.cursor() as cur:`** 与 **`try` / `finally`**。
3. **SQL 注入**：插入抓取文本时务必使用**参数化** `execute("... %s ...", (val,))`；**不要**字符串拼接 SQL。
4. **去重与幂等**：入库前按业务键（如 URL）查重，或使用 **`INSERT ... ON DUPLICATE KEY UPDATE`** 等幂等策略。

---

## 3. 示例代码

### 3.1 维基表格写入 CSV（书中思路）

原书片段里 `find_all('table', ...)` 返回的是**列表**，不能直接 `.find_all('tr')`；应先取 **`tables[0]`**（或循环多张表）。向维基发请求时务必设置合规 **`User-Agent`**，否则易 **403**（见 `wikitable_to_csv.py`）。

可运行脚本（含超时、HTTPS、User-Agent）：`chapter-06/wikitable_to_csv.py`

书中逻辑修正版示例：

```python
import csv
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

url = "https://en.wikipedia.org/wiki/Comparison_of_text_editors"
req = Request(url, headers={"User-Agent": "YourBot/1.0 (mailto:you@example.com)"})
html = urlopen(req, timeout=30)
bs = BeautifulSoup(html.read(), "html.parser")

tables = bs.find_all("table", {"class": "wikitable"})
if not tables:
    raise SystemExit("未找到 wikitable")
table = tables[0]
rows = table.find_all("tr")

with open("editors.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    for row in rows:
        csv_row = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
        writer.writerow(csv_row)
print("CSV 文件已生成")
```

### 3.2 存储到 MySQL（PyMySQL）

需本机或远程 **MySQL** 服务，并 `pip install pymysql`。密码等敏感信息请用环境变量（见脚本注释）。

可运行脚本：`chapter-06/mysql_pages_demo.py`

```python
import pymysql

conn = pymysql.connect(
    host="127.0.0.1",
    user="root",
    password="password",
    database="mysql",
    charset="utf8mb4",
)

try:
    with conn.cursor() as cur:
        cur.execute("CREATE DATABASE IF NOT EXISTS scraping")
        cur.execute("USE scraping")
        cur.execute(
            """CREATE TABLE IF NOT EXISTS pages (
            id BIGINT NOT NULL AUTO_INCREMENT,
            title VARCHAR(200),
            content VARCHAR(10000),
            PRIMARY KEY (id))"""
        )
        title = "示例标题"
        content = "抓取的网页内容..."
        cur.execute(
            "INSERT INTO pages (title, content) VALUES (%s, %s)",
            (title, content),
        )
        conn.commit()
        print("数据已成功存入数据库")
finally:
    conn.close()
```

### 3.3 Email（SMTP）示意

```python
import os
import smtplib
from email.message import EmailMessage

msg = EmailMessage()
msg["Subject"] = "爬虫任务完成"
msg["From"] = os.environ["SMTP_FROM"]
msg["To"] = os.environ["SMTP_TO"]
msg.set_content("任务已成功结束。")

with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587"))) as s:
    s.starttls()
    s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
    s.send_message(msg)
```

实际参数（端口、TLS、授权码）依邮箱服务商文档配置。

---

## 4. 学习贴士

- **规范化**：若大量重复出现同一 URL、站点名等长字符串，可拆表用 **ID 引用**，节省空间并利于更新。
- **异步与管线**：Scrapy 的 **Pipeline** 可与写入队列/数据库配合，在高并发下更需关心连接池与事务粒度（与第 5、16 章相关）。

---

## 5. 与本仓库其他示例

- **`chapter-06/save_csv_json.py`**：`DictWriter` + **JSON Lines** 小示例。  
- **`chapter-06/sqlite_store.py`**：无 MySQL 时的本地 **`sqlite3`** 落库练习。  
- **`chapter-06/download_urlretrieve.py`**（可选）：演示将远程图片保存到本地（运行生成 `_demo_*.png`，已 `.gitignore`）。

## 练习建议

1. 用 **`csv.DictReader`** 读回 `editors.csv`，打印列名与第一行。  
2. 为 `pages` 表增加 **`url VARCHAR(500) UNIQUE`**，插入前按 URL 去重。  
3. 在 Scrapy Pipeline 中把 Item 写入 MySQL（伪代码 + 连接池思路即可）。
