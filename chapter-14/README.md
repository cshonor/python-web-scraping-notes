# 第 14 章 避开抓取陷阱：学习笔记

前面各章解决的是「怎么把数据抓下来」，本章解决的是「怎么在抓取过程中不被误判、不被封禁」。核心机制一句话：站点通过 UA、IP、行为节奏、隐藏元素等多个维度识别机器人，工程上的应对不是「对抗」，而是在**合法、合规、礼貌**的前提下让自动化请求更**稳健**——减少被误判为恶意机器人、降低被封禁概率。需要强调的是，本章只讲技术层面的风险控制；至于「能不能抓、抓来能不能用、违反了什么条款」的边界问题，属于第 18 章法律与道德讨论的范围，两章必须结合起来看，缺一不可。

**本章目标**

1. 理解站点识别爬虫的主要维度：**UA、IP、行为节奏、蜜罐元素**，知道每个维度的工程对策
2. 会用 **`requests.Session`** 统一携带自定义请求头并自动管理 Cookie（`headers_session.py`）
3. 理解**服务端种下的 Cookie** 与 **JS 执行后生成的跟踪值**的差异，知道何时才需要上浏览器自动化
4. 会用 **Selenium 的 `is_displayed()`** 检查隐藏链接与隐藏输入，识别蜜罐（`selenium_honey_demo.py`）
5. 掌握限速、随机间隔、尊重 `Retry-After` 与 `robots.txt` 的礼貌抓取组合
6. 建立「被封是信号」的工程心态：减速、降并发、换数据源或取得授权，而非堆叠对抗技巧

---

## 1. 核心知识点与原理

### 1.1 站点如何识别爬虫：四个常见维度

反爬的本质是「找异常」。真实用户和脚本在多个维度上表现不同，站点的 WAF 或风控系统把这些信号组合起来打分，超过阈值就拦截、弹验证码或返回假数据：

| 维度 | 脚本的典型破绽 | 工程对策 |
|---|---|---|
| **User-Agent** | 默认 `Python-urllib/x.x`、`python-requests/x.x` 一眼即知 | 设置接近真实浏览器的 UA，或如实声明 bot 身份与联系方式 |
| **IP 与频率** | 单 IP 短时间大量请求、7×24 不间断、数据中心 IP 段 | 限速、随机间隔、尊重 `Retry-After`；必要时换数据源或取得授权 |
| **行为节奏** | 间隔恒定如时钟、只访问数据接口不加载静态资源、不看页面直接 POST 表单 | 随机 `sleep`、按正常浏览路径访问、先 GET 页面再提交 |
| **蜜罐元素** | 点击了正常用户看不见的链接、提交了隐藏字段 | 用 `is_displayed()` 或对照 CSS 过滤可疑元素 |

两点要记牢：其一，没有哪一个维度是「改了就一定安全」的，站点看的是信号组合；其二，也没有必要把每个维度都伪装到极致——目标是让自己的访问模式落在站点可接受的正常范围内，而不是和站方的安全团队较劲。对抗升级对双方都是成本。

还有一个容易被忽视的维度是 **TLS / HTTP 指纹**：`requests` 的 TLS 握手特征与真实浏览器不同，严格的风控系统会据此识别。但对学习阶段和大多数合规场景而言，不值得为此折腾——遇到这个量级的反爬，正确的反应通常是「这个站不欢迎抓取」，转而寻找官方 API 或授权渠道。

### 1.2 修改请求头与 Session 复用

`requests` 发出的默认 UA 形如 `python-requests/2.x.x`，很多站点会直接给它打上低分甚至拒绝响应。常见做法是设置接近真实浏览器的 **`User-Agent`**，并按需补充 **`Accept-Language`**、**`Referer`**。常用请求头的作用一览：

| 请求头 | 作用 | 设置建议 |
|---|---|---|
| **`User-Agent`** | 声明客户端身份 | 真实浏览器 UA，或诚实的 bot 声明（含联系方式） |
| **`Accept-Language`** | 声明语言偏好 | 与目标站点语言一致，如 `en-US,en;q=0.9` / `zh-CN,zh;q=0.9` |
| **`Referer`** | 声明来源页面 | 仅在真实用户也会产生它的场景下加，乱填更可疑 |
| **`Accept`** | 声明可接受的响应类型 | 一般保持默认即可，API 场景按需指定 `application/json` |

