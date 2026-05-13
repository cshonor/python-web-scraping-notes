# 第5章：Scrapy

## 核心主题

使用 Scrapy 框架构建可配置、可扩展的中大型爬虫项目。

---

## 5.1 为什么用 Scrapy

### 核心概念

- **异步调度**：内置 Twisted，适合高吞吐抓取（在合规与站点承受范围内）  
- **管道（Pipeline）**：清洗、校验、写入数据库的流水线  
- **中间件**：统一处理代理、User-Agent、重试等  

### 依赖

```bash
pip install scrapy
```

创建项目：`scrapy startproject myproject`

### 新手易错点

- Scrapy 学习曲线陡，**小脚本不必强行上框架**  
- `settings.py` 里 `ROBOTSTXT_OBEY`、`DOWNLOAD_DELAY` 务必先配置  

---

## 5.2 Spider、Item、Pipeline 概览

### 核心概念

- **Spider**：生成 `Request`，解析 `Response`，`yield` Item 或跟进链接  
- **Item**：字段容器，可与 `ItemLoader` 做输入处理  
- **Pipeline**：`process_item`，适合做去重与持久化  

### 可运行代码示例

`code/chapter05/` 下提供最小 `quotes` 风格示例说明（需本地 `scrapy startproject` 后对照笔记目录结构粘贴）。  

---

## 本章小结

- Scrapy 适合**多站点多规则、长期运行、团队维护**  
- 框架能力是「工程化」，不是「绕过反爬」  

## 本章练习题

1. 官方教程：完成 `quotes.toscrape.com` 全站引用抓取  
2. 写一个 Pipeline 把 Item 追加写入 JSON Lines 文件  
3. 启用并观察 `ROBOTSTXT_OBEY` 对禁止路径的行为  
