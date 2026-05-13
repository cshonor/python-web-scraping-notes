# 第 12 章 利用 API 抓取数据：学习笔记

本章说明如何**尽量绕过复杂 HTML 与全量 JS 执行**，改为从 **HTTP API** 获取结构化数据。在合规前提下，这通常比「只解析页面」更**省带宽、更稳定**。

---

## 1. 核心知识点与原理

### 1.1 API 概述

**API** 定义了软件之间如何请求与响应。Web API 常见形态：

- **URL 路由 + 查询参数**（REST 风格）；
- 返回体多为 **JSON** 或 **XML**（JSON 在爬虫侧更易与 Python `dict`/`list` 互转）。

### 1.2 HTTP 方法（常见语义）

- **GET**：读取资源，**不应**产生服务端副作用（缓存友好）。
- **POST**：提交数据（登录、创建、表单）。
- **PUT / PATCH / DELETE**：更新、部分更新、删除；公共只读 API 中相对少见，具体以文档为准。

### 1.3 解析 JSON

使用标准库 **`json.loads`**（或 `requests` 的 **`.json()`**）将文本反序列化为 Python 对象，再按键路径取值。

### 1.4 「无文档」接口与 Network 面板

许多站点用 Ajax 拉取 **JSON**，而不是把数据嵌进首屏 HTML。通过浏览器 **Network**（筛选 **Fetch/XHR**、MIME、关键词）可记录 URL、方法、Query、请求体与响应结构，再用 **`requests`** / **`urllib`** 复现最小请求。

**合规提醒**：未公开的内部接口可能受服务条款或法律保护；商业或大规模使用前请评估授权与第 18 章内容。

---

## 2. 查找与记录无文档 API

- **时机**：在刷新/翻页/筛选**之前**打开 Network，避免漏抓首屏请求。
- **过滤**：`XHR` / `Fetch`、类型 `json`、Initiator 指向的脚本名、路径含 `api`/`graphql` 等。
- **记录**：导出为 **HAR** 或复制 **cURL**，对照 Header（`Authorization`、`Cookie`、`X-Requested-With`）与分页参数。

---

## 3. 代码示例：解析 IP 地理位置（书中思路的现代替代）

书中曾用 **`ip.taobao.com`** 的接口；该服务已**长期不可用**。下面给出等价的 **`json` + `urllib`** 示例，改用公共 **`ip-api.com`**（有速率与非商业等限制，以官方说明为准；生产环境请换带 SLA 的供应商）。

可运行脚本：`chapter-12/geo_ip_api.py`

```python
import json
from urllib.request import Request, urlopen

def get_country(ip_address: str) -> str:
    url = f"http://ip-api.com/json/{ip_address}?fields=status,message,country"
    req = Request(url, headers={"User-Agent": "GeoDemo/1.0"})
    raw = urlopen(req, timeout=15).read().decode("utf-8")
    data = json.loads(raw)
    if data.get("status") != "success":
        raise RuntimeError(data.get("message", "lookup failed"))
    return data.get("country", "")

print(get_country("50.78.253.58"))
```

---

## 4. 学习贴士

- **API 优先**：能走文档化或稳定的 JSON 源，就不要先上全页浏览器自动化。
- **密钥管理**：Token 放环境变量或密钥库，**不要**写进 Git。

---

## 5. 与本仓库其他示例

`chapter-12/json_placeholder.py`：`requests` + `jsonplaceholder.typicode.com` 列表练习。

## 练习建议

1. 为 `get_country` 增加 **`try/except`** 与超时，失败时返回 `None`。  
2. 把同一 JSON 用 **`requests.get(...).json()`** 重写一版并对比代码量。  
3. 在 Network 里找一条真实 **分页 API**，用循环拉取直到空页。