后两个字段要谨慎：`Referer` 在从列表页点进详情页这类场景下真实存在，此时补上更自然；`Accept-Language` 与目标站点的语言保持一致即可，抓中文站却带着 `en-US` 也是一个弱信号。

`requests.Session` 是多请求场景的便利工具：

```python
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; EduBot/1.0)"})
r = s.get("https://example.com", timeout=15)
```

Session 带来两个实际收益：一是**头只需设置一次**，会话内后续每个请求自动携带，避免逐个请求手写导致漏写；二是**自动管理 Cookie**（详见 1.3）。易错点有两个：其一，`s.headers.update()` 本质是字典更新，同名键的值会被整体覆盖，想做 UA 轮换时应自行维护 UA 列表、每次请求显式传入，而不是反复 `update`；其二，**改头不能使未授权或超范围的抓取合法化**——UA 只是「自我介绍」，不是通行证。需要登录才能看的内容、条款明确禁止抓取的内容，换个 UA 照样不该抓。

### 1.3 Cookie 与跟踪：requests 够不够用

Cookie 承担会话保持与个性化。用 `requests` 时，服务端通过 `Set-Cookie` 响应头种下的 Cookie 会被 `Session` 自动保存（在 `s.cookies` 里可见）并在后续请求中自动回带，登录态维持这类场景完全不需要浏览器。真正的问题是另一类 Cookie：**由页面内 JS 跟踪脚本执行后才写入的值**。纯 `requests` 不执行 JS，永远拿不到它们。此时有三个层次的选择，成本递增：

| 方案 | 成本 | 适用场景 |
|---|---|---|
| **DevTools Network 面板复现** | 低 | 先在浏览器里观察真实请求；若该 Cookie 其实不影响目标接口的返回，直接忽略它 |
| **从 JS 源码推导取值逻辑** | 中 | Cookie 值由页面内脚本用公开算法生成（如时间戳哈希），可在 Python 里复算 |
| **Selenium / Playwright 渲染** | 高 | 必须执行完整 JS、加载渲染后的页面才能拿到所需状态时 |

原则是**能不上浏览器就不上**。浏览器自动化启动慢、内存占用高，还引入驱动与浏览器版本匹配等新的故障面。只有当 Network 面板确认「缺了这个 JS 生成的值，接口就拒绝返回数据」时，才考虑 Selenium——而且拿到 Cookie 后仍可以塞回 `requests.Session` 里继续用轻量方式抓取，不必全程挂着浏览器。

一个典型工作流是混合式的：用 Selenium 完成登录或首屏渲染，从 `driver.get_cookies()` 读出会话 Cookie，逐项 `s.cookies.set(...)` 移植到 `requests.Session`，之后的高频抓取全部走 `requests`。这样既过了 JS 这道坎，又把后续成本压回轻量级。

### 1.4 控制速度与人性化

高并发、无间隔请求是触发封禁最常见的原因，而且它对站方是真实成本（带宽、连接数、数据库压力）——这就是为什么「礼貌」和「不被封」在这里是同一件事。常用手段可组合使用：

| 手段 | 说明 |
|---|---|
| **固定 / 随机 `sleep`** | 请求间加 2 秒左右的基础间隔再加随机抖动，避免机械式恒定节奏 |
| **全局限速器** | 令牌桶或时间戳检查，保证 QPS 上限不被突破，多线程共享同一个限速器 |
| **降低并发** | 线程池调小，或 Scrapy 的 `CONCURRENT_REQUESTS_PER_DOMAIN` / `DOWNLOAD_DELAY` 调保守 |
| **尊重 `Retry-After`** | 收到 429 / 503 时按响应头指定的秒数等待，而不是立刻重试火上浇油 |
| **尊重 `robots.txt`** | 不抓被明确禁止的路径；Scrapy 默认 `ROBOTSTXT_OBEY=True`，应保留为常态 |

两个易错点：其一，随机间隔不要写成 `sleep(random.random())` 这种 0–1 秒的均匀分布——间隔过短且均值固定，流量聚合后特征依然明显；实践常用「基础间隔 + 抖动」，例如 `sleep(2 + random.uniform(0, 2))`。其二，限速要按**域名**而不是按全局——同时抓多个站时，对每个站独立限速才合理，全局限速既可能压不住对单站的冲击，也会无谓拖慢整体。

