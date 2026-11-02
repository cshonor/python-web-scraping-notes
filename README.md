# Python 网络爬虫权威指南（第 2 版）· 学习笔记仓库

配合 Ryan Mitchell《Web Scraping with Python》(2nd Edition) 逐章整理的笔记与可运行示例。

按 **18 个章节目录**组织：`chapter-01` … `chapter-18`，每章一个文件夹。

> 笔记为纲要式整理，需与原书配合阅读；所有示例仅用于学习，请遵守目标站点条款、`robots.txt` 与当地法律法规（第 18 章专讲这条线）。

---

## 体例说明

18 章目录结构完全一致：

```text
chapter-NN/
├── README.md          ← 本章笔记（GitHub 默认展示，唯一入口）
├── requirements.txt   ← 本章依赖（照这个装就能跑）
└── *.py               ← 配套示例脚本
```

每章 README 的骨架也一致：

1. `# 第 N 章 …：学习笔记` 标题
2. 开头一段导语，说明**本章要解决什么问题**
3. `---` 分隔线
4. **编号小节**：第 `1.` 节必讲本章核心机制，之后是示例代码 / 易错点等按章定制的小节
5. `## 学习贴士`
6. `## 与本仓库其他示例`
7. `## 练习建议`

节名按主题微调，层级与顺序不变。已知的三类差异（都是内容差异，不是体例差异）：

| 章节 | 差异 |
|---|---|
| 第 7–10、14、16、17 章 | 不单列「易错点」节，相关提示并入示例节与「学习贴士」 |
| 第 13 章 | 6 个编号节（工具库 → 预处理 → 验证码 → 示例 → 贴士 → 其他示例） |
| 第 18 章 | 纯法律/伦理章，无代码，因而「与本仓库其他示例」指向空 |

> 早期版本中第 1–5 章曾用「`README.md` 薄索引 + `笔记.md` 全文」的双文件结构，现已并入单一 README，与其余章节对齐。

---

## 全书目录

| 章 | 目录 | 主题 | 主要依赖 |
|----|------|------|----------|
| 第 1 章 | [chapter-01/](chapter-01/) | 初见网络爬虫 | `requests` `bs4` |
| 第 2 章 | [chapter-02/](chapter-02/) | 复杂 HTML 解析 | `bs4` |
| 第 3 章 | [chapter-03/](chapter-03/) | 编写网络爬虫 | `bs4` |
| 第 4 章 | [chapter-04/](chapter-04/) | 网络爬虫模型 | `requests` `bs4` |
| 第 5 章 | [chapter-05/](chapter-05/) | Scrapy（含 `wikiSpider/` 子项目） | `scrapy` |
| 第 6 章 | [chapter-06/](chapter-06/) | 存储数据 | `bs4` `PyMySQL` |
| 第 7 章 | [chapter-07/](chapter-07/) | 读取文档 | `bs4` `pypdf` `pdfminer.six` |
| 第 8 章 | [chapter-08/](chapter-08/) | 数据清洗 | `pandas` |
| 第 9 章 | [chapter-09/](chapter-09/) | 自然语言处理 | `nltk` |
| 第 10 章 | [chapter-10/](chapter-10/) | 表单与登录 | `requests` |
| 第 11 章 | [chapter-11/](chapter-11/) | 抓取 JavaScript | `selenium` `playwright` |
| 第 12 章 | [chapter-12/](chapter-12/) | 利用 API | `requests` |
| 第 13 章 | [chapter-13/](chapter-13/) | 图像与 OCR | `Pillow` `pytesseract` |
| 第 14 章 | [chapter-14/](chapter-14/) | 避开抓取陷阱 | `requests` `selenium` |
| 第 15 章 | [chapter-15/](chapter-15/) | 用爬虫测试网站 | `requests` `bs4` `selenium` |
| 第 16 章 | [chapter-16/](chapter-16/) | 并行抓取 | `requests` |
| 第 17 章 | [chapter-17/](chapter-17/) | 远程抓取 | `requests` `PySocks` `selenium` |
| 第 18 章 | [chapter-18/](chapter-18/) | 法律与道德约束 | 无代码 |

---

## 环境与依赖

Python **3.10+**，建议先建虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

装依赖有两种方式，**推荐第一种**：

### 方式一：按章安装（推荐）

只在读某一章时装那一章的依赖，互不干扰：

```bash
cd chapter-06
pip install -r requirements.txt
python3 wikitable_to_csv.py
```

### 方式二：全量安装

想一次性跑遍全书：

```bash
pip install -r requirements.txt   # 根目录，含全部 14 个第三方包
```

### 三步系统级准备（pip 装不出来）

| 需要 | 场景 | 命令 |
|---|---|---|
| Chromium（Playwright 自带浏览器） | 第 11 章 Playwright 示例 | `python3 -m playwright install chromium` |
| Tesseract OCR 引擎 | 第 13 章 | macOS `brew install tesseract`；Debian/Ubuntu `sudo apt install tesseract-ocr` |
| Tor 服务 | 第 17 章 | 需监听 `127.0.0.1:9050`，否则脚本连接被拒（属预期） |

另外：Selenium 示例（11/14/15/17 章）需本机已装 Chrome（Selenium 4.6+ 自带 Selenium Manager 自动配驱动）；第 6 章 MySQL 示例需一个可连的 MySQL 实例（同章 `sqlite_store.py` 是不依赖服务的替身）；第 9 章首次运行需 `nltk.download()` 下载语料。

---

## 运行 Scrapy 维基示例（第 5 章）

```bash
cd chapter-05/wikiSpider        # 必须进入含 scrapy.cfg 的这一层
scrapy crawl articles -o sample.json
```

运行前请把 `wikiSpider/wikiSpider/settings.py` 中的 `USER_AGENT` / `mailto` 改成你自己的标识与联系方式。

---

## 抓取礼仪

书里的示例站点是教学用的，但习惯要一开始就立对：

- 带上**可识别的 `User-Agent`**，必要时附联系方式（维基、GitHub 等站点对此有硬性要求）
- 加**延迟与页数上限**，别把示例代码直接对着生产站跑
- 遵守 `robots.txt` 与站点条款；涉及个人信息、付费内容、绕过访问控制的场景，先看第 18 章

---

## LICENSE

[MIT](LICENSE) —— 代码可自由取用；笔记内容基于原书整理，版权归原作者所有。
