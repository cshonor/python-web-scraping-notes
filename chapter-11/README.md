# 第 11 章 抓取 JavaScript：学习笔记

前面所有章节的抓取都建立在同一个假设上：服务器返回的 HTML 里就有正文。本章处理这个假设失效的情况 —— 越来越多的站点首包只返回一个「空壳 HTML」，里面只有模板骨架和脚本引用，正文由浏览器执行 JavaScript 拉取 JSON 后再拼进 DOM，因此 `urllib` / `requests` 抓回来的永远只是那副骨架。核心机制一句话概括：**用真实浏览器内核执行页面 JS，配合等待策略等目标节点出现，再取渲染后的 DOM**。这正是第 1 章第 4 点「`urlopen()` 不会自动加载图片、CSS、JS，只拿到单次响应字节流」的直接推论：要拿到 JS 渲染的结果，就得有一个真正会跑 JS 的东西。

**本章目标**

1. 说清 **CSR（客户端渲染）**、**Ajax**、**DHTML** 三个概念的区别，以及它们在 DevTools 中的表征
2. 理解为什么「在 Python 里直接执行站点 JS」不现实，工程上必须借真实浏览器内核
3. 掌握三种等待策略（固定延迟 / 隐式等待 / 显式等待）的语义与选型，默认用**显式等待**
4. 会用 **Selenium 4 + 无头 Chrome** 写「等待元素出现再取数」的完整脚本
5. 会用 **Playwright** 写等价脚本，理解它与 Selenium 在驱动模型、API 风格上的差异
6. 知道 **PhantomJS** 已停止维护，能识别旧书旧文里的相关写法并迁移到现代方案

---

## 1. 核心知识点与原理

### 1.1 动态网页的挑战：CSR、Ajax 与 DHTML

「动态网页」是一个笼统的说法，拆开来其实是三件事：

| 概念 | 全称 | 是什么 | 在 DevTools 中的表征 |
|---|---|---|---|
| **CSR** | Client-Side Rendering | 首包 HTML 只是模板与脚本，正文由浏览器拉数据后拼进 DOM | `view-source:` 里看不到正文，Elements 面板里能看到 |
| **Ajax** | Asynchronous JavaScript + XML | 不整页刷新地与服务器交换数据并局部更新 DOM（名字里有 XML，如今实际多为 JSON） | Network 面板 `Fetch/XHR` 分类下出现额外请求 |
| **DHTML** | Dynamic HTML | 广义指用客户端脚本改动 DOM / CSS 的一类技术，常与 Ajax 同时出现 | 无独立表征，是行为描述而非协议 |

对爬虫的影响可以归结成一条：**静态抓取拿到的是「渲染前」的 HTML，而你要的数据在「渲染后」的 DOM 里**。判断一个页面是不是 CSR 的最快方法：对比 `view-source:`（服务器原始响应）与 Elements 面板（渲染后 DOM）的内容差异；再打开 Network 面板筛选 `Fetch/XHR`，看页面加载后是否还有后续请求带回正文数据。如果正文能在某个 XHR 的 JSON 响应里直接找到，优先考虑第 12 章的思路 —— 直接复现那个接口，而不是上浏览器。

### 1.2 为什么不能「在 Python 里执行 JS」

直觉上的诱惑是：把页面里的 JS 抠出来，用一个 JS 引擎（比如 V8）跑一遍不就行了？工程上走不通，原因是现代前端代码不是纯计算脚本：

- **依赖浏览器环境**：代码里到处是 `document`、`window`、`fetch`、事件回调，这些不是 JS 语言的一部分，而是浏览器注入的宿主对象；脱离 DOM 树，绝大多数代码第一行就抛错。
- **执行是事件驱动的**：数据填充发生在网络回调、定时器回调里，不是「跑一遍就结束」的同步过程，必须有一个完整的事件循环和网络栈配合。
- **依赖链极深**：一个真实页面往往串联几十个打包后的 bundle，还涉及 CSSOM 计算、布局、字体加载，重建这套环境等于自己写一个浏览器。

所以结论很朴素：**要 JS 渲染的结果，就用真正的浏览器**。自动化工具的价值是把「开浏览器、等渲染、取 DOM」变成可编程的三步。

### 1.3 工具演进：PhantomJS 已成历史

