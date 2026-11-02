# 第 12 章 利用 API 抓取数据：学习笔记

前面各章的主线是「拿到 HTML 再解析」，本章换一个入口：**尽量绕过复杂 HTML 与全量 JS 执行，直接从 HTTP API 拿结构化数据**。核心机制一句话：很多页面展示的数据本来就来自后端 JSON 接口，找到这个接口、用最小请求复现它，就能跳过渲染直接取数。这和第 11 章抓 JavaScript 页面并不矛盾 —— 浏览器里那些 Ajax / XHR 请求**本身就是 API 调用**，第 11 章是「让浏览器替我们发这些请求」，本章是「看清这些请求后自己发」。在合规前提下，走 API 通常比解析页面**更省带宽、更稳定、字段更干净**。

**本章目标**

1. 理解 **Web API / REST** 的基本形态：URL 路由、查询参数、JSON / XML 响应体
2. 掌握 **HTTP 方法**（GET / POST / PUT / PATCH / DELETE）的语义分工与爬虫侧的常见用法
3. 了解常见**认证方式**（API Key、Bearer Token、Cookie 会话、OAuth）在请求层面的体现
4. 会用 **`json.loads`** 与 **`requests` 的 `.json()`** 把响应反序列化为 Python 对象并按键路径取值
5. 会用浏览器 **DevTools Network 面板**定位并记录无文档的 XHR 接口，再用 `requests` / `urllib` 复现
6. 建立**速率限制与合规**意识：免费接口的配额、服务条款与密钥管理

---

## 1. 核心知识点与原理

### 1.1 API 概述与 REST 风格

**API（Application Programming Interface）** 定义了软件之间如何请求与响应。对爬虫而言，Web API 的价值在于：服务端直接把**结构化数据**交给你，省掉 HTML 解析与 JS 渲染两层不确定性。

常见形态对比：

| 形态 | 特征 | 爬虫侧体验 |
|---|---|---|
| **REST 风格** | URL 路由表资源（`/posts/1`），查询参数表过滤（`?_limit=5`），HTTP 方法表动作 | 最友好：URL 可读、参数可猜、可用浏览器直接试 |
| **RPC / GraphQL** | 单一端点，动作与条件全在请求体里 | 需要先看懂请求体结构，复现成本略高 |
| **服务端渲染页面** | 数据嵌在 HTML 里 | 就是前几章的老路：解析 DOM |

返回体格式上，**JSON 已成事实标准**：它可与 Python 的 `dict` / `list` 几乎无损互转；XML 在老接口中仍存在，需要用 `xml.etree` 或 lxml 解析，繁琐得多。判断一个接口返回什么，看响应头 **`Content-Type`**（`application/json` 还是 `text/html`）最快。

读懂一个 REST 接口的 URL 也有固定套路，以本章实际调用的地址为例：

```text
http://ip-api.com/json/50.78.253.58?fields=status,message,country
\___/   \_________/ \_________________/ \_______________________/
 scheme     host        路径（资源）          Query（过滤/选项）
```

- **路径**段通常按「集合 / 单条资源」层级组织（`/posts`、`/posts/1`、`/posts/1/comments`）；
- **Query** 段是 `key=value` 对、以 `&` 连接，常承担分页（`page`、`limit`）、筛选、字段裁剪（`fields`）的职能；
- 手动拼 Query 容易在转义上翻车，`requests` 的 **`params=` 字典参数**会自动拼接并 URL 编码，本章 `json_placeholder.py` 用的就是它。

另外，无论接口多「友好」，都要先看 **HTTP 状态码**再谈解析：`200` 成功、`4xx` 是请求方问题（参数错、未认证、超限）、`5xx` 是服务端故障。`requests` 侧用 **`raise_for_status()`** 一行就能把 4xx/5xx 变成异常；`urllib` 侧 `urlopen` 遇到错误状态会直接抛 `HTTPError`，本质上等价。

