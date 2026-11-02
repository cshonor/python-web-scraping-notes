# 第 10 章 穿越网页表单与登录窗口：学习笔记

前几章抓的页面默认「谁都能看」，本章面对的是另一堵墙：表单与登录窗口。核心机制一句话：**表单提交本质是把字段按约定编码进 HTTP 请求（查询串、表单体或 multipart），登录态本质是服务端用 Cookie 给浏览器发一张「通行证」，而 `requests.Session` 负责自动保管并在后续请求中出示这张通行证**。只要把这两件事放对位置，纯 `requests` 就能穿过大多数传统登录页。本章上承第 3、4 章的「无需身份」抓取，也为后面遇到 JavaScript 渲染、验证码与反爬时判断「该不该继续用 requests」打底。

**本章目标**

1. 分清 **GET / POST** 以及 **`params` / `data` / `json` / `files`** 四种参数去向与对应 Content-Type
2. 理解 **Cookie / Set-Cookie** 的会话维持机制，知道手动复制 Cookie 的局限
3. 会用 **`requests.Session`** 完成「POST 登录 → 携带 Cookie 访问受保护页」的完整流程
4. 会用 **`files=`** 以 multipart/form-data 上传文件
5. 会用 **`HTTPBasicAuth`** 访问返回 401 的 HTTP Basic 保护资源
6. 知晓本章工具链在**验证码、CSRF、二次验证**面前的边界与应对思路

---

## 1. 核心知识点与原理

### 1.1 HTTP 方法与表单编码：GET、POST 与四种参数去向

HTML 表单常见两种提交方法：

| 方法 | 字段位置 | 典型用途 | 副作用 |
|---|---|---|---|
| **GET** | URL 查询串 | 搜索、翻页等「读取型」操作 | 无（可重复、可收藏） |
| **POST** | 请求体 | 登录、下单、提交内容等「写入型」操作 | 有（刷新会提示重复提交） |

在 `requests` 里，决定「字段去哪」的是你选的参数名，而不是请求方法本身：

| 参数 | 字段位置 | 请求体 Content-Type | 适用场景 |
|---|---|---|---|
| **`params=`** | URL 查询串（对 POST 同样生效） | —（请求体为空） | 查询、筛选；少数「类 GET」的接口 |
| **`data=`**（dict） | 请求体 | `application/x-www-form-urlencoded` | 绝大多数 HTML 登录/提交表单 |
| **`json=`** | 请求体 | `application/json` | REST API |
| **`files=`** | 请求体 | `multipart/form-data; boundary=...` | 文件上传、含文件的表单 |

**最常见的两个坑都出在这一节**：

- **字段名抄错**：Python 字典的键必须与 HTML 里 `<input name="...">` 的 `name` 属性一字不差（大小写敏感）。把 `username` 写成 `user_name`，服务器只当少传了字段，返回的往往还是 200，只是登录失败 —— 典型的「静默失败」。
- **位置放错**：本章 2.1 节就是活教材 —— 原书把登录字段放在 `params=`（查询串），当年可行；2026-11-02 实测该站点已只认 `data=`（表单体），用 `params=` 提交返回 200 但不下发 Cookie，直接判为登录失败。**判断登录是否成功要看响应体与 Cookie，不能只看状态码。**

另外两条纪律也值得记牢：**登录绝不用 GET**（密码会出现在 URL 里，进而落进浏览器历史、代理日志与服务器访问日志）；**POST 要设 `timeout`**，否则网络抖动时脚本会无限期挂起，本章两个脚本都显式传了 20–25 秒。

### 1.2 Cookie 机制：无状态 HTTP 的「通行证」

HTTP 本身无状态，服务器无法把两个请求关联成「同一个人」。Cookie 是补丁，流程固定三步：

1. 登录 POST 成功后，服务器在响应头里下发 **`Set-Cookie`**（本章实测得到的是 `loggedin=1, username=Ryan`）。
2. 浏览器（或 `requests.Session`）把 Cookie 存下来，之后对同域名的每个请求自动带上 **`Cookie`** 请求头。
3. 服务器凭 Cookie 里的会话标识查出「你是谁」，放行受保护页。

`Set-Cookie` 除了「名=值」还带一组属性，读 Network 面板时应对得上号：

