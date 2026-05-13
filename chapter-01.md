# 第1章：初见网络爬虫

## 核心主题

学习如何向服务器发送请求并读取返回的 HTML 内容，搭建爬虫的基础能力。

---

## 1.1 网络连接基础

### 核心概念

- **HTTP 请求**：爬虫和网站服务器之间的通信协议  
- **GET 请求**：最常用的请求方式，向服务器获取数据  
- **状态码**：服务器返回的响应状态，比如 `200` 成功、`404` 不存在、`500` 服务器错误  

### 可运行代码示例

见仓库内：`code/chapter01/get_example.py`

```python
import requests

url = "https://example.com"
response = requests.get(url)

print(f"状态码: {response.status_code}")
print("响应内容前500字符:")
print(response.text[:500])
```

### 新手易错点

- 不要用 `print(response)`，这只会打印请求对象，不会显示内容  
- 网络请求会受网络环境、防火墙、代理影响，一定要加异常处理  

---

## 1.2 BeautifulSoup 简介与安装

### 核心概念

- **BeautifulSoup**：Python 的 HTML/XML 解析库，能把杂乱的 HTML 转成可操作的对象  
- **解析器**：常用的有 `html.parser`（Python 自带）和 `lxml`（速度更快，需要额外安装）  

### 安装命令

```bash
pip install beautifulsoup4
pip install lxml  # 可选，更快的解析器
```

### 可运行代码示例

见：`code/chapter01/bs4_example.py`

```python
from bs4 import BeautifulSoup
import requests

url = "https://example.com"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

print("网页标题:", soup.title.string)

paragraphs = soup.find_all("p")
for p in paragraphs:
    print(p.get_text())
```

### 新手易错点

- `soup.title` 可能为 `None`，访问 `.string` 前先判断  
- 编码异常时检查 `response.encoding` 或响应头中的字符集  

---

## 1.3 可靠的网络连接与异常处理

### 核心概念

爬虫在运行中会遇到各种网络问题，比如连接超时、服务器拒绝、断网等，必须通过异常处理让程序稳定运行。

### 可运行代码示例

见：`code/chapter01/safe_get.py`

```python
import requests
from requests.exceptions import RequestException

def safe_get_url(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except RequestException as e:
        print(f"请求出错: {e}")
        return None

html = safe_get_url("https://example.com")
if html:
    print("获取成功")
else:
    print("获取失败")
```

---

## 本章小结

- 爬虫的第一步是**发送请求、获取响应**  
- BeautifulSoup 是解析 HTML 的基础工具  
- 网络请求必须加异常处理，才能写出稳定的爬虫  

## 本章练习题

1. 用 `requests` 访问你喜欢的一个网站，打印它的状态码和响应头信息  
2. 用 BeautifulSoup 提取该网站的所有链接  
3. 给上面的代码加上异常处理，模拟断网场景测试程序稳定性  
