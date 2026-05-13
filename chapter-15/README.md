# 第 15 章 用爬虫测试网站：学习笔记

本章介绍如何把「请求 + 解析」能力用于**前端回归与交互测试**：在可控环境里重复执行场景、断言 DOM 与截图留证。

---

## 1. 核心知识点与原理

### 1.1 单元测试（`unittest`）

**单元测试**验证小单元行为是否符合预期。Python 标准库 **`unittest`** 提供用例组织、断言与运行器。

### 1.2 常用钩子

- **`setUp` / `tearDown`**：每个用例前后执行，适合做浏览器启动/关闭（若每测一例都需隔离环境）。
- **`setUpClass` / `tearDownClass`**：整个测试类一次，适合**昂贵资源**（启动一次浏览器，多用例复用）。

### 1.3 Selenium 交互测试

相比只解析静态 HTML，Selenium/Playwright 能模拟**点击、输入、拖放**等交互，更贴近真实用户路径；也支持 **`get_screenshot_as_file`** 保存快照，便于人工复核或基线对比。

### 1.4 与「生产爬虫」区分

测试应对准**授权环境**（自家 staging、公开测试站如 `example.com`），避免对无关站点高频探测（参见第 14 章）。

---

## 2. 示例代码：`unittest` + Selenium 拖放

书中曾用 **PhantomJS**；此处改为 **Chrome** + **Selenium 4** API（`By.ID` 等）。

示例页：`https://pythonscraping.com/pages/javascript/draggableDemo.html`（若页面改版，断言文案需同步调整）。

可运行脚本：`chapter-15/selenium_drag_unittest.py`

```python
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains

class TestDragAndDrop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        cls.driver = webdriver.Chrome(options=options)
        cls.driver.get("https://pythonscraping.com/pages/javascript/draggableDemo.html")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_drag(self):
        element = self.driver.find_element(By.ID, "draggable")
        target = self.driver.find_element(By.ID, "div2")
        ActionChains(self.driver).drag_and_drop(element, target).perform()
        msg = self.driver.find_element(By.ID, "message").text
        self.assertIn("bot", msg.lower())

if __name__ == "__main__":
    unittest.main()
```

---

## 3. 学习贴士

- **链接巡检**：`chapter-15/link_checker.py` 演示同域链接探测与限速。  
- **CI**：将 `python -m unittest` 或 `pytest` 接入流水线，失败时附带截图路径。

---

## 4. 练习建议

1. 把拖放断言改为**截图文件存在**且大小大于某阈值。  
2. 用 **`unittest.mock`** 模拟 `requests.get`，对解析函数做单测（无需浏览器）。  
3. 为登录流程写一个 **`setUpClass` 登录一次、多个用例复用 Session** 的草图（注意 Cookie 过期）。