| 属性 | 作用 | 对爬虫的意义 |
|---|---|---|
| `Expires` / `Max-Age` | 过期时间；缺省为会话 Cookie，浏览器关闭即失效 | 关掉 Session 对象就丢，重跑脚本必须重新登录 |
| `Domain` / `Path` | 作用域：哪些域名、哪些路径下的请求才携带 | 换子域名或路径后 Cookie「消失」，先查作用域 |
| `HttpOnly` | 禁止 JavaScript 读取 | 对 requests 无影响（它不执行 JS） |
| `Secure` | 仅经 HTTPS 发送 | 把 URL 从 https 改回 http 会导致 Cookie 不带 |

两条工程结论：

- **手动复制 Cookie 到 `headers["Cookie"]` 是反模式**：从浏览器开发者工具里抄出来的 Cookie 易过期、难维护，账号在别处退出或会话轮换后整段代码无声失效。一次性调试可以这么干，正式代码一律用 Session（见 1.3）。
- **Cookie 有过期与作用域**：`Expires / Max-Age` 决定活多久，`Domain / Path` 决定带去哪。长期任务应设计「检测登录态失效 → 重新走登录流程」的回路，而不是把 Cookie 持久化到磁盘指望它永远有效。

### 1.3 `requests.Session`：登录流程的默认推荐

`requests.Session()` 是一个带状态的请求工厂，解决三件事：

- **自动 Cookie 管理**：响应里的 `Set-Cookie` 自动存入 `session.cookies`（可用 `get_dict()` 查看），后续请求自动携带，不需要手工拼任何头部。
- **连接复用**：底层用 urllib3 的连接池做 keep-alive，对同站点多请求明显省时。
- **共享配置**：`session.headers["User-Agent"] = "..."` 设一次，整个会话生效；`auth`、默认超时策略同理。

最小骨架：

```python
import requests

session = requests.Session()
session.headers["User-Agent"] = "Chapter10Cookies/1.0 (educational)"

r = session.post("https://example.com/login",
                 data={"username": "Ryan", "password": "password"},
                 timeout=25)
r.raise_for_status()
print("Cookie:", session.cookies.get_dict())

r2 = session.get("https://example.com/profile", timeout=25)
print(r2.text[:800])
```

注意 **`raise_for_status()`** 只挡 4xx/5xx，挡不住「200 但登录失败」，所以登录后应再请求一个受保护页验证身份 —— 2.1 节的脚本正是这个结构。

### 1.4 文件上传：multipart/form-data

带 `<input type="file">` 的表单不能用 `data=`，要用 **`files=`**。值可以是文件对象，也可以是 `(文件名, 文件对象, MIME 类型)` 三元组，以便自定义服务器看到的文件名：

```python
import io

import requests

buf = io.BytesIO(b"hello from crawler")
buf.seek(0)
r = requests.post(
    "https://httpbin.org/post",
    files={"file": ("note.txt", buf, "text/plain")},
    timeout=30,
)
print(r.status_code, r.json().get("files"))
```

**已实测（2026-11-02）**：输出 `200 {'file': 'hello from crawler'}`，httpbin 回显的请求头为 `multipart/form-data; boundary=...`，内容正确送达。

**Content-Type 的一个常见误解**：用 `files=` 时**不要手动设置 `Content-Type: multipart/form-data`** —— multipart 的 `boundary` 分隔串由 requests 现场生成并拼进头部，手工指定一个没有 boundary 的 Content-Type 反而让服务器解不出字段。`data=` 与 `json=` 同理：编码方式和对应头部都交给库处理，人只管键值。

### 1.5 HTTP 基本认证（HTTP Basic Auth）

另一类「登录窗口」根本不用表单：服务器直接返回 **401** 加 `WWW-Authenticate: Basic ...` 头，浏览器于是弹出系统级账号密码框。凭据以 `base64(user:pass)` 的形式放进 `Authorization` 请求头（注意 Base64 只是编码不是加密，所以 Basic 必须配合 HTTPS）。

```python
import requests
from requests.auth import HTTPBasicAuth

r = requests.get(
    "https://httpbin.org/basic-auth/user/pass",
    auth=HTTPBasicAuth("user", "pass"),
    timeout=25,
)
```

**已实测（2026-11-02）**：带 `auth` 返回 `200 {'authenticated': True, 'user': 'user', ...}`；不带 `auth` 返回 `401`。也可直接传元组 `auth=("user", "pass")`，效果等价。

与表单登录的区别：Basic 是**每次请求都带凭据**、无会话概念；表单登录是**一次凭据换一张 Cookie 通行证**。前者常见于路由器、内网工具与 API 网关，后者才是绝大多数网站的形态。

### 1.6 验证码、CSRF 与二次验证：本章工具链的边界