旧版教材和旧博文里经常出现 **PhantomJS** —— 一个无头的 WebKit 浏览器，曾是「无界面渲染」的代名词。需要记住的事实只有一条：**PhantomJS 项目已停止维护**，内核停留在多年前的 WebKit，对现代前端（ES6+、新 CSS）兼容性差，任何新代码都不应再依赖它。识别旧代码的标志性写法：

```python
# PhantomJS 已停止维护；请勿在新项目中依赖
# driver = webdriver.PhantomJS(executable_path=phantomjs_path)
```

现代替代方案是 **Headless Chrome / Firefox**（Selenium 驱动）或 **Playwright**（自带浏览器二进制）。Selenium 4 起 API 也有一次迁移：旧的 `find_element_by_id(...)` 系列方法已弃用，统一改为 `find_element(By.ID, ...)` 风格，本章脚本用的就是新写法。

### 1.4 Selenium 与 Playwright 对比

两者都能完成任务，但驱动模型和工程体验不同：

| 维度 | Selenium 4 | Playwright |
|---|---|---|
| 驱动模型 | 走 **WebDriver** 协议，浏览器与驱动（chromedriver 等）分离 | 通过自家协议直连浏览器，**无独立驱动进程** |
| 浏览器二进制 | 用本机已装的 Chrome / Firefox / Edge | `playwright install` 下载**内置**浏览器，版本锁定 |
| 驱动匹配 | 4.6+ 自带 **Selenium Manager** 自动解析驱动，不必手写路径 | 无需匹配，安装即配套 |
| API 风格 | 经典、资料多；等待靠 `WebDriverWait` + 条件对象 | 现代链式 API；`locator` 自带自动等待 |
| 适用倾向 | 已有 Selenium 资产的团队、需要对接 WebDriver 生态 | 新项目、CI 环境、多浏览器一致性要求高 |

两个脚本抓的是同一个示例页（`https://pythonscraping.com/pages/javascript/ajaxDemo.html`：点击后由 Ajax 填充内容的演示页），逻辑完全同构：打开页面 → 等 `#loadedButton` 出现 → 取 `#content` 文本。对照着读最能体会 1.4 表中的差异。

### 1.5 等待策略三选一（本章最易混的概念）

页面加载是异步的，「什么时候取数」比「怎么取数」更容易出错。三种策略对比：

| 策略 | 写法 | 语义 | 评价 |
|---|---|---|---|
| 固定延迟 | `time.sleep(n)` | 无脑等 n 秒 | 实现简单但**慢且不稳**：短了没加载完，长了纯浪费；注意它**不是**隐式等待 |
| 隐式等待 | `driver.implicitly_wait(seconds)` | `find_element` 找不到时**轮询**一段时间再抛错 | 全局生效，一处设置影响所有查找，容易拖慢整个脚本，慎用 |
| 显式等待 | `WebDriverWait` + `expected_conditions` | 对**具体条件**（元素出现、可点击、文本出现）轮询，超时再失败 | **推荐**：只等该等的，语义清晰，超时可捕获 |

显式等待的典型形态（与 `selenium_ajax_wait.py` 一致）：

```python
WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.ID, "loadedButton"))
)
content = driver.find_element(By.ID, "content").text
```

语义是：最多等 15 秒，期间不断轮询 DOM，一旦 `#loadedButton` 出现立刻继续。Playwright 里对应的是 `page.wait_for_selector("#loadedButton", timeout=15_000)`，同样属于「针对具体条件的显式等待」。

对照看另外两种写法的形态与问题：

```python
# 固定延迟：短了拿不到，长了干等，且与隐式等待无关
import time
driver.get(url)
time.sleep(3)

# 隐式等待：全局生效，之后每次 find_element 找不到都会先轮询
driver.implicitly_wait(10)
button = driver.find_element(By.ID, "loadedButton")
```

`time.sleep` 的问题在批处理里会被放大：每页多睡 2 秒，一万页就是五个多小时的纯浪费。隐式等待看似省事，但它是「所有查找共享」的全局开关，一个本来就慢的元素会拖住后续所有 `find_element` 的报错时机。显式等待把「等什么、等多久、等不到怎么办」都限定在单个调用里，语义最干净，这也是本章脚本只用它、并把超时单独 `except` 的原因。

### 1.6 SPA 路由：URL 变了不一定是「跳转」

