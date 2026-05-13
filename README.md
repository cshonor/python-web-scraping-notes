# Python 网络爬虫权威指南（第2版）· 学习笔记

本仓库按原书章节拆成 **GitHub 风格 Markdown 笔记**（`chapter-01.md` … `chapter-18.md`），每章独立成篇，便于上传、复习与迭代。配套示例在 `code/chapterXX/`。

> 说明：笔记为**纲要式整理与示例代码**，与 Ryan Mitchell 原著配合阅读；请遵守站点条款与法律法规。

---

## 全书目录

| 章 | 文件 | 主题 |
|----|------|------|
| 第1章 | [chapter-01.md](chapter-01.md) | 初见网络爬虫 |
| 第2章 | [chapter-02.md](chapter-02.md) | 复杂 HTML 解析 |
| 第3章 | [chapter-03.md](chapter-03.md) | 编写网络爬虫 |
| 第4章 | [chapter-04.md](chapter-04.md) | 网络爬虫模型 |
| 第5章 | [chapter-05.md](chapter-05.md) | Scrapy |
| 第6章 | [chapter-06.md](chapter-06.md) | 存储数据 |
| 第7章 | [chapter-07.md](chapter-07.md) | 读取文档 |
| 第8章 | [chapter-08.md](chapter-08.md) | 数据清洗 |
| 第9章 | [chapter-09.md](chapter-09.md) | 自然语言处理 |
| 第10章 | [chapter-10.md](chapter-10.md) | 穿越网页表单与登录窗口进行抓取 |
| 第11章 | [chapter-11.md](chapter-11.md) | 抓取 JavaScript |
| 第12章 | [chapter-12.md](chapter-12.md) | 利用 API 抓取数据 |
| 第13章 | [chapter-13.md](chapter-13.md) | 图像识别与文字处理 |
| 第14章 | [chapter-14.md](chapter-14.md) | 避开抓取陷阱 |
| 第15章 | [chapter-15.md](chapter-15.md) | 用爬虫测试网站 |
| 第16章 | [chapter-16.md](chapter-16.md) | 并行网页抓取 |
| 第17章 | [chapter-17.md](chapter-17.md) | 远程抓取 |
| 第18章 | [chapter-18.md](chapter-18.md) | 网页抓取的法律与道德约束 |

---

## 环境与依赖

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

部分章节依赖可选包（如 Scrapy、NLTK、Selenium），见各章「依赖」小节或 `requirements.txt` 注释。

---

## 补充材料（原仓库结构）

| 路径 | 说明 |
|------|------|
| [basic/](basic/) | `requests` + BeautifulSoup 短文与 demo |
| [advanced/](advanced/) | 动态页与 Playwright 示例 |
| [reverse-engineering/](reverse-engineering/) | 接口与调试思路笔记 |

---

## 代码示例索引

```
code/
├── chapter01/   … chapter18/
```

每章笔记末尾会指向对应 `code/chapterXX/` 下的脚本文件名。
