# 动态页面：Selenium 与 Playwright

## 何时使用

- 首屏 HTML 里没有目标数据，需执行 JavaScript 后才出现。
- 站点依赖浏览器环境（复杂 Cookie、指纹、WebSocket 等）。
- 需要模拟点击、滚动、填表等交互。

## Selenium（简述）

- 通过 WebDriver 驱动真实浏览器（Chrome、Firefox 等）。
- 生态成熟，资料多；部署时注意驱动版本与浏览器版本匹配（或使用 `webdriver-manager` 等辅助）。

典型流程：启动浏览器 → `get(url)` → `find_element` / 显式等待 → 取 `page_source` 或元素文本。

## Playwright（简述）

- 微软维护，API 现代，内置自动等待，自带浏览器二进制。
- 适合 CI 与无头抓取；录制工具可加速脚本编写。

安装（示例）：

```bash
pip install playwright
playwright install chromium
```

## 通用建议

1. **尽量无头 + 合理视口**，但部分站点会检测无头特征，必要时用有头调试。
2. **显式等待**某元素出现后再读 DOM，避免 `time.sleep` 硬等。
3. **资源拦截**：可屏蔽图片/CSS 以提速（在允许的前提下）。
4. **合规**：自动化同样受站点条款约束；高并发对目标站不友好。

Playwright 文档：<https://playwright.dev/python/>  
Selenium 文档：<https://www.selenium.dev/documentation/>
