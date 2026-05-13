# 第 1 章 初见网络爬虫

## 本章入口

- **完整学习笔记（推荐存档阅读）**：[笔记.md](笔记.md)  
- **主示例脚本**：[`get_title.py`](get_title.py) — 在仓库根目录执行：  
  `py -3 chapter-01/get_title.py`  
  或先 `cd chapter-01` 再：`py -3 get_title.py`

## 补充脚本（与书中各段对照）

| 文件 | 说明 |
|------|------|
| `get_title_urllib.py` | 书中风格 `getTitle` + `body.h1` 与异常分支 |
| `get_example.py` | `requests` 最简 GET |
| `bs4_example.py` | `requests` + BeautifulSoup |
| `safe_get.py` | `requests` 与 `RequestException` |

安装依赖示例：`pip install beautifulsoup4 lxml`（`lxml` 可选）。