单页应用（SPA）用 **History API / `pushState`** 在客户端改写 URL，页面内容随之切换，但**不发生新的 HTTP 导航**—— 从网络层看可能一个请求都没有，状态码层面也谈不上 3xx。对自动化来说这意味着「等页面跳转」不能等响应码：Playwright 用 `page.wait_for_url(...)`，Selenium 则轮询 `driver.current_url` 或等待新视图的根节点出现。这是第 2 节「重定向」条目的原理背景。

---

## 2. 异常处理与重定向（易错点）

1. **元素未找到 / 超时**：JS 未完成时 DOM 不完整，此时 `find_element` 直接抛 `NoSuchElementException`，显式等待超时则抛 `TimeoutException`。对策是在每个关键步骤前加显式等待，并像 `selenium_ajax_wait.py` 那样 `except TimeoutException` 单独处理 —— 打印可读的错误信息并以非零退出码结束，而不是让 traceback 淹没真正的原因。

2. **客户端路由造成的「假跳转」**：SPA 用 `pushState` 改 URL 时，HTTP 层可能仍是 200，等「跳转完成」不能用响应码。Playwright 用 `wait_for_url` 等待 URL 变化，Selenium 则轮询 `driver.current_url` 或等待新视图的根节点；否则会在旧视图上用新选择器，拿到一堆「元素不存在」。

3. **驱动与浏览器版本不匹配**：Selenium 走 WebDriver 协议，驱动（chromedriver）与浏览器主版本必须大致匹配。Selenium 4.6+ 的 Selenium Manager 会自动解析并下载匹配的驱动，通常不必手写 `executable_path`；但在 CI 环境里浏览器版本可能漂移，建议固定浏览器版本号，让「昨天能跑今天挂」有确定的原因可查。

4. **无头模式被站点识别**：部分站点检测 `navigator.webdriver`、缺少插件、异常视口等无头特征而拒绝服务或返回简化页。排错时先关掉 headless 用有头模式观察真实交互（配合 DevTools），确认是逻辑问题还是风控问题；是后者的话，降低频率、补合理 UA 往往比硬改指纹更可持续。

5. **选择器随页面改版失效**：动态站点的 class 名常是构建工具生成的哈希串（如 `css-1x2f3ab`），改版即变。定位器优先级建议是：语义化属性（`data-testid` 之类）> `By.ID` > 稳定的结构 CSS > XPath 长路径。选择器失效应被视为「必然事件」，脚本要在异常信息里带上当时等待的目标，方便事后定位。

6. **服务端重定向与示例页下线**：服务端 3xx 由浏览器自动跟随，脚本里 `driver.get` / `page.goto` 之后的落地 URL 可能与初始 URL 不同，断言时要以落地 URL 为准。另一个现实风险是示例站下线或改版（如本章用的 `ajaxDemo.html`），届时应换自建演示页并**同步修改等待条件与选择器**，而不是怀疑代码写错。

7. **资源泄漏**：浏览器进程比 HTTP 会话重得多，忘了 `driver.quit()` / `browser.close()` 会在跑批时积累一堆僵尸进程、吃光内存。本章三个脚本都把释放放在 `finally`（或 Playwright 的 `with` / `finally` 组合）里，这个结构要原样保留，不要图省事删掉。

8. **iframe 与新窗口句柄**：目标节点在 iframe 里时，顶层文档的 `find_element` 永远找不到它，必须先 `driver.switch_to.frame(...)`（Playwright 用 `page.frame_locator(...)`）；链接打开新标签页时同理，Selenium 要在 `driver.window_handles` 间切换。表现都是「页面明明有、代码说没有」，排查时先确认节点所在的文档层级。

---

## 3. 可直接运行的 Python 示例代码

环境准备（按需安装，只读代码不跑可不装）：

```bash
cd chapter-11
pip install -r requirements.txt          # selenium>=4.15.0, playwright>=1.40.0
python -m playwright install chromium    # 仅 Playwright 脚本需要
```

注意：Selenium 脚本需本机已安装 Chrome（Selenium Manager 自动配驱动）；Playwright 脚本需先拉取内置浏览器。本笔记写作环境中两者均未安装，故三个脚本**均未实测**（`rendered_title.py` 的缺依赖降级路径除外，见 3.3），输出以脚本逻辑为准，不杜撰运行结果。

