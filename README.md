# Python 爬虫示例仓库

本仓库按难度组织：**基础 HTTP + 解析**、**动态页面（浏览器自动化）**、**逆向与调试思路**。代码仅供学习合法、合规的数据采集；请遵守目标站点的服务条款与 robots.txt，并控制请求频率。

## 目录结构

| 目录 | 说明 |
|------|------|
| `basic/` | 静态页面：`requests` 拉取 HTML，`BeautifulSoup` 解析 |
| `advanced/` | 动态页面：`Selenium` / `Playwright` 思路与示例 |
| `reverse-engineering/` | 前端接口、签名、调试等进阶笔记 |

## 环境

建议使用 Python 3.10+，并创建虚拟环境：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 快速入口

1. 从 `basic/requests-demo.py` 开始跑通一次请求与解析。
2. 阅读 `basic/beautifulsoup.md` 了解常见选择器模式。
3. 若页面内容由 JavaScript 渲染，再看 `advanced/` 与 `reverse-engineering/`。