还要理解限速的「双重身份」：对自己，它是稳定性保障（避免触发封禁导致任务中断重跑）；对站方，它是基本礼貌（你的抓取不该成为别人服务器的压力来源）。Scrapy 的 `AUTOTHROTTLE` 把这个思路做到了极致——根据响应延迟自动升降速，站点慢了就等一等，这既是礼貌也是自适应的稳定性策略。

### 1.5 蜜罐（Honey Pots）：隐藏链接与隐藏字段

蜜罐是站点故意埋下的「只有机器人会上当」的元素。正常用户看不见它们，自然不会点击或提交；脚本若不加分辨地遍历 DOM、见链接就跟、见字段就填，就会暴露。有些蜜罐甚至不只用来「识别」，还用来「喂养」：识别出机器人后，站点给它返回一份格式正常但内容编造的数据，让抓取方在毫无察觉的情况下积累一堆垃圾。

常见隐藏手段：

| 手段 | 典型写法 | 用户视角 |
|---|---|---|
| **隐藏输入类型** | `<input type="hidden">` | 表单里不可见 |
| **CSS 不显示** | `display:none` | 不占布局，完全不可见 |
| **CSS 透明化** | `visibility:hidden` | 占位但不可见 |
| **零尺寸** | `width:0; height:0; overflow:hidden` | 缩成一个点 |
| **移出视口** | `position:absolute; left:-9999px` | 渲染在屏幕外 |
| **同色文字** | 文字颜色与背景相同 | 看得见元素但读不出内容 |

**原理**：若客户端仍提交隐藏字段或跟进隐藏链接，服务端即可判定为自动化，轻则返回编造的假数据污染你的结果，重则封 IP、封账号。**数据污染比封禁更隐蔽**：抓取结果出现异常规律（某字段永远相同、链接指向不存在的页面、数据整齐得不像真实内容）时，要回头检查是否踩了蜜罐。

**对策**分两种场景：

- **浏览器自动化**：对可疑元素调用 **`is_displayed()`**，它由渲染引擎综合计算元素的实际可见性（覆盖上表大部分手段），返回 `False` 的一律不点、不提交。这是 Selenium 在这类检查上不可替代的原因——自己手写规则逐条判断 CSS 属性，永远追不齐所有隐藏手法。
- **纯 `requests`**：没有渲染引擎，`is_displayed()` 不可用，应人工对照 DOM 与样式表过滤，**不提交**可疑字段、**不跟进**可疑链接。注意区分蜜罐字段与正常业务字段：`type="hidden"` 里既有陷阱也有 CSRF token 这类必需字段，区分依据是「真实用户提交表单时带没带它」——在浏览器 Network 面板里看一次真实提交即可确认。

### 1.6 技术合规的边界：本章与第 18 章的关系

本章所有技巧都有一个隐含前提：**目标内容是允许抓取的**。改 UA、限速、避开蜜罐，这些都只解决「如何礼貌地访问」，不解决「是否被允许访问」。两者经常被混淆，值得单独强调：

| 问题 | 属于 | 答案来源 |
|---|---|---|
| 请求头怎么设置、间隔多大合适 | 工程问题（本章） | 性能与稳定性测试 |
| 登录后的内容能不能抓 | 授权问题（第 18 章） | 服务条款、授权协议 |
| 抓来的数据能不能商用、再发布 | 法律问题（第 18 章） | 著作权、隐私法规、条款 |
| 绕过验证码、破解加密接口 | 越界行为 | 本章不提供此类技巧 |

一句话总结本章的立场：**稳健不等于隐身，礼貌不等于伪装**。把所有精力花在「让正常访问更稳定」上，而不是「让违规访问更难被发现」上。

---

## 2. 示例代码：用 Selenium 检查隐藏链接与隐藏输入

**PhantomJS 已停止维护**，不要在新代码里使用；本章使用 **Selenium 4 + Chrome**（与第 11 章一致）。两个脚本按「轻量 headers → 重量级浏览器」的顺序排列，分别对应 1.2 与 1.5 两节的机制。依赖安装：`cd chapter-14 && pip install -r requirements.txt`（`requests>=2.31.0`、`selenium>=4.15.0`）。

### 2.1 `headers_session.py`：Session 统一携带自定义头