### 1.2 HTTP 方法（常见语义）

| 方法 | 语义 | 幂等 | 爬虫侧典型场景 |
|---|---|---|---|
| **GET** | 读取资源，**不应**产生服务端副作用 | 是 | 抓取主力；参数全在 URL Query 里，缓存友好 |
| **POST** | 提交数据、触发动作 | 否 | 登录、表单搜索、GraphQL 查询、翻页接口 |
| **PUT** | 整体更新资源 | 是 | 公共只读 API 中少见 |
| **PATCH** | 部分更新资源 | 否 | 公共只读 API 中少见 |
| **DELETE** | 删除资源 | 是 | 爬虫几乎用不到 |

抓取场景 **90% 以上是 GET**。需要留神的是 POST 型接口：参数不再暴露在 URL 里，而藏在请求体中，复现时必须在 Network 面板里看清 **Payload** 再照搬。POST 请求体有两种主流编码，写代码前要先分清：

| 编码（`Content-Type`） | 形态 | `requests` 写法 |
|---|---|---|
| `application/x-www-form-urlencoded` | `a=1&b=2`，传统表单 | `requests.post(url, data={...})` |
| `application/json` | JSON 文本 | `requests.post(url, json={...})` |

两者用错会得到 400 或「参数缺失」类的报错，而错误信息往往不点破原因 —— 抓包时对一下 `Content-Type` 头能省半小时调试。具体接口的语义以各站文档为准，不要凭方法名臆测。

### 1.3 认证方式

公开 API 未必「无门槛」，常见认证在请求层面的体现：

| 方式 | 出现位置 | 典型形态 |
|---|---|---|
| **API Key** | Query 参数或自定义头 | `?api_key=...`、`X-API-Key: ...` |
| **Bearer Token** | `Authorization` 头 | `Authorization: Bearer <token>` |
| **Cookie 会话** | `Cookie` 头 | 浏览器登录后由 DevTools 复制，注意时效与绑定 IP/UA 的限制 |
| **OAuth 2.0** | 先换 token 再带 token | 流程最重：授权 → 回调 → access_token → 调接口 |
| **无认证** | —— | 本章两个示例均属此类（但有速率/用途限制） |

铁律：**任何密钥都不进 Git 仓库**。Token 放环境变量（`os.environ`）或密钥库，脚本里只读不写；把带 Cookie 的 HAR / cURL 导出文件也当敏感文件处理，别随手提交。环境变量读取的标准写法：

```python
import os

api_key = os.environ.get("MY_API_KEY")
if not api_key:
    raise SystemExit("请先设置环境变量 MY_API_KEY")
```

「未配置就明确报错退出」比「拿着 None 去请求然后收到看不懂的 401」友好得多，这个分支写法值得养成习惯。

### 1.4 解析 JSON

拿到 JSON 文本后有两条等价路径：

```python
# 路径 A：标准库（urllib 场景）
import json
data = json.loads(raw_text)

# 路径 B：requests 一步到位
data = requests.get(url, timeout=20).json()
```

反序列化后就是普通 Python 对象，按**键路径**取值：`data["country"]`、`posts[0]["title"]`。工程上建议用 **`.get()`** 配默认值或显式校验，而不是裸 `data["x"]` —— 接口字段缺失或改版时，前者可控降级，后者直接 `KeyError`。本章 `geo_ip_api.py` 先查 `data.get("status") != "success"` 再取 `country`，就是这个思路：先验证接口层的业务状态，再相信字段存在。

注意 `.json()` / `json.loads` 在响应不是合法 JSON 时会抛 `JSONDecodeError`（如网关故障返回 HTML 错误页），生产代码应对其捕获。JSON 取值阶段的常见坑汇总：

