# 第 11 章 抓取 JavaScript：学习笔记

在现代 Web 中，**JavaScript** 负责大量交互与数据填充。本章说明为何 **`urllib` / `requests` 只看到「空壳 HTML」**，以及如何用**浏览器自动化**执行 JS、配合**等待策略**稳定取数。

---

## 1. 核心知识点与原理

### 1.1 动态网页的挑战

- **客户端渲染（CSR）**：首包 HTML 可能只是模板与脚本；正文由浏览器拉取 JSON 再拼进 DOM，传统「只抓 HTML 响应」会拿不到最终内容。
- **Ajax（异步 JS + XML）**：在不整页刷新的前提下与服务器交换数据并局部更新 DOM；在 Network 里常表现为 **`fetch` / `XHR`**。
- **DHTML**：广义上指用客户端脚本**改动 DOM/CSS** 的一类技术，与 Ajax 常同时出现。

### 1.2 核心工具：Selenium 与现代无头方案

直接解释执行站点 JS 不现实，工程上通常用**真实浏览器内核**驱动页面。

- **Selenium**：通过 **WebDriver** 协议驱动 Chrome / Firefox / Edge 等；需匹配浏览器版本（Selenium 4.6+ 常带 **Selenium Manager** 自动解析驱动，不必手写 `chromedriver` 路径）。
- **PhantomJS（历史）**：曾是流行的无头 WebKit；**项目已停止维护**，现代环境请改用 **Headless Chrome / Firefox** 或 **Playwright**。
- **Playwright**：微软维护，API 现代、内置浏览器二进制；仓库示例见 `code/chapter11/playwright_ajax_demo.py` 与 `advanced/dynamic-page-demo.py`。

### 1.3 等待策略（易混概念）

- **固定延迟**：`time.sleep(n)`。实现简单，但**慢且不稳**（短了未加载完，长了浪费时间）；**不是** Selenium 意义上的「隐式等待」。
- **隐式等待（Implicit）**：`driver.implicitly_wait(seconds)`，在 `find_element` 找不到时**轮询一段时间**再抛错；全局生效，需慎用以免拖慢所有查找。
- **显式等待（Explicit，推荐）**：**`WebDriverWait` + `expected_conditions`**，对**具体条件**（某元素出现、可点击、某文本出现）轮询，超时再失败。书中示例里这种写法应归类为**显式等待**。

---

## 2. 异常处理与重定向（易错点）

1. **元素未找到 / 超时**：JS 未完成时 DOM 不完整，需在关键步骤前加 **显式等待** 或合理 **隐式等待**，并捕获 **`TimeoutException`**。
2. **客户端路由**：SPA 用 **History API / `pushState`** 改 URL 时，HTTP 层可能仍是 200；自动化需 **`wait_for_url`**（Playwright）或轮询 `driver.current_url` / 等待新视图根节点。
3. **驱动与版本**：若关闭自动管理，需保证 **浏览器主版本 ≈ 驱动主版本**；CI 中建议固定浏览器版本号。

---

## 3. 可直接运行的 Python 示例代码

书中曾用 **PhantomJS**；下面给出 **Selenium 4 + 无头 Chrome** 等价写法（**Selenium 4** 使用 **`find_element(By.ID, ...)`**，不再使用已弃用的 **`find_element_by_id`**）。

**示例页**：`https://pythonscraping.com/pages/javascript/ajaxDemo.html`（点击后由 Ajax 填充内容；若站点下线，请换自建页并同步修改选择器）。

可运行脚本：

- **`code/chapter11/selenium_ajax_wait.py`**（需 `pip install selenium`，本机已安装 Chrome）
- **`code/chapter11/playwright_ajax_demo.py`**（需 Playwright，作为不依赖 WebDriver 的备选）

书中 PhantomJS 风格伪代码（**仅作历史对照，不建议再使用**）：

```python
# PhantomJS 已停止维护；请勿在新项目中依赖
# driver = webdriver.PhantomJS(executable_path=phantomjs_path)
```

Selenium 4 推荐结构（与脚本一致）：

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

def get_dynamic_content(url: str) -> None:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "loadedButton"))
        )
        content = driver.find_element(By.ID, "content").text
        print(content)
    except TimeoutException:
        print("加载超时")
    finally:
        driver.quit()
```

---

## 4. 学习贴士

- **与 BeautifulSoup 衔接**：`driver.page_source` 取渲染后 HTML，再交给 **BeautifulSoup** 做复杂解析（注意：能 CSS/XPath 直接用 Selenium/Playwright 往往更省事）。
- **调试优先有头**：排错时先关掉 headless，观察真实交互与 DevTools。
- **定位器**：`By.ID`、`By.CSS_SELECTOR`、`By.XPATH` 等；优先稳定、语义化的 **`data-testid`**（若有）。
- **先 Network 再浏览器**：很多「动态」实为 **XHR JSON**（第 12 章）；能用 `requests` 复现就不要上全浏览器，成本与维护量更低。

---

## 5. 与本仓库其他示例

- `advanced/dynamic-page-demo.py`：Playwright 打开 `example.com` 的最小示例。  
- `reverse-engineering/js-debug-notes.md`：XHR 与调试思路。

## 练习建议

1. 把显式等待条件从「元素出现」改为「**文本包含某子串**」（`text_to_be_present_in_element`）。  
2. 用 Playwright 的 **`page.route`** 拦截 XHR，打印 JSON 响应体（合法测试页）。  
3. 对比同一 URL 的 **`view-source:`** 与 **`page.content()`** 长度差异并记录原因。