演示 1.2 节的最小实践，全脚本 15 行。先定义 `HEADERS` 字典：`User-Agent` 声明为 `Mozilla/5.0 (compatible; EduBot/1.0; +https://example.com)`（bot 名 + 版本 + 联系 URL 的诚实格式），另带 `Accept-Language: en-US,en;q=0.9`。然后创建 `requests.Session()`，用 `s.headers.update(HEADERS)` 让会话内所有请求自动携带这套头；接着 `s.get("https://example.com", timeout=15)`——`timeout` 显式给出，避免网络异常时无限挂起；`raise_for_status()` 把 4xx/5xx 变成异常而不是静默拿到错误页；最后打印状态码与响应头里的 `Content-Type`。重点不在功能而在语义：**头设一次、处处生效**，这就是 Session 对多请求抓取的价值。

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; EduBot/1.0; +https://example.com)",
    "Accept-Language": "en-US,en;q=0.9",
}

s = requests.Session()
s.headers.update(HEADERS)
r = s.get("https://example.com", timeout=15)
r.raise_for_status()
print(r.status_code, r.headers.get("Content-Type"))
```

```bash
cd chapter-14
pip install -r requirements.txt
python headers_session.py
```

**已实测**：输出 `200 text/html; charset=utf-8`，请求正常完成。注意 UA 里的联系 URL 是占位符 `example.com`，实际使用时换成自己的项目页或联系方式，诚实声明比伪装更可持续。

实测时还可以顺带验证一件事：把脚本里的 UA 删掉再请求某些站点，对比响应差异——有的站会返回 403，有的会返回一份精简版页面。这是理解「UA 是第一道门槛」最直观的方式。另外注意 `raise_for_status()` 只负责把错误状态码变成异常，脚本没有捕获它；真实项目里应在调用处 `try/except requests.HTTPError` 并配合退避重试（见练习 3）。

### 2.2 `selenium_honey_demo.py`：检查 itsatrap 示例页的隐藏元素

对应 1.5 节的蜜罐检测。目标页 `https://pythonscraping.com/pages/itsatrap.html` 是专为教学准备的陷阱页，故意包含隐藏链接与隐藏输入。脚本结构分三层：

1. **启动层**：`ChromeOptions` 加三个参数——`--headless=new`（新版无头模式，不需要显示服务器）、`--disable-gpu`（避免无显示环境下的 GPU 初始化问题）、`--no-sandbox`（为部分 Linux 容器准备的兼容参数）；`webdriver.Chrome(options=options)` 包在 `try/except WebDriverException` 里——启动失败（没装 Chrome、驱动不匹配）时向 stderr 打印「无法启动 Chrome / 请安装 selenium 与本机 Chrome」并以退出码 1 结束，而不是甩出一屏 traceback。Selenium 4.6+ 自带 Selenium Manager 自动管理驱动，不再需要手动下载 chromedriver。
2. **检查层**：`driver.get(URL)` 后，先遍历所有 `<a>` 标签，对 `is_displayed()` 为 `False` 的打印「警告：隐藏链接」及其 `href`；再遍历所有 `<input>`，同样过滤后打印「警告：隐藏字段」及其 `name`。
3. **清理层**：浏览器进程很重，`driver.quit()` 放在 `finally` 里，保证检查中途抛异常也能释放资源。

```python
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
try:
    driver = webdriver.Chrome(options=options)
except WebDriverException as e:
    print("无法启动 Chrome:", e, file=sys.stderr)
    return 1

try:
    driver.get(URL)
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if not link.is_displayed():
            print("警告：隐藏链接", link.get_attribute("href"))
    for field in driver.find_elements(By.TAG_NAME, "input"):
        if not field.is_displayed():
            print("警告：隐藏字段", field.get_attribute("name"))
finally:
    driver.quit()
```

```bash
cd chapter-14
pip install -r requirements.txt   # 需要 selenium>=4.15.0
python selenium_honey_demo.py     # 需本机已安装 Chrome
echo "退出码: $?"                 # 正常检查完成为 0；Chrome 启动失败为 1
```

脚本的退出码语义值得留意：正常跑完检查（无论有没有发现隐藏元素）返回 0；只有 Chrome 启动失败才返回 1。也就是说「没有发现蜜罐」和「发现蜜罐」都会以 0 退出，差异体现在 stdout 的警告行上——在 CI 或定时任务里用这个脚本做巡检时，应该 grep 输出里的「警告」关键字而不是只看退出码。

**未实测**：本机未安装 Chrome 且当前 Python 环境未装 selenium，无法实际运行。按代码逻辑，脚本会在页面渲染完成后逐元素调用 `is_displayed()`，把蜜罐元素及其 `href` / `name` 打印出来，形如：

