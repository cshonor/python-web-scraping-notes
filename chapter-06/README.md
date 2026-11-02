# 第 6 章 存储数据：学习笔记

前几章解决的是「怎么把数据抓下来」，本章解决的是「抓下来之后放哪」。核心机制一句话：抓取结果只是内存里的临时对象，必须通过**文件（媒体 / CSV / JSON Lines）**或**数据库（SQLite / MySQL）**落地，任务才算闭环；此外还可以用 **Email（SMTP）** 把「任务完成 / 出错」这件事通知给人。第 5 章的 Scrapy Pipeline 里 `yield` 出来的 Item，最终走的正是本章这些落地路径；而第 8 章以后数据量上来、要做清洗与自然语言处理时，读取的源头也还是本章存好的文件与表。

**本章目标**

1. 理清「只存 URL」与「下载到本地」两种媒体存储策略的取舍
2. 会用标准库 **`csv`（含 `DictWriter`）** 与 **JSON Lines** 落地结构化数据
3. 理解 **Connection + Cursor** 的数据库访问模型，会写**参数化** SQL
4. 会用零依赖的 **`sqlite3`** 做本地落库，并理解它与 MySQL 的差异
5. 知晓 **SMTP 邮件通知**的基本流程与凭据管理原则

---

## 1. 核心知识点与原理

### 1.1 存储媒体文件：存 URL 还是存文件

抓取中遇到的图片、音视频等二进制资源，有两种常见策略：

| 策略 | 优点 | 缺点 |
|---|---|---|
| **只存 URL** | 省空间、省带宽、对源站压力小 | 可能遇到**盗链限制**、链接失效、权限变更，数据「看似存了实则没了」 |
| **下载到本地** | 更接近真实浏览，**持久性**好，可离线复用 | 占磁盘；下载未知文件有**安全风险**（勿用管理员权限乱下可执行文件） |

标准库 **`urllib.request.urlretrieve(url, filename)`** 是最省事的一行式下载写法，`download_urlretrieve.py` 用的就是它。但它的可控性差（不好设超时与请求头），新代码更推荐 **`Request` + `urlopen` + 写文件** 的组合 —— `wikitable_to_csv.py` 抓 HTML 时正是这套写法，同一套思路换成二进制资源再 `open(..., "wb")` 即可。

### 1.2 存储为 CSV 与 JSON Lines

CSV 通用、轻量，适合表格交换与快速分析；JSON Lines（每行一个 JSON 对象）则更适合日志式追加与后续流式处理。

| 工具 | 适用场景 | 要点 |
|---|---|---|
| **`csv.writer`** | 行是列表/元组 | 自动处理引号、逗号、换行的转义 |
| **`csv.DictWriter`** | 行是字典 | `fieldnames` 固定列序，`writeheader()` 先写表头，按字段名访问可读性更好 |
| **`json.dumps` + 换行** | 半结构化记录 | `ensure_ascii=False` 保留中文原文，一行一条便于 `jq` / 逐行读取 |

**编码细节**：写中文 CSV 若要给 Excel 直接双击打开，用 **`encoding="utf-8-sig"`**（带 BOM），否则 Excel 常按本地码表解码出乱码；纯程序间交换用 `encoding="utf-8"` 即可。`save_csv_json.py` 里两种都演示了：CSV 用 `utf-8-sig`，JSONL 用 `utf-8`。

### 1.3 数据库访问模型：Connection + Cursor

中大型项目常用关系型库做聚合与查询。无论 PyMySQL 还是标准库 `sqlite3`，访问模型是同一套：

- **Connection**：管理网络/文件通道与事务，负责 `commit()` / `rollback()` / `close()`。
- **Cursor**：在连接上执行 SQL、取结果集，用完即关（推荐 `with conn.cursor() as cur:`）。
- **事务**：DML（INSERT/UPDATE）默认在事务里，**不 `commit()` 就不会真正落盘**；脚本异常退出时未提交的写入会丢失。

典型一次写入的完整生命周期：