| 坑 | 现象 | 对策 |
|---|---|---|
| 字段缺失 / 接口改版 | `KeyError` | 用 `.get()` 配默认值，或先校验再取 |
| 层级比想象深 | 取到 dict 还想当字符串用 | 先 `print(json.dumps(data, indent=2))` 看清结构再写路径 |
| 响应不是 JSON | `JSONDecodeError` | 捕获之，并打出响应前几百字符帮助定位 |
| HTTP 错误页也是 200 | 解析拿到 HTML 文本 | 先查 `Content-Type` / 业务状态字段 |
| 数字被包成字符串 | `"123"` 参与算术报错 | 取值后显式 `int()` / `float()` 转换 |

### 1.5 速率限制与礼貌调用

免费 API 几乎都有配额，常见限制维度与应对：

| 限制维度 | 典型表现 | 应对 |
|---|---|---|
| **每分钟/每天请求数** | 429 状态码、`Retry-After` 头 | 请求间 `sleep`、指数退避 |
| **并发连接数** | 连接被重置、403 | 控制并发，别开线程池猛打 |
| **用途限制** | 条款禁止商用/大规模抓取 | 读条款；生产换带 SLA 的付费服务 |
| **来源限制** | 要求注册、绑定 Referer | 按文档注册，别伪造 |

本章用的 `ip-api.com` 免费层就是典型：非 HTTPS、有每分钟配额、限非商业用途 —— 教学够用，生产请换正式供应商。**看到 429 就退避，而不是换个 IP 继续打**，这是礼貌也是自保。

一个最小可用的退避重试骨架（供练习 1 参考，不属本章脚本）：

```python
import time
import requests

for attempt in range(3):
    r = requests.get(url, timeout=20)
    if r.status_code == 429:
        time.sleep(2 ** attempt)   # 1s, 2s, 4s
        continue
    r.raise_for_status()
    break
else:
    raise RuntimeError("重试 3 次仍失败")
```

要点：**固定间隔不如指数退避**（撞上限流窗口时固定节奏会持续挨打），重试要有**上限**，且只对 429 / 5xx 这类「可能自愈」的错误重试，4xx 参数错误重试一万次也不会成功。

---

## 2. 查找与记录无文档 API

许多站点用 Ajax 拉取 **JSON** 而不是把数据嵌进首屏 HTML。这类接口没有文档，但浏览器 DevTools 能把它们完整暴露出来。可操作的抓包流程：

1. **提前开面板**：在刷新 / 翻页 / 点筛选**之前**打开 DevTools（F12）的 **Network** 标签，避免漏抓首屏请求。
2. **收窄范围**：过滤器选 **Fetch/XHR**（老版叫 XHR），把 CSS / 图片 / 字体噪音滤掉；可按响应类型 `json`、路径关键词（`api`、`graphql`、`list`、`search`）进一步搜。
3. **触发动作**：在页面上执行一次目标操作（翻页、下拉加载、切换筛选），观察新增请求。
4. **逐个核对**：看每条请求的 **Initiator**（哪个 JS 文件发起的）、**Payload**（Query 与请求体）、**Preview / Response**（返回结构是不是想要的数据）。
5. **记录与导出**：右键请求 → **Copy as cURL**，或整体 **Save all as HAR**；重点记下方法、URL、Query、`Authorization` / `Cookie` / `X-Requested-With` 等关键头、分页参数（`page` / `cursor` / `offset`）。
6. **最小化复现**：把 cURL 翻译成 `requests`，然后**逐头做减法** —— 每次删一个非必要头再请求一次，找到「能通的最小集合」。只带必需头的脚本最抗改版。
7. **验证翻页规律**：手动改分页参数发几发，确认是页码、游标还是偏移量，写循环时才知道终止条件。

三种分页参数的识别与循环终止条件对照：

| 分页类型 | 参数长相 | 下一页怎么来 | 终止条件 |
|---|---|---|---|
| **页码** | `page=2&size=20` | 页码 +1 | 返回空列表 / 条数不足一页 |
| **偏移量** | `offset=40&limit=20` | offset += limit | 同上 |
| **游标** | `cursor=eyJpZCI6...` | 从**本次响应里**取下一游标 | 响应不再给游标 |

