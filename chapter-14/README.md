# 第 14 章 避开抓取陷阱：学习笔记

本章讨论如何在**合法、合规、礼貌**的前提下，让自动化请求更**稳健**：减少被误判为恶意机器人、降低被封禁概率。重点不是「对抗」站点安全，而是**工程化的风险控制**。

---

## 1. 核心知识点与原理

### 1.1 修改请求头（Headers）

默认 **`Python-urllib/x.x`** 等 UA 容易被策略识别。常见做法是设置接近真实浏览器的 **`User-Agent`**，并按需补充 **`Accept-Language`**、**`Referer`**（在真实用户也会出现 Referer 的场景下）。**注意**：改头不能使未授权或超范围的抓取合法化。

### 1.2 Cookie 与跟踪

Cookie 用于会话与个性化。部分跟踪脚本写入的 Cookie 需 **JS 执行**后才出现；纯 `requests` 可能拿不到这类值，此时才考虑 **Selenium / Playwright**（成本更高）。优先仍应是 **Network 面板**里能否用简单请求复现。

### 1.3 控制速度（Timing）

高并发、无间隔请求是触发封禁的常见原因。可组合：**固定/随机 `sleep`**、**全局限速器**、**降低并发**、**尊重 `Retry-After`** 与 **`robots.txt`**。

### 1.4 蜜罐（Honey Pots）

- **隐藏字段 / 隐藏链接**：通过 `type="hidden"`、`display:none`、`visibility:hidden`、零尺寸等方式让**正常用户不可见**。
- **原理**：若客户端仍提交或点击，服务端可能判定为自动化并采取措施。
- **对策（浏览器自动化）**：对可疑元素调用 **`is_displayed()`**；在 `requests` 场景则应对照 DOM/样式，**不提交**可疑字段、**不跟进**可疑链接。

---

## 2. 示例代码：用 Selenium 检查隐藏链接与隐藏输入

**PhantomJS 已停止维护**；下面使用 **Selenium 4 + Chrome**（与第 11 章一致）。示例页：`https://pythonscraping.com/pages/itsatrap.html`

可运行脚本：`chapter-14/selenium_honey_demo.py`

```python
from selenium import webdriver
from selenium.webdriver.common.by import By

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
driver = webdriver.Chrome(options=options)
driver.get("https://pythonscraping.com/pages/itsatrap.html")

for link in driver.find_elements(By.TAG_NAME, "a"):
    if not link.is_displayed():
        print("隐藏链接:", link.get_attribute("href"))

for field in driver.find_elements(By.TAG_NAME, "input"):
    if not field.is_displayed():
        print("隐藏字段:", field.get_attribute("name"))

driver.quit()
```

---

## 3. 学习贴士

- **headers_session**：`chapter-14/headers_session.py` 演示 `requests.Session` + 自定义头。  
- **被封是信号**：应减速、降并发、换数据源或取得授权，而不是堆叠对抗技巧。

---

## 4. 与本仓库其他示例

`chapter-14/headers_session.py`：最小 UA + Session 示例。

## 练习建议

1. 为 `requests` 封装默认 **UA + 超时 + 重试（退避）**。  
2. 在 HTML 中手写一个 `display:none` 的 `<a>`，用脚本验证 `is_displayed()` 行为。  
3. 阅读目标站 **`robots.txt`** 与条款，列出三条你计划遵守的规则。