```text
connect() → cursor() → execute(CREATE/INSERT，参数化) → commit() → cursor 关闭 → conn.close()
```

任何一步抛异常，都应保证 `conn.close()` 在 `finally` 中执行，否则连接泄漏会在长任务里慢慢耗尽数据库侧的连接配额。

两条铁律：**字符集用 `utf8mb4`**（MySQL 的老 `utf8` 只支持三字节，存不下 emoji 等四字节字符）；**SQL 一律参数化**，把值交给驱动转义，绝不字符串拼接（详见第 2 节）。

### 1.4 SQLite 与 MySQL 的分工

`sqlite_store.py` 与 `mysql_pages_demo.py` 演示的是同一类操作（建表、插入、提交）在两种库上的形态：

| 维度 | SQLite | MySQL |
|---|---|---|
| 部署 | 标准库自带，一个 `.db` 文件 | 需独立服务进程 |
| 并发写 | 单写者（库级锁） | 多客户端并发 |
| 参数占位符 | `?` | `%s`（注意不是格式化，仍由驱动转义） |
| 适用 | 原型、单机小工具、测试 | 生产、多进程写入、需要权限管理 |

学习阶段可以先用 SQLite 把「建表 — 参数化插入 — 查重」练熟，换到 MySQL 时只需换驱动与连接参数，SQL 思路完全平移。

### 1.5 Email 通知（SMTP）

长任务跑在后台，人不可能一直盯着。通过 **SMTP**，脚本可在任务完成、抛异常或命中规则时发邮件。流程固定四步：构造 `EmailMessage`（Subject/From/To/正文）→ `smtplib.SMTP(host, port)` 连接 → `starttls()` + `login()` → `send_message()`。两个前提：邮箱服务商处**开启 SMTP** 并申请**应用专用密码**（很多服务商已不允许用登录密码直连）；凭据**绝不写进仓库**，用环境变量（`os.environ`）或密钥管理读取。本章没有独立的邮件脚本，原则性示例见第 2 节第 8 条。

---

## 2. 异常处理与最佳实践（易错点）

1. **`find_all` 返回的是列表，不能直接接着 `.find_all`**。书中导出维基表格的片段常写成 `bs.find_all("table", ...).find_all("tr")`，运行即报 `AttributeError: 'ResultSet' object has no attribute 'find_all'`。原因是 `find_all` 返回 `ResultSet`（列表的子类），必须先取 `tables[0]`（或循环多张表）再对单张表找行。`wikitable_to_csv.py` 已按此处理，并对「一张表都没找到」的情况做了显式报错退出。

2. **向维基发请求必须带合规 `User-Agent`**。不带 UA 或用明显伪造的浏览器串，容易被 403 拦下。维基媒体基金会有公开的 UA 政策：写明 bot 名、版本与联系方式即可。`wikitable_to_csv.py` 的 `USER_AGENT` 里附了政策页链接，实测能正常取回页面；使用前建议把 `mailto` 改成自己的联系方式。

3. **BeautifulSoup 指定 `lxml` 解析器而本机没装 lxml**。`wikitable_to_csv.py` 用 `BeautifulSoup(raw, "lxml")`，若环境缺 lxml 会在构造时抛 `bs4.FeatureNotFound`。对策：要么 `pip install lxml`（本章运行环境已装，实测可用），要么把解析器换成标准库的 `html.parser`，速度略慢但零依赖。

4. **文件下载安全与网络异常**。未知来源的二进制可能有害：限制保存目录、校验类型、在低权限环境运行，是底线。网络侧 `urlretrieve` / `urlopen` 可能抛 `HTTPError`（服务器返回错误状态）、`URLError`（连不上）与 `OSError`（本地写盘失败），本章两个下载类脚本都用 `try / except (HTTPError, URLError, OSError)` 捕获并返回非零退出码，而不是让 traceback 糊一脸。