游标型最容易写错：下一页的凭证藏在上一页的响应体里（如 `next_cursor`），不能自己编。抓包时连续翻两三页、对比请求参数的变化规律，就能判断属于哪种。

**合规提醒**：以上方法解决的是「读懂自己的浏览器在干什么」。未公开的内部接口可能受服务条款或法律保护；「技术上能访问」不等于「有权抓取」。商业或大规模使用前请评估授权，并参考第 18 章关于法律与伦理的内容。

---

## 3. 代码示例：解析 IP 地理位置（书中思路的现代替代）

书中曾用 **`ip.taobao.com`** 的接口演示「调 API 查 IP 归属地」；该服务已**长期不可用**。本章给出两个等价现代替代：一个用标准库 `urllib + json` 调公共 `ip-api.com`，一个用 `requests` 调 `jsonplaceholder` 练习列表型 JSON。两个脚本均于 **2026-11-02** 在本地实测通过（`requests` 已装，Python 为 `~/.workbuddy/binaries/python/envs/default/bin/python`）。

### 3.1 `geo_ip_api.py`：urllib 查询 IP 所在国家

零第三方依赖的最小 API 调用示例。`get_country(ip)` 拼接 `http://ip-api.com/json/{ip}?fields=status,message,country`（用 `fields` 参数让接口只返回需要的字段，省带宽），带上标识用途的 `User-Agent` 头，用 `urlopen(req, timeout=15)` 发请求；网络层异常（`HTTPError` / `URLError` / `OSError`）捕获后向 stderr 打印原因并返回 `None`。JSON 解析后先校验业务状态 `status == "success"`，失败（如保留 IP、查询超限）时打印整个响应体再返回 `None`，成功则返回 `country` 字段。`main()` 用书中同款 IP `50.78.253.58` 演示，查询成功返回退出码 0，失败返回 1。

```python
url = f"http://ip-api.com/json/{ip_address}?fields=status,message,country"
req = Request(url, headers={"User-Agent": "Chapter12GeoDemo/1.0 (educational)"})
try:
    with urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8")
except (HTTPError, URLError, OSError) as e:
    print("请求失败:", e, file=sys.stderr)
    return None

data = json.loads(raw)
if data.get("status") != "success":
    print("接口返回非 success:", data, file=sys.stderr)
    return None
return data.get("country")
```

```bash
cd chapter-12
python geo_ip_api.py
```

**已实测（2026-11-02）**：输出 `50.78.253.58 -> United States`，退出码 0。该接口免费层仅支持 HTTP 且有每分钟配额，频繁调用会收到 `status: "fail"` —— 脚本对此已有分支处理，正好可用来观察限速行为。

### 3.2 `json_placeholder.py`：requests 拉取列表型 JSON

列表型接口的最小练习：调 `jsonplaceholder.typicode.com`（免费的测试用假 REST API，无需注册）的 `/posts` 端点，`params={"_limit": 5}` 让 requests 自动把查询参数拼进 URL。`raise_for_status()` 先把 HTTP 层错误（4xx/5xx）变成异常，`.json()` 一步反序列化得到字典列表；随后遍历打印每条的 `id` 和 `title`，标题超过 50 字符截断并补 `...`。整个主流程五行代码，对比 3.1 的 urllib 写法能直观体会 requests 的省事程度。

```python
BASE = "https://jsonplaceholder.typicode.com"

r = requests.get(f"{BASE}/posts", params={"_limit": 5}, timeout=20)
r.raise_for_status()
posts = r.json()
for p in posts:
    print(p["id"], p["title"][:50] + ("..." if len(p["title"]) > 50 else ""))
```

```bash
cd chapter-12
pip install -r requirements.txt   # 仅需 requests>=2.31.0
python json_placeholder.py
```

