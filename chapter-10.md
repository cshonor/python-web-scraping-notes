# 第10章：穿越网页表单与登录窗口进行抓取

## 核心主题

用 `requests.Session` 维护 Cookie，处理 POST、隐藏字段与登录态，必要时结合浏览器自动化。

---

## 10.1 Session 与 Cookie

### 核心概念

- **`requests.Session()`**：跨请求复用连接、自动携带服务端下发的 Cookie  
- **登录后 Cookie**：后续 GET 需在**同一 Session** 上发起  

### 可运行代码示例

`code/chapter10/session_post.py`（对 `httpbin.org` 等公开测试端点演示 POST）  

### 新手易错点

- 忘记在登录响应后检查是否返回错误页（状态码仍可能是 200）  
- CSRF token 常在表单隐藏域，需先 GET 登录页再解析 token  

---

## 10.2 浏览器登录（衔接第 11 章）

### 核心概念

- **OAuth / 验证码 / 复杂 JS 指纹**：纯 requests 难以复现时，用 Selenium/Playwright 完成登录后导出 Cookie 到 Session（注意合规）  

---

## 本章小结

- 表单抓取 = **解析字段名 + 维持会话 + 校验成功标志**  
- 隐藏字段与 token 是「防 CSRF」机制，爬虫应**模拟真实浏览器行为**，而非绕过安全研究未授权系统  

## 本章练习题

1. 用 Session 对 `https://httpbin.org/cookies/set?k=v` 再访问 `/cookies` 验证 Cookie  
2. 找一页公开测试表单（或自建 Flask 表单），用 POST 提交并打印响应片段  
3. 画流程图：从打开登录页到带 Cookie 访问受保护页的请求顺序  