5. **连接与句柄泄漏**。数据库连接和文件句柄用完**必须关闭**：文件用 `with open(...) as f:`（`Path.open` 同理），连接用 `try / finally: conn.close()`，游标用 `with conn.cursor() as cur:`。`mysql_pages_demo.py` 的 `finally` 结构就是标准模板 —— 即使中间 SQL 抛错，连接也一定能释放，不会把数据库侧的连接数占满。

6. **SQL 注入：插入抓取文本时必须参数化**。抓来的标题、正文是完全不可信的输入，若用 f-string 拼 SQL，文本里的一个引号就能破坏语句甚至被注入。正确姿势是把值放进参数元组：`cur.execute("INSERT INTO pages (title, content) VALUES (%s, %s)", (title, content))`；SQLite 对应写法是 `INSERT OR REPLACE INTO pages VALUES (?,?,?)`。两个脚本中的占位符（`%s` 与 `?`）风格不同，但原理一致：**值永远不进 SQL 文本**。

7. **忘记 `commit()`，数据「写了但没有」**。PyMySQL 与 sqlite3 都默认手动提交事务，只 `execute` 不 `commit`，进程退出后数据不落盘。本章三个入库脚本都在插入后显式 `conn.commit()`；在循环批量插入时，应每 N 条提交一次而不是每条提交（性能）或全程不提交（丢数据风险）。

8. **凭据与幂等**。数据库密码、SMTP 授权码不要硬编码进仓库 —— `mysql_pages_demo.py` 全部走 `MYSQL_HOST / MYSQL_USER / MYSQL_PASSWORD / MYSQL_PORT` 环境变量，且未设密码时**优雅跳过**（打印提示、返回 0）而不是报错，这个「宁可不跑也不泄露」的写法值得抄。入库去重则按业务键处理：`sqlite_store.py` 直接以 `url TEXT PRIMARY KEY` + `INSERT OR REPLACE` 实现幂等（重复抓取同 URL 只会覆盖不会堆叠）；MySQL 侧对应思路是加 `UNIQUE` 约束后 `INSERT ... ON DUPLICATE KEY UPDATE`。

---

## 3. 示例代码

五个脚本按「文件 → 表格 → 双格式 → 本地库 → 生产库」的难度梯度排列。除 MySQL 示例外，其余均已在本地用 `python`（requests / bs4 / lxml 已装）实际运行验证，输出为真实结果。

### 3.1 `download_urlretrieve.py`：一行式下载远程图片

演示「下载到本地」策略的最小形态：把 Python 官网的 logo PNG 保存到脚本同目录的 `_demo_python_logo.png`。核心就一行 `urlretrieve(URL, OUT)`，外围包了 `HTTPError / URLError / OSError` 三层异常，失败时向 stderr 打印原因并返回退出码 1。文件路径用 `Path(__file__).resolve().parent` 定位，保证从任何工作目录运行都落在脚本旁边。

```python
from urllib.request import urlretrieve

URL = "https://www.python.org/static/img/python-logo.png"
OUT = Path(__file__).resolve().parent / "_demo_python_logo.png"

urlretrieve(URL, OUT)
print("已保存:", OUT)
```

```bash
cd chapter-06
python download_urlretrieve.py
```

**已实测**：输出 `已保存: .../chapter-06/_demo_python_logo.png`，生成 15770 字节的 PNG（该产物已被 `.gitignore` 忽略）。

### 3.2 `wikitable_to_csv.py`：维基表格导出 CSV

抓取英文维基「Comparison of text editors」页，取第一张 `class="wikitable"` 的表格逐行写进 `editors.csv`。流程：带合规 `User-Agent` 的 `Request` → `urlopen(req, timeout=40)` → `BeautifulSoup(raw, "lxml")` → `find_all` 定位表格后**取 `tables[0]`** → 对每行 `tr` 收集 `td` / `th` 的文本（`get_text(strip=True)`）→ `csv.writer` 以 `utf-8` 写出。表格缺失或网络失败都会打印原因并返回 1。

