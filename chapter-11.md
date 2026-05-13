# 第11章：抓取 JavaScript

## 核心主题

当关键内容由前端渲染或依赖浏览器 API 时，用无头浏览器执行脚本并读取 DOM 或网络响应。

---

## 11.1 何时不必上浏览器

### 核心概念

- **内嵌 JSON**：`__NEXT_DATA__`、`window.__INITIAL_STATE__` 等有时可直接请求或正则提取  
- **XHR 接口**：Network 面板中找到 JSON API，用 requests 复现（第 12 章）  

---

## 11.2 Selenium / Playwright

### 核心概念

- **显式等待**：等元素出现再读，避免 `sleep` 硬等  
- **`page.content()` / `driver.page_source`**：取渲染后 HTML 交给 BeautifulSoup  

### 依赖

见仓库 `advanced/dynamic-page-demo.py`；安装：`pip install playwright` 后 `playwright install chromium`  

### 可运行代码示例

`code/chapter11/rendered_title.py`（Playwright 可选）  

### 新手易错点

- 无头模式可能被检测；调试时先用有头模式  
- 浏览器资源占用大，注意关闭实例与并发控制  

---

## 本章小结

- 优先 **API / 内嵌数据**；浏览器自动化是**成本最高的兜底**  
- 与第 10 章结合：可用浏览器完成登录再转接 requests（在允许的前提下）  

## 本章练习题

1. 用 Playwright 打开动态站点（合法测试页），打印渲染后某选择器文本  
2. 在 DevTools 中对比「查看源代码」与「检查元素」的 HTML 差异  
3. 记录一次 XHR 请求的 URL 与参数，尝试用 requests 单独复现  