共用示例页：`https://pythonscraping.com/pages/javascript/ajaxDemo.html`（3.1 与 3.2 的目标）。该页初始 HTML 里没有正文，页面脚本发起 Ajax 取回内容后才出现 `#loadedButton` 与填充后的 `#content`，正好用来验证「等渲染、再取数」这条链路；若站点日后下线，换自建演示页即可，等待条件与选择器需同步调整。

### 3.1 `selenium_ajax_wait.py`：Selenium 4 + 显式等待

这是本章的主示例，完整演示「无头 Chrome + 显式等待」抓 Ajax 页面。`get_dynamic_content` 先配 `ChromeOptions`（`--headless=new`、`--disable-gpu`、`--no-sandbox`），启动失败时向 stderr 打印安装提示并返回 1；随后 `driver.get(url)` 打开示例页，用 `WebDriverWait(driver, 15)` 等 `#loadedButton` 出现 —— 这正是 1.5 节的显式等待；条件满足后取 `#content` 的文本打印。`TimeoutException` 被单独捕获（报「未在限定时间内找到 #loadedButton」），`finally` 里保证 `driver.quit()`。整个函数返回退出码，`__main__` 用 `SystemExit` 透传，方便脚本化调用。

关键代码摘录：

```python
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
driver = webdriver.Chrome(options=options)
driver.get(url)
WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.ID, "loadedButton"))
)
content = driver.find_element(By.ID, "content").text
```

运行（需本机 Chrome + selenium，本机未装 Chrome 驱动环境，**未实测**）：

```bash
cd chapter-11
python selenium_ajax_wait.py
```

### 3.2 `playwright_ajax_demo.py`：Playwright 版同构脚本

与 3.1 抓同一个页面、同一条逻辑链，用来对照 1.4 表的差异。脚本在函数体内 `try` 导入 `sync_playwright`，缺依赖时打印安装提示返回 1，而不是启动即炸；随后 `sync_playwright()` 起运行时，`p.chromium.launch(headless=True)` 拉起内置 Chromium，`page.goto(url, wait_until="domcontentloaded", timeout=30_000)` 只等 DOM 就绪（不等全部资源，更快），再 `page.wait_for_selector("#loadedButton", timeout=15_000)` 做显式等待，最后 `page.locator("#content").inner_text()` 取文本。注意它没有独立的驱动进程 —— 这是与 Selenium 最实质的架构区别；异常统一捕获后 `finally` 里 `browser.close()`。

关键代码摘录：

```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_selector("#loadedButton", timeout=15_000)
    txt = page.locator("#content").inner_text()
```

运行（需 `playwright install chromium`，本机未装 playwright，**未实测**）：

```bash
cd chapter-11
python playwright_ajax_demo.py
```

### 3.3 `rendered_title.py`：Playwright 最小示例

只保留最小闭环：打开 `https://example.com`，打印渲染后的 `page.title()`。结构上同样有缺依赖降级（`ImportError` 时提示 `pip install playwright && playwright install chromium` 并返回 1），`goto` 用 `wait_until="domcontentloaded"` 加 30 秒超时，`finally` 保证 `browser.close()`。它适合当「环境自检脚本」：能打出 `title: Example Domain` 就说明 Playwright 与浏览器二进制都装好了，再跑 3.2 的 Ajax 示例才有意义。它不是纯解析脚本（依赖浏览器内核），无法在缺浏览器的环境验证渲染结果。

关键代码摘录：

```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://example.com", wait_until="domcontentloaded", timeout=30_000)
    print("title:", page.title())
```

运行（本机未装 playwright，**渲染路径未实测**；缺依赖的优雅降级路径已实测：打印安装提示到 stderr，退出码 1）：

```bash
cd chapter-11
python rendered_title.py
```

### 3.4 三个脚本的对照

| 脚本 | 工具 | 等待方式 | 缺依赖时的行为 | 定位 |
|---|---|---|---|---|
| `selenium_ajax_wait.py` | Selenium 4 + 本机 Chrome | `WebDriverWait` + `presence_of_element_located`，15 秒 | 启动异常 → stderr 提示 + 返回 1 | 主示例，WebDriver 生态 |
| `playwright_ajax_demo.py` | Playwright + 内置 Chromium | `wait_for_selector`，15 秒；`goto` 另给 30 秒 | `ImportError` → 打印安装命令 + 返回 1 | 同逻辑对照，无独立驱动 |
| `rendered_title.py` | Playwright + 内置 Chromium | 仅 `goto` 的 30 秒超时，无元素等待 | 同上 | 最小闭环 + 环境自检 |