```python
req = Request(URL, headers={"User-Agent": USER_AGENT})
raw = urlopen(req, timeout=40).read()
bs = BeautifulSoup(raw, "lxml")

tables = bs.find_all("table", {"class": "wikitable"})
if not tables:
    print("未找到 class=wikitable 的表格", file=sys.stderr)
    return 1
for row in tables[0].find_all("tr"):
    csv_row = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
    writer.writerow(csv_row)
```

```bash
cd chapter-06
pip install -r requirements.txt   # 需要 beautifulsoup4（及 lxml）
python wikitable_to_csv.py
```

**已实测**：输出 `CSV 已写入: .../chapter-06/editors.csv`，共 68 行，首行表头为 `Name,Developer,Initial release,...`。

### 3.3 `save_csv_json.py`：DictWriter 与 JSON Lines 双写

纯本地、零网络的小示例：把两条 `{url, title}` 字典分别写成 `sample_output.csv` 和 `sample_output.jsonl`。CSV 侧用 `csv.DictWriter` 固定 `fieldnames=["url", "title"]`，`writeheader()` 先写表头，编码用 `utf-8-sig`（带 BOM，Excel 双击不乱码）；JSONL 侧逐条 `json.dumps(r, ensure_ascii=False)` 加换行，一行一个完整 JSON 对象。

```python
with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["url", "title"])
    w.writeheader()
    w.writerows(rows)

with jsonl_path.open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
```

```bash
cd chapter-06
python save_csv_json.py
```

**已实测**：输出 `wrote .../sample_output.csv .../sample_output.jsonl`；CSV 共 3 行（1 表头 + 2 数据，首行可见 BOM），JSONL 共 2 行，中文场景下 `ensure_ascii=False` 会保留原文。

### 3.4 `sqlite_store.py`：零依赖本地落库

不装任何东西就能跑的关系型存储练习：在脚本同目录建 `pages.db`，建 `pages` 表（`url TEXT PRIMARY KEY, title TEXT NOT NULL, scraped_at TEXT NOT NULL`），以 `?` 占位符参数化执行 `INSERT OR REPLACE`（以 URL 为业务键，重复写入即覆盖，天然幂等），`commit()` 后 `SELECT` 全表打印，最后关连接。

```python
conn = sqlite3.connect(db_path)
conn.execute(
    "INSERT OR REPLACE INTO pages VALUES (?,?,?)",
    ("https://example.com", "Example", "2026-01-01T00:00:00Z"),
)
conn.commit()
for row in conn.execute("SELECT * FROM pages"):
    print(row)
conn.close()
```

```bash
cd chapter-06
python sqlite_store.py
```

**已实测**：输出 `('https://example.com', 'Example', '2026-01-01T00:00:00Z')` 与 `db: .../chapter-06/pages.db`；重复运行结果不变，正好验证 `INSERT OR REPLACE` 的幂等性。

### 3.5 `mysql_pages_demo.py`：PyMySQL 写入 MySQL

生产形态的入库模板。连接参数全部来自环境变量（`MYSQL_HOST / MYSQL_USER / MYSQL_PASSWORD / MYSQL_PORT`，均有默认值），**未设 `MYSQL_PASSWORD` 时打印提示并正常退出**（返回 0），避免把空密码怼到数据库上。连接时指定 `charset="utf8mb4"`，随后建库 `scraping`、建表 `pages`（自增 `id` 主键 + `title` / `content`），用 `%s` 占位符参数化插入一行示例数据，`commit()` 后在 `finally` 里关连接。

```python
conn = pymysql.connect(host=host, port=port, user=user,
                       password=password, charset="utf8mb4")
try:
    with conn.cursor() as cur:
        cur.execute("CREATE DATABASE IF NOT EXISTS scraping")
        cur.execute("USE scraping")
        cur.execute("INSERT INTO pages (title, content) VALUES (%s, %s)",
                    (title, content))
    conn.commit()
finally:
    conn.close()
```

```bash
cd chapter-06
pip install -r requirements.txt   # 需要 PyMySQL
export MYSQL_PASSWORD=yoursecret  # 另需可连的 MySQL 实例
python mysql_pages_demo.py
```

