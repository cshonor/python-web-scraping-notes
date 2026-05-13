# Python 网络爬虫权威指南（第2版）· 学习笔记仓库

本仓库按 **18 个章节目录**组织：每章一个文件夹 **`chapter-01`** … **`chapter-18`**，内含：

- **`README.md`**：该章学习笔记（GitHub 默认展示）  
- **`.py` 等代码**：与该章配套的示例脚本（在同一文件夹内运行或按章内说明执行）

> 说明：笔记为纲要式整理与示例代码，与 Ryan Mitchell 原著配合阅读；请遵守站点条款与法律法规。

---

## 全书目录

| 章 | 目录 | 主题 |
|----|------|------|
| 第1章 | [chapter-01/](chapter-01/) | 初见网络爬虫 |
| 第2章 | [chapter-02/](chapter-02/) | 复杂 HTML 解析 |
| 第3章 | [chapter-03/](chapter-03/) | 编写网络爬虫 |
| 第4章 | [chapter-04/](chapter-04/) | 网络爬虫模型 |
| 第5章 | [chapter-05/](chapter-05/) | Scrapy（含 `wikiSpider/` 子项目） |
| 第6章 | [chapter-06/](chapter-06/) | 存储数据 |
| 第7章 | [chapter-07/](chapter-07/) | 读取文档 |
| 第8章 | [chapter-08/](chapter-08/) | 数据清洗 |
| 第9章 | [chapter-09/](chapter-09/) | 自然语言处理 |
| 第10章 | [chapter-10/](chapter-10/) | 表单与登录 |
| 第11章 | [chapter-11/](chapter-11/) | 抓取 JavaScript |
| 第12章 | [chapter-12/](chapter-12/) | 利用 API |
| 第13章 | [chapter-13/](chapter-13/) | 图像与 OCR |
| 第14章 | [chapter-14/](chapter-14/) | 避开抓取陷阱 |
| 第15章 | [chapter-15/](chapter-15/) | 用爬虫测试网站 |
| 第16章 | [chapter-16/](chapter-16/) | 并行抓取 |
| 第17章 | [chapter-17/](chapter-17/) | 远程抓取 |
| 第18章 | [chapter-18/](chapter-18/) | 法律与道德约束 |

---

## 环境

建议使用 Python 3.10+：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

各章依赖不同（如 Scrapy、Selenium、NLTK），以各章 `README.md` 与 `requirements.txt` 注释为准。

---

## 运行 Scrapy 维基示例（第 5 章）

在仓库根目录：

```bash
cd chapter-05/wikiSpider
scrapy crawl articles
```