纯 `requests` 能做的事可以概括成一句：**在完全知道协议细节后，精确重放浏览器的行为**。一旦站点故意把协议搞复杂，边界就到了：

| 机制 | 为什么难 | 工程上的应对 |
|---|---|---|
| **CSRF / 隐藏 token** | 登录表单内嵌一次性 `_token`，每次 GET 登录页都会变 | 先 **GET 登录页**，用 BeautifulSoup 解析隐藏域，把 token 一起 **POST** 回去（同一 Session 内，Cookie 才连贯） |
| **图片验证码 / 滑块** | 设计目标就是区别人机 | 不绕过：降低频率、走官方 API、人工介入；这是合规红线 |
| **短信 / 扫码二次验证** | 凭据之外还要持有设备 | 改用官方 OAuth / API，或人工登录后复用会话（注意会话安全） |
| **JavaScript 渲染的登录** | 表单由 JS 动态生成，HTML 源码里看不到字段 | 先用 Network 面板确认请求是否真是 JS 发出的；是就换浏览器自动化方案（后续章节展开） |

判断流程：**先在浏览器 Network 面板把真实登录请求（URL、方法、表单字段、Cookie）抄清楚**；如果纯表单 + Cookie 就能复现，用 requests 最划算；一旦出现验证码或重度 JS 依赖，不要硬磕。

---

## 2. 代码示例：使用 Session 保持登录状态

书中示例站点若改版或下线，请以浏览器 **Network 面板** 为准调整 URL 与字段名 —— 本节 2.1 就是一次真实的「站点改版」记录。两个脚本均在 `requests>=2.31.0`（见 `requirements.txt`）环境下实测。

### 2.1 `session_cookies_welcome.py`：Session + Cookie 登录闭环

演示「POST 登录 → Session 自动带 Cookie → GET 受保护页」的完整闭环。脚本建一个 `requests.Session`，设置标识性的 `User-Agent`，向 `welcome.php` 提交用户名密码后打印 `session.cookies.get_dict()`，再用同一 Session 请求 `profile.php` 并打印前 800 字符。网络层用 `try / except requests.RequestException` 兜底，两次请求都 `raise_for_status()` 并设 25 秒超时，失败时向 stderr 打印原因并返回退出码 1。注意脚本**保留了原书的 `params=` 写法**（字段走查询串），并在注释里提醒：若站点改为表单体提交，应改用 `data={...}`。

```python
session = requests.Session()
session.headers["User-Agent"] = "Chapter10Cookies/1.0 (educational)"

r = session.post(
    "https://pythonscraping.com/pages/cookies/welcome.php",
    params={"username": "Ryan", "password": "password"},  # 原书写法：字段在查询串
    timeout=25,
)
r.raise_for_status()
print("Cookie:", session.cookies.get_dict())

r2 = session.get("https://pythonscraping.com/pages/cookies/profile.php", timeout=25)
print(r2.text[:800])
```

```bash
cd chapter-10
pip install -r requirements.txt
python session_cookies_welcome.py
```

**已实测（2026-11-02，退出码 0）**，但结果是一堂生动的反面课：

```text
Cookie: {}
You're not logged into the site!<br>Visit <a href="login.html">the login page</a> to log in
```

脚本运行**没有任何异常**，站点却悄悄拒绝登录 —— 因为它现在只认表单体提交。随后用同 URL 做了一次探测（不改脚本，只把 `params=` 换成 `data=`），两种方式的对比如下：

| 提交方式 | 状态码 | `Set-Cookie` | `profile.php` 回显 |
|---|---|---|---|
| `params=`（脚本现状） | 200 | 无 | `You're not logged into the site!` |
| `data=`（探测改写） | 200 | `loggedin=1, username=Ryan` | `Hey Ryan! Looks like you're still logged into the site!` |

结论：**`params` 与 `data` 放错位置的症状就是「200 但登录失败」；排查时看响应体和 Cookie，而不是看状态码。**

### 2.2 `session_post.py`：对 httpbin 的 `data=` POST 演示

最小的「字段放对位置」正例：用 `requests.Session()` 向 `https://httpbin.org/post` 以 `data={"user": "demo", "token": "abc"}` 提交表单，`raise_for_status()` 后解析 JSON 响应，把 httpbin 回显的 `form` 字段的键排序打印。httpbin 会原样返回它收到的请求内容，因此这个脚本能直接验证「`data=` 的字段确实进了表单请求体」。

