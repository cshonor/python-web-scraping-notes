# 第12章：利用 API 抓取数据

## 核心主题

识别并调用站点或第三方提供的 HTTP API，通常比解析 HTML 更稳定。

---

## 12.1 REST 风格请求

### 核心概念

- **方法**：GET 查询、POST 创建、PUT/PATCH 更新（以 API 文档为准）  
- **认证**：`Authorization: Bearer ...`、API Key、OAuth2  
- **分页**：`page`/`cursor`/`offset` 等参数循环直至无数据  

### 可运行代码示例

`code/chapter12/json_placeholder.py` — 使用公开假数据 API `jsonplaceholder.typicode.com`  

### 新手易错点

- 未读文档就猜字段名，易踩版本变更  
- 速率限制（429）需退避重试，尊重 `Retry-After`  

---

## 12.2 与 HTML 爬虫对比

### 核心概念

- API 返回 **结构化 JSON**，省去脆弱选择器  
- 仍需处理认证、分页、错误码与合规边界  

---

## 本章小结

- 有官方或公开 API 时，**优先 API**  
- 逆向非公开接口可能违反条款，见第 18 章  

## 本章练习题

1. 拉取 `jsonplaceholder` 的 `/posts` 前 5 条，打印 `title`  
2. 实现带 `timeout` 与 `raise_for_status` 的 `get_json(url)` 包装函数  
3. 若 API 需要 Header 中的 Key，设计不把密钥写进 Git 的配置方式（环境变量）  