选型建议：已有 Selenium 资产或需对接 WebDriver 生态用 3.1 的写法；新项目、CI 环境优先 Playwright 系（3.2 / 3.3），省去驱动匹配问题；任何环境下都先跑通 3.3 再跑 Ajax 示例，把「环境问题」与「逻辑问题」分开排查。

---

## 4. 学习贴士

- **先 Network 再浏览器**。很多「动态页面」的正文其实就在某个 XHR 的 JSON 里（第 12 章的主题）。能用 `requests` 复现接口就不要上全浏览器 —— 速度快一个数量级，还没有驱动版本、浏览器二进制这些维护负担。浏览器自动化是兜底方案，不是默认方案。
- **调试优先有头**。排错时把 headless 关掉，让真实窗口弹出来配合 DevTools 看：元素到底出没出现、等待条件是不是写错了节点。逻辑确认无误后再切回无头跑批。
- **与 BeautifulSoup 衔接**。`driver.page_source`（Selenium）或 `page.content()`（Playwright）拿到的是渲染后的完整 HTML，可以交给 BeautifulSoup 做复杂解析；但简单取数直接用 Selenium / Playwright 的定位器往往更省事，别为了用 bs4 而用 bs4。
- **定位器求稳不求巧**。优先 ID 与语义化属性（`data-testid`），避免构建产物式的哈希 class 和脆弱的 XPath 长路径；选择器写法集中放在脚本顶部，改版时改一处即可。
- **把等待条件当断言写**。等待条件本身就是「页面已就绪」的业务断言（等 `#loadedButton` 而不是等 2 秒），条件选得准，脚本在快慢网络下都稳；这也是显式等待优于 `time.sleep` 的根本原因。

---

## 5. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-11/selenium_ajax_wait.py` | 主示例：Selenium 4 无头 Chrome + `WebDriverWait` 显式等待抓 Ajax 演示页（未实测，需本机 Chrome） |
| `chapter-11/playwright_ajax_demo.py` | 同逻辑的 Playwright 版：`wait_for_selector` + `locator`，无独立驱动进程（未实测，需 `playwright install chromium`） |
| `chapter-11/rendered_title.py` | Playwright 最小闭环：渲染并打印 `example.com` 标题，兼作环境自检（渲染路径未实测；缺依赖降级路径已实测） |
| `chapter-11/js-debug-notes.md` | 接口发现与前端调试补充：Network 面板筛 `Fetch/XHR` 抄接口、「Copy as cURL」复现、识别 `__NEXT_DATA__` 类内嵌状态、逆向合规提醒 |
| `chapter-11/requirements.txt` | 本章依赖：`selenium>=4.15.0`、`playwright>=1.40.0`；只读代码不跑脚本可不装 |
| `chapter-01/README.md`（前置） | 「urllib 不会自动加载图片、CSS、JS」—— 本章问题的理论起点 |
| `chapter-12/README.md`（后续） | 若正文在 XHR JSON 里，直接抓接口是更便宜的路线，与本章互为备选 |

---

## 练习建议

1. 把 3.1 的显式等待条件从「元素出现」改为「文本包含某子串」（`EC.text_to_be_present_in_element`），体会等待条件即业务断言的写法。
2. 用 Playwright 的 `page.route` 拦截示例页的 XHR，打印其 JSON 响应体（仅限合法测试页），对照 `js-debug-notes.md` 里的接口发现流程。
3. 对同一 URL 分别保存 `view-source:` 内容与 `page.content()` 的输出，比较长度与内容差异，写三行结论说明差异来自哪些 JS 行为。
4. 故意把等待条件改成不存在的选择器跑一次，观察 `TimeoutException`（Selenium）与 Playwright 的报错形态，记录两者报错里哪些信息对定位最有用。
5. 把 3.1 改造成上下文管理器（`with` 包裹 driver），对比 `try/finally` 版本，说明两种资源释放方式在异常路径下的等价性。
6. 找一个含 iframe 的演示页（或自建一个），用 `driver.switch_to.frame` / `page.frame_locator` 各取一次其中的节点，体会第 2 节第 8 条「文档层级」问题。