```python
import requests

s = requests.Session()
r = s.post("https://httpbin.org/post",
           data={"user": "demo", "token": "abc"}, timeout=20)
r.raise_for_status()
data = r.json()
print("form keys in json:", sorted(data.get("form", {}).keys()))
```

```bash
cd chapter-10
python session_post.py
```

**已实测（2026-11-02，退出码 0）**：输出 `form keys in json: ['token', 'user']`。两个字段都落在响应 JSON 的 `form` 对象里，说明 `application/x-www-form-urlencoded` 编码的请求体被服务器正确解析 —— 这正是绝大多数 HTML 登录表单期待的形态。

顺手用同一端点做了对照实验：把 `data=` 换成 `params=`，同样的字段改落在响应的 **`args`** 对象里（`args: ['token', 'user']`、`form: []`）。httpbin 把查询串放 `args`、表单体放 `form`，所以下次不确定字段到底发去了哪，把目标换成 httpbin 跑一次就一目了然。

---

## 3. 学习贴士

- **警惕蜜罐字段**：提交前检查表单里有没有 `display:none`、`visibility:hidden` 或藏在视口外的输入框。真人不会填的字段，爬虫填了就是自报家门。正确做法是**只提交浏览器 Network 面板里真实出现的字段**，不要「好心」把 HTML 里所有 `input` 都填满。
- **Network 面板是第一文档**：任何「照着教程写却登录失败」的情况，先自己在浏览器里登录一次，把真实 POST 的 URL、方法、字段名、Cookie 抄下来逐条对比。2.1 节的 `params`/`data` 教训就是这么发现的。
- **登录是否成功以响应内容为准**：状态码 200 只说明「服务器处理了这个请求」，不说明「你登录上了」。固定流程：POST 后检查 `session.cookies`，再 GET 一个受保护页看内容，两步都过才算登录成功。
- **长期任务别缓存 Cookie 硬撑**：会话 Cookie 随时会过期。与其把 Cookie 存盘指望复用，不如封装一个 `ensure_logged_in(session)`：先请求受保护页，被踢回登录页就重新走登录流程，对调用方透明。
- **频率与身份合规**：登录后的爬虫带着真实账号身份，高频抓取出问题时责任更直接。加超时、控并发、尊重站点条款；遇到验证码就收手走官方渠道（见 1.6）。

---

## 4. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-10/session_cookies_welcome.py` | Session + Cookie 登录闭环；保留原书 `params=` 写法（实测站点已需 `data=`，见 2.1） |
| `chapter-10/session_post.py` | httpbin `data=` POST 演示，验证字段进入表单请求体（已实测） |
| `chapter-10/requirements.txt` | 本章依赖：`requests>=2.31.0` |

与前后章对照着看：第 3、4 章用 `urllib` / `requests` 抓的是「无需身份」的公开页，本章给同一套工具加上身份层；第 6 章的 CSV / SQLite / MySQL 落地，可以无缝接在本章「登录后抓到的受保护数据」之后 —— 把 2.1 里 `profile.php` 的解析结果交给第 6 章的 `csv.DictWriter` 或 `sqlite3`，一条「登录 → 抓取 → 入库」的链路就齐了。

---

## 练习建议

1. 复制一份 `session_cookies_welcome.py` 为 `_practice_login.py`，把 `params=` 改成 `data={"username": "Ryan", "password": "password"}` 再运行，对比两次的 Cookie 输出与 `profile.php` 内容，亲身体会 2.1 的结论。
2. 用 `https://httpbin.org/cookies/set?demo=1` 与 `https://httpbin.org/cookies` 两个端点，分别用裸 `requests` 和 `Session` 连续请求，观察只有后者能把 Cookie 带回来。
3. 用 `https://httpbin.org/basic-auth/user/pass` 练习 `HTTPBasicAuth`（参考 1.5 的实测结果），再试试传元组 `auth=("user", "pass")` 的等价写法。
4. 写一个「GET 登录页 → BeautifulSoup 解析隐藏 `_token` → POST 登录 → GET 受保护页」的伪代码骨架（不需要真实目标站），并标注每一步 Cookie 与表单字段的变化。
5. 把 1.4 的文件上传示例改成上传一个你自己生成的 CSV（可复用第 6 章 `save_csv_json.py` 的产物），在 httpbin 响应的 `files` 字段里确认内容完整。
6. 打开浏览器 Network 面板，登录任意测试站点，把真实请求的 `Content-Type`、表单字段、响应的 `Set-Cookie` 逐条抄进笔记，再判断它属于本章哪一节的模型。