**已实测（2026-11-02）**：输出 5 行 `id + 截断标题`，首行为 `1 sunt aut facere repellat provident occaecati excep...`，末行为 `5 nesciunt quas odio`，退出码 0。

两个脚本的对照正好覆盖了本章「两种 HTTP 客户端」与「两种 JSON 形态」的组合：

| 维度 | `geo_ip_api.py` | `json_placeholder.py` |
|---|---|---|
| HTTP 客户端 | 标准库 `urllib.request` | 第三方 `requests` |
| 响应形态 | 单个对象（`{"status": ..., "country": ...}`） | 对象列表（`[{...}, {...}, ...]`） |
| 失败处理 | 捕获网络异常 + 校验业务 `status` 字段 | `raise_for_status()` 抛 HTTP 层异常 |
| 依赖 | 零（标准库） | `requests>=2.31.0` |

学 API 调用，先把这两个最小形态吃透 —— 单对象按键取、列表逐条遍历 —— 后面再复杂的接口也只是这两者的嵌套组合。

---

## 4. 学习贴士

- **API 优先**：能走文档化或稳定的 JSON 源，就不要先上全页浏览器自动化。先花十分钟在 Network 面板里翻一翻，常常能省下整套 Selenium / Playwright 的复杂度。
- **密钥管理**：Token 放环境变量或密钥库，**不要**写进 Git；Copy as cURL 出来的内容带 Cookie，等同账号凭据，导出后妥善处理。
- **先校验业务状态再取字段**：HTTP 200 不代表成功，很多接口用 body 里的 `status` / `code` 表业务结果（3.1 的 `status != "success"` 分支即此）。裸取下标的代码在接口改版时第一个崩。
- **超时是底线配置**：`urlopen(..., timeout=15)`、`requests.get(..., timeout=20)`，本章两个脚本都显式设了。不设超时的脚本会在线路抖动时无限挂起，批量任务里一颗老鼠屎坏一锅粥。
- **改版必然发生，把脚本写得「易改」**：URL、UA、分页参数集中放在文件顶部常量里；解析逻辑和请求逻辑分开成函数。接口路径变了改一行，比在一坨过程代码里翻强得多。

---

## 5. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-12/geo_ip_api.py` | 标准库 `urllib + json` 调 ip-api.com 查 IP 归属国（已实测，2026-11-02） |
| `chapter-12/json_placeholder.py` | `requests` 调 jsonplaceholder 拉 5 条 posts（已实测，2026-11-02） |
| `chapter-12/requirements.txt` | 本章依赖：仅 `requests>=2.31.0`（`geo_ip_api.py` 为零依赖） |

对照第 11 章看：那里用 Selenium 驱动浏览器执行 JS、等 Ajax 完成后从 DOM 取数；本章则是绕过浏览器直接调那些 Ajax 背后的接口。同一个数据源，两条路径 —— 能用本章方式解决的，就别动用浏览器。

---

## 练习建议

1. 给 `get_country` 增加**重试**：遇 429 / 5xx 时按 1s、2s、4s 指数退避重试 3 次，仍失败返回 `None`。
2. 把 `geo_ip_api.py` 用 **`requests.get(...).json()`** 重写一版，对比与 urllib 版的代码量与可读性差异。
3. 调 `jsonplaceholder` 的 `/posts/1/comments` 端点，练习「资源嵌套」式 URL，并把结果存成 JSON Lines（衔接第 6 章存储）。
4. 在 Network 面板里找一条真实**分页 API**，确认其分页参数类型（页码 / 游标 / 偏移），用循环拉取直到空页或达到上限。
5. 给 `json_placeholder.py` 加 `--limit` 命令行参数（`argparse`），并把超时做成可选配置，体会「常量集中管理」的好处。
6. 挑一个需要 API Key 的公开服务（如天气类），把密钥放环境变量里读取，验证「未设密钥时优雅报错退出」的分支写法。