```text
警告：隐藏链接 http://pythonscraping.com/...（示例，取决于页面实际内容）
警告：隐藏字段 phone（示例，取决于页面实际字段名）
```

再次强调这个 API 的价值：它由浏览器渲染引擎综合计算「用户能否看见」，比手写规则判断 `display:none`、零尺寸等属性可靠得多——这正是蜜罐检查必须用浏览器自动化、而不能用纯 `requests` 的原因。另外 `--no-sandbox` 是为部分 Linux 容器环境准备的兼容参数，在有严格安全要求的环境里应评估后去掉。

---

## 3. 学习贴士

- **先复现，再伪装**。遇到反爬先开 DevTools Network 面板，看真实浏览器发什么头、走什么顺序、收什么 Cookie；多数时候差的只是一个 UA 或一次「先 GET 页面再提交表单」的正常顺序，不需要堆叠技巧。
- **被封是信号，不是挑战**。出现 403 / 429 / 验证码，正确反应是减速、降并发、换数据源或联系站方取得授权，而不是升级对抗手段——对抗升级对双方都是成本，而且通常站方的工具比你多。
- **能 `requests` 就不 Selenium**。浏览器自动化的成本是数量级的：启动秒级、内存数百 MB、还有驱动与浏览器版本匹配问题。本章两个脚本的梯度正是这个原则的体现；即使必须用 Selenium 拿 Cookie，也可以拿到后塞回 `requests.Session` 继续轻量抓取。
- **`is_displayed()` 不是万能的**。它判断「是否可见」，不判断「是不是蜜罐」；个别站点会用正常可见的链接做蜜罐（真实用户没兴趣点的那种 URL）。结合链接语义判断更稳妥。
- **把 UA 写成诚实的自我介绍**。`EduBot/1.0; +联系URL` 这种格式符合维基媒体等机构的公开 UA 政策，比伪装成 Chrome 更可持续——愿意放行善意爬虫的站点比想象中多，被识破的伪装反而会上黑名单。

---

## 4. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-14/headers_session.py` | `requests.Session` + 自定义 UA / `Accept-Language` 最小示例（已实测，返回 `200 text/html; charset=utf-8`） |
| `chapter-14/selenium_honey_demo.py` | Selenium 4 + headless Chrome 检查隐藏链接与隐藏输入（需本机 Chrome，未实测） |
| `chapter-14/requirements.txt` | 本章依赖：`requests>=2.31.0`、`selenium>=4.15.0` |

对照第 11 章看：那里把 Selenium 当作「抓取 JS 渲染页面」的工具，本章把它当作「检测蜜罐可见性」的工具——同一个 `is_displayed()` API，用途完全不同。对照第 5 章看：Scrapy 的 `DOWNLOAD_DELAY`、`AUTOTHROTTLE`、`ROBOTSTXT_OBEY` 就是本章 1.4 节原则的框架化实现。对照第 18 章看：本章所有技巧都以「合法合规礼貌」为前提，法律与道德边界问题以那一章为准。

---

## 练习建议

1. 给 `headers_session.py` 扩展为「UA 轮换」版本：维护 3–5 个真实浏览器 UA 的列表，每次请求随机选取，并用 `httpbin.org/headers` 之类的回显服务验证实际发出去的头。
2. 在本地 HTML 里手写一个 `display:none` 的 `<a>`、一个正常链接和一个 `type="hidden"` 的 `<input>`，用 `selenium_honey_demo.py` 的思路（改成本地 `file://` URL）验证 `is_displayed()` 对三者的返回差异。
3. 写一个限速装饰器：让任意请求函数两次调用之间至少间隔 2 秒（含随机抖动），并统计 1 分钟内的实际 QPS，体会「基础间隔 + 抖动」的效果。
4. 选一个公开站点，先读它的 `robots.txt` 与服务条款，列出三条你计划遵守的规则，并在你的爬虫代码注释里写明依据。
5. 构造一个「假数据污染」实验：本地起一个简单 HTTP 服务，对携带蜜罐字段的 POST 返回伪造页面，对比正常响应，体会为什么踩蜜罐比被封更危险。
6. 用 DevTools 观察一个需要登录的站点：找出维持会话的 Cookie 是 `Set-Cookie` 种下的还是 JS 写入的，判断用 `requests.Session` 能否复现登录态。
