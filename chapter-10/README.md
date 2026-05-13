# 第 10 章 穿越网页表单与登录窗口：学习笔记

本章讲解如何用 **`requests`** 模拟提交表单、维持 **Cookie / Session**、上传文件，以及处理 **HTTP 基本认证**；并强调与**蜜罐字段**、**Network 面板**相关的工程习惯。

---

## 1. 核心知识点与原理

### 1.1 Requests 库

相比 `urllib`，**`requests`** 对会话、Cookie、重定向、超时与编码的处理更直观，适合表单与 API 类交互。

### 1.2 提交表单（POST）

表单多数以 **POST** 提交。关键是 **HTML 字段 `name`** 与 Python 侧 **`data={}` 字典键**一一对应（文件字段除外）。**注意**：若把表单字段放在 URL 查询串上，应使用 **`params`**；放在请求体里用 **`data`** 或 **`json`**。书中个别示例用 `post(..., params=...)` 模拟的是「类 GET 的登录接口」，真实站点多为 **`data=`**。

### 1.3 文件上传

```python
import io

import requests

url = "https://httpbin.org/post"
buf = io.BytesIO(b"hello from crawler")
buf.seek(0)
r = requests.post(
    url,
    files={"file": ("note.txt", buf, "text/plain")},
    timeout=30,
)
print(r.status_code, r.json().get("files"))
```

### 1.4 Cookie 与 Session

- **Cookie**：服务端下发的会话标识；可手动从响应头复制到 **`headers["Cookie"]`**，但易过期、难维护。
- **`requests.Session()`**：自动在后续请求中携带 Cookie，并复用连接，是登录流程的默认推荐。

### 1.5 HTTP 基本认证

对返回 **401** 且采用 **HTTP Basic** 的资源，使用：

```python
from requests.auth import HTTPBasicAuth
requests.get(url, auth=HTTPBasicAuth("user", "pass"))
```

---

## 2. 代码示例：使用 Session 保持登录状态

书中示例站点若改版或下线，请以 **Network 面板** 为准调整 URL 与字段名。

可运行脚本：`chapter-10/session_cookies_welcome.py`（含异常与 **HTTPS**；原书为 `http` + `params` 风格，脚本内附注释说明 **`data` vs `params`**）

```python
import requests

session = requests.Session()
params = {"username": "Ryan", "password": "password"}

s = session.post(
    "https://pythonscraping.com/pages/cookies/welcome.php",
    params=params,
    timeout=20,
)
print("Cookie:", session.cookies.get_dict())

s = session.get("https://pythonscraping.com/pages/cookies/profile.php", timeout=20)
print(s.text[:500])
```

---

## 3. 学习贴士

- **蜜罐字段**：提交前检查是否存在 **`display:none`** 或视觉上隐藏的输入框；不要随意填充，否则易被反爬策略标记。
- **分析网络流量**：复杂登录（多步跳转、CSRF、`_token`）务必用浏览器 **Network** 对照**真实 POST** 的 URL、方法与表单字段；必要时先 **GET 登录页**解析隐藏域再 POST。

---

## 4. 与本仓库其他示例

`chapter-10/session_post.py`：对 **httpbin.org** 的 **`data=`** POST 演示。

## 练习建议

1. 将书中登录改为 **`data={"username":..., "password":...}`**（若接口支持），对比与 `params` 的差异。  
2. 用 **`httpbin.org/basic-auth/user/pass`** 练习 **`HTTPBasicAuth`**。  
3. 用 Session 完成：**GET 登录页 → 解析 CSRF → POST 登录 → GET 受保护页** 的伪代码（无需真攻真实账户）。