**未实测入库**：本机无 MySQL 实例且当前环境未装 PyMySQL（脚本实测按预期输出 `请先安装: pip install pymysql` 并以退出码 1 结束，验证了依赖检查分支）。具备条件时按上面命令跑通即可。

---

## 4. 学习贴士

- **先文件后库，先 SQLite 后 MySQL**。学习路径上先用 CSV/JSONL 把「写盘」练顺，再用 `sqlite3` 练「建表 — 参数化 — 事务」，最后才上 MySQL。每一步只引入一个新概念，排错时目标明确。
- **幂等优先于去重**。与其「插入前先 SELECT 查一遍」（两次往返还有竞态），不如把业务键设成主键/唯一索引，用 `INSERT OR REPLACE` 或 `ON DUPLICATE KEY UPDATE` 让数据库自己处理冲突 —— 重跑爬虫时这个设计能救命。
- **规范化省空间**。若大量行重复出现同一站点名、来源 URL 等长字符串，拆成两张表用 ID 引用，既省磁盘又让「改一处全改」成为可能；这与第 5 章 Pipeline 里做字段清洗的思路一脉相承。
- **批量插入控制事务粒度**。每行一 `commit` 会被 fsync 拖垮，全程不 `commit` 又怕崩溃全丢；工程上常用「每 500–1000 行提交一次」的折中，并配合断点记录支持续跑。
- **落地格式跟着下游走**。要进 Excel / 给非技术人员看 → CSV（`utf-8-sig`）；要被程序流式消费、追加写 → JSON Lines；要做筛选聚合、多进程并发写 → 数据库。先想清楚「谁会读这份数据」，再选格式，能少返工一次。

---

## 5. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-06/download_urlretrieve.py` | `urlretrieve` 一行式下载图片（已实测，生成 `_demo_python_logo.png`） |
| `chapter-06/wikitable_to_csv.py` | 维基 wikitable 导出 CSV：UA、超时、`tables[0]` 修正（已实测） |
| `chapter-06/save_csv_json.py` | `DictWriter`（`utf-8-sig`）+ JSON Lines 双写（已实测） |
| `chapter-06/sqlite_store.py` | `sqlite3` 建表、`?` 参数化、`INSERT OR REPLACE` 幂等（已实测） |
| `chapter-06/mysql_pages_demo.py` | PyMySQL 环境变量凭据、`utf8mb4`、`%s` 参数化（需 MySQL 实例，未实测） |
| `chapter-06/requirements.txt` | 本章依赖：`beautifulsoup4>=4.12.0`、`PyMySQL>=1.1.0` |

对照第 5 章看：Scrapy 的 Pipeline 只是「把 Item 送过来」，真正的落地动作就是本章这些 —— 把 `process_item` 里的逻辑换成 `csv.writer` / `sqlite3` / `pymysql`，一个能入库的 Scrapy 工程就齐了。

---

## 练习建议

1. 用 **`csv.DictReader`** 读回 `editors.csv`，打印列名与第一行；再试试不加 `utf-8-sig` 写一版，用 Excel 打开对比乱码现象。
2. 给 `save_csv_json.py` 的 rows 加一条含**逗号和双引号**的标题，观察 `csv` 模块如何自动加引号转义，以及 JSONL 侧为何无需关心。
3. 把 `sqlite_store.py` 改成循环插入 1000 条生成数据，分别测试「每条 commit」与「每 200 条 commit」的耗时差异。
4. 给 `mysql_pages_demo.py` 的 `pages` 表增加 **`url VARCHAR(500) UNIQUE`**，插入改用 `INSERT ... ON DUPLICATE KEY UPDATE`，实现按 URL 幂等（需 MySQL 实例）。
5. 参考第 2 节第 8 条的原则，用 `smtplib` + 环境变量写一个「爬虫结束后发通知邮件」的独立小脚本（可用任意支持 SMTP 的邮箱）。
