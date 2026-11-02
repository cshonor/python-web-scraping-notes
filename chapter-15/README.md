# 第 15 章 用爬虫测试网站：学习笔记

前面十几章一直在学「怎么用程序读网站」，本章把方向倒过来：用爬虫的同一套工具链去**测**网站。核心机制一句话——把「请求 + 解析 + 驱动浏览器」的能力当作测试工具用，在可控环境里重复执行场景、断言 DOM 状态、巡检链接并截图留证。这样做的好处是回归测试可以自动化：每次改完代码，让脚本替你把关键页面走一遍，比人肉点一遍可靠得多。本章用两个脚本分别覆盖两条路线：`unittest` + Selenium 做**交互行为测试**，`requests` + BeautifulSoup 做**链接健康巡检**。

**本章目标**

1. 理解标准库 **`unittest`** 的用例模型：`TestCase`、断言方法与运行器
2. 分清 **`setUp` / `tearDown`** 与 **`setUpClass` / `tearDownClass`** 的适用场景
3. 会用 Selenium 的 **`ActionChains`** 模拟拖放等真实用户交互
4. 会把「解析页面抽链接」的爬虫技巧改造成**同域链接巡检**工具
5. 知晓如何把 `python -m unittest` 接入 CI 流水线，并用截图辅助定位失败
6. 明确测试爬虫与生产爬虫的边界：只对准**授权环境**

---

## 1. 核心知识点与原理

### 1.1 `unittest` 模型：TestCase、断言与运行器

**单元测试**验证小单元行为是否符合预期。Python 标准库 **`unittest`** 提供了三件套：用例组织（`TestCase` 子类）、断言方法（`assertIn` / `assertEqual` / `assertTrue` 等）、运行器（`unittest.main()` 或 `python -m unittest`）。写一个测试类的最小流程是：

| 组成 | 作用 | 本章示例 |
|---|---|---|
| 继承 `unittest.TestCase` | 让运行器识别这是一个测试类 | `class TestDragAndDrop(unittest.TestCase)` |
| 以 `test_` 开头的方法 | 每个方法是一个独立用例 | `def test_drag(self)` |
| 断言方法 | 失败时抛出 `AssertionError`，标记用例失败 | `self.assertIn("bot", msg.lower())` |
| `unittest.main()` | 发现用例、执行、汇总报告 | 脚本末尾的入口 |

相比随手写 `assert`，`unittest` 的价值在于**结构化**：多个用例统一跑、失败单独计数、钩子函数自动管理环境。Selenium 这类重资源的测试尤其需要它。

常用断言方法速查：

| 断言 | 语义 | 典型场景 |
|---|---|---|
| `assertIn(a, b)` | `a` 是 `b` 的成员/子串 | 页面文案包含关键词（本章拖放断言） |
| `assertEqual(a, b)` | 两者相等 | 状态码、元素数量 |
| `assertTrue(x)` / `assertFalse(x)` | 布尔判断 | 元素是否存在、文件是否生成 |
| `assertIsNone(x)` / `assertIsNotNone(x)` | 同一性判断 | 资源句柄初始化检查 |
| `assertRaises(E)` | 捕获指定异常 | 验证错误分支被触发 |

断言失败时，`unittest` 会打印双方实际值的 diff 摘要，比裸 `assert` 的一行 `AssertionError` 好定位得多。

### 1.2 常用钩子：`setUp` 系与 `setUpClass` 系

- **`setUp` / `tearDown`**：每个用例前后各执行一次，适合做「每测一例都需要隔离环境」的准备/清理（如每例重启浏览器）。
- **`setUpClass` / `tearDownClass`**：整个测试类只执行一次，适合**昂贵资源**——启动一次浏览器，多个用例复用，全部跑完再关闭。

| 维度 | `setUp` / `tearDown` | `setUpClass` / `tearDownClass` |
|---|---|---|
| 执行次数 | 每用例各一次（N 例 = 2N 次） | 每类各一次（共 2 次） |
| 方法形态 | 实例方法，挂在 `self` | `@classmethod`，挂在 `cls` |
| 共享方式 | 每例新建，天然隔离 | 类属性共享，用例间有状态延续 |
| 适合 | 会互相污染的用例（登录态、表单残留） | 启动昂贵的只读资源（浏览器、驱动） |
| 代价 | 慢——每个用例都付一次启动成本 | 用例顺序敏感，污染会跨例传递 |

本章的 `selenium_drag_unittest.py` 用的就是后者：浏览器启动开销大（秒级），而拖放页面的测试用例之间不需要隔离，所以在 `setUpClass` 里一次性启动 Chrome 并加载页面，`tearDownClass` 里 `quit()`。两个钩子都是 `@classmethod`，通过 `cls.driver` 在类级别共享浏览器实例。

值得注意的一个健壮性写法：脚本在 `setUpClass` 里捕获了 `WebDriverException`，Chrome 不可用时抛出 **`unittest.SkipTest`** 而不是让 traceback 直接炸出来——这样在没有浏览器的 CI 节点上，用例被标记为「跳过」而非「失败」，语义更准确。

### 1.3 Selenium 交互动作链（`ActionChains`）

相比只解析静态 HTML，Selenium 能驱动真实浏览器模拟**点击、输入、拖放**等交互，更贴近真实用户路径。其中「拖放」这种复合动作用 `ActionChains` 描述：

| API | 作用 |
|---|---|
| `ActionChains(driver)` | 创建一个动作链，绑定到某个浏览器实例 |
| `.drag_and_drop(src, dst)` | 压入「从 src 元素拖到 dst 元素」这一动作 |
| `.perform()` | 真正执行链上积累的所有动作 |

关键点：动作链是**惰性**的，链式调用只是在排队，必须调用 `perform()` 才会实际下发给浏览器。本章脚本拖放后立刻读取 `#message` 元素的文本做断言——因为示例页逻辑简单、拖放反馈是同步的，所以没有引入显式等待；面对真实项目里的异步反馈，应配合 `WebDriverWait` 等待目标状态出现再断言（见第 3 节）。

此外 Selenium 支持 **`get_screenshot_as_file`** 保存页面快照，便于失败时人工复核或与基线图对比，这是纯 `requests` 测试做不到的。

### 1.4 链接巡检：把爬虫技巧倒过来用

第 2、3 章学的「GET 页面 → BeautifulSoup 抽 `<a href>` → `urljoin` 归一化」流程，换个用法就是网站健康检查工具：从入口页出发，收集所有**同域**链接，逐个发 `HEAD` 请求看状态码，就能发现 404、500、跳转链断裂等问题。与抓取数据的区别在于关注点：

| 维度 | 数据爬虫 | 链接巡检 |
|---|---|---|
| 目标 | 抽取内容落库 | 探测每个 URL 是否可达 |
| 请求方法 | GET（要正文） | HEAD（只要状态码，省带宽） |
| 范围控制 | 按规则跟链 | 严格限定同域，去重、去锚点 |
| 输出 | 结构化数据 | 状态码清单 + 异常记录 |

`link_checker.py` 用的 `HEAD` + `allow_redirects=True` 组合值得记住：`HEAD` 不下载正文，对被测站压力小；跟随重定向后打印的是**最终**状态码，能区分「301 到正常页」和「301 到错误页」。

### 1.5 接入 CI 与失败留证

测试脚本的归宿是流水线。把 `python -m unittest`（或 `pytest`）挂进 CI 的要点：

- **失败即红**：`unittest` 运行器在用例失败时以非零退出码结束，CI 天然能识别；
- **截图路径入档**：Selenium 用例失败时把 `get_screenshot_as_file` 的产物路径打进日志，并配置为 CI 的构建产物（artifact），事后可直接下载查看现场；
- **环境分层**：无浏览器的节点靠 `SkipTest` 自动跳过 Selenium 用例、只跑纯 HTTP 巡检；有浏览器的节点才跑完整套件。

一个最小 GitHub Actions 配置骨架（仅示意）：

```yaml
name: site-tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: browser-actions/setup-chrome@v1
      - run: pip install -r chapter-15/requirements.txt
      - run: python -m unittest discover -s chapter-15 -v
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          path: screenshots/
```

注意 `if: failure()`：只有测试红了才上传截图目录，绿色构建不浪费存储。

### 1.6 与「生产爬虫」的边界

测试应对准**授权环境**（自家 staging、公开测试站如 `example.com`、官方演示站），避免对无关站点高频探测（参见第 14 章）。本章两个脚本都遵守这条线：拖放用例只访问 `pythonscraping.com` 的官方演示页，链接巡检默认目标是为文档示例保留的 `example.com`，且每次探测间隔 0.5 秒限速。

---

## 2. 示例代码：`unittest` + Selenium 拖放

书中曾用 **PhantomJS**（已停止维护）；此处改为 **Chrome** + **Selenium 4** API（`By.ID` 等）。示例页：`https://pythonscraping.com/pages/javascript/draggableDemo.html`（若页面改版，断言文案需同步调整）。本章两个脚本按「浏览器交互 → 纯 HTTP 巡检」排列。

### 2.1 `selenium_drag_unittest.py`：拖放用例

演示把一次拖放操作固化成可重复执行的单元测试。`setUpClass` 里以 `--headless=new --disable-gpu --no-sandbox` 启动无头 Chrome（Chrome 不可用时抛 `SkipTest` 跳过），并加载演示页一次；`test_drag` 用例按 ID 定位源元素 `#draggable` 与目标容器 `#div2`，用 `ActionChains` 执行拖放，然后读取 `#message` 文本断言其中包含 "bot"；`tearDownClass` 负责 `quit()`。浏览器实例通过类属性 `driver`（初值 `None` 哨兵）在钩子与用例之间共享。

```python
URL = "https://pythonscraping.com/pages/javascript/draggableDemo.html"

class TestDragAndDrop(unittest.TestCase):
    driver = None

    @classmethod
    def setUpClass(cls) -> None:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        try:
            cls.driver = webdriver.Chrome(options=options)
        except WebDriverException as e:
            raise unittest.SkipTest(f"Chrome WebDriver 不可用: {e}") from e
        cls.driver.get(URL)

    def test_drag(self) -> None:
        assert self.driver is not None
        element = self.driver.find_element(By.ID, "draggable")
        target = self.driver.find_element(By.ID, "div2")
        ActionChains(self.driver).drag_and_drop(element, target).perform()
        msg = self.driver.find_element(By.ID, "message").text
        self.assertIn("bot", msg.lower())
```

```bash
cd chapter-15
pip install -r requirements.txt   # 需要 selenium>=4.15.0，且本机装有 Chrome
python -m unittest selenium_drag_unittest -v
# 或：python selenium_drag_unittest.py
```

**未实测**：本机未安装 Chrome、当前 Python 环境也未装 `selenium`，脚本无法实际运行。逐层梳理过的逻辑要点：`setUpClass` 的 `SkipTest` 分支保证无浏览器环境下用例被跳过而非报错；`test_drag` 首行的 `assert self.driver is not None` 是类型收窄哨兵；断言用 `msg.lower()` 做了大小写归一，对页面文案的大小写变化更宽容。该页面无异步反馈，故脚本未使用显式等待——移植到真实项目时应加 `WebDriverWait`。

三个 Chrome 启动参数的含义：

| 参数 | 作用 | 为什么测试里要加 |
|---|---|---|
| `--headless=new` | 启用新版无头模式 | CI 节点没有显示器，无头才能跑 |
| `--disable-gpu` | 禁用 GPU 加速 | 无头环境下 GPU 初始化常失败，禁掉更稳 |
| `--no-sandbox` | 关闭沙箱 | 容器/CI 里权限受限，沙箱会导致浏览器起不来（本机调试可去掉） |

### 2.2 `link_checker.py`：同域链接巡检

不依赖浏览器的纯 HTTP 巡检器。流程：建 `requests.Session`（统一 UA 为 `LinkCheckerDemo/1.0`）→ `GET` 起始页并 `raise_for_status()` → BeautifulSoup（`lxml` 解析器）抽所有 `<a href>` → `urljoin` 归一化为绝对 URL → 只保留 `http(s)` 且 `netloc` 与起始页相同的**同域**链接，并切掉 `#` 锚点后放入 `set` 去重 → 对排序后的每个 URL 发 `HEAD`（跟随重定向、10 秒超时）打印 `状态码 URL`，异常打印 `ERR` 行 → 每次探测后 `time.sleep(0.5)` 礼貌限速。

```python
START = "https://example.com/"
DELAY = 0.5

session = requests.Session()
session.headers["User-Agent"] = "LinkCheckerDemo/1.0"
r = session.get(START, timeout=15)
r.raise_for_status()
soup = BeautifulSoup(r.text, "lxml")
origin = urlparse(START).netloc
links: set[str] = set()
for a in soup.find_all("a", href=True):
    u = urljoin(START, a["href"])
    if urlparse(u).scheme.startswith("http") and urlparse(u).netloc == origin:
        links.add(u.split("#")[0])
for u in sorted(links):
    try:
        h = session.head(u, allow_redirects=True, timeout=10)
        print(h.status_code, u)
    except requests.RequestException as e:
        print("ERR", u, e)
    time.sleep(DELAY)
```

```bash
cd chapter-15
python link_checker.py   # 只需 requests + beautifulsoup4（+ lxml）
```

URL 处理管道逐环拆解（这是从第 2、3 章沿用来的老功夫）：

| 步骤 | 代码 | 作用 |
|---|---|---|
| 抽取 | `soup.find_all("a", href=True)` | 只拿带 `href` 的 `<a>`，跳过锚点占位标签 |
| 归一化 | `urljoin(START, a["href"])` | 把相对路径（`/about`、`../x`）拼成绝对 URL |
| 协议过滤 | `scheme.startswith("http")` | 排除 `mailto:`、`javascript:`、`tel:` 等非 HTTP 链接 |
| 同域过滤 | `netloc == origin` | 只测本站，外链不归你巡检 |
| 去锚点去重 | `u.split("#")[0]` 入 `set` | `page#s1` 与 `page#s2` 是同一个资源，只测一次 |

**已实测**：脚本以退出码 0 正常结束、无输出行。原因是当前 `example.com` 首页（实测返回 200，全文约 577 字节）**不含任何 `<a href>` 标签**，同域链接集合为空，循环体一次都不执行——这恰好验证了脚本的边界行为：空集合时不报错、静默退出。若把 `START` 换成含站内链接的授权测试页，即可看到逐行的状态码输出。

---

## 3. 学习贴士

- **昂贵资源放 `setUpClass`**。浏览器、数据库连接池这类秒级开销的准备，放进类级钩子一次完成；但要接受用例间共享状态的代价——若用例会互相污染（登录态、页面停留位置），退回 `setUp` 每例重建，或在用例开头手动复位。
- **用 `SkipTest` 表达「环境不满足」**。依赖外部资源（浏览器、特定服务）的用例，环境缺失时跳过比失败更能说明问题，CI 报告里红绿含义才不会失真。
- **异步页面必须配显式等待**。本章示例页拖放反馈是同步的所以能直接断言；真实项目里 `WebDriverWait(driver, 10).until(...)` 等待目标元素/文案出现再断言，能消除绝大部分「偶发红」。
- **巡检脚本的三个好习惯**：`HEAD` 代替 `GET` 省带宽、`set` + 去锚点去重、`time.sleep` 限速——这三点让工具可以安全地对自家站点反复跑。
- **失败时截图入档**。在 `tearDown` 里判断用例是否失败，失败则 `get_screenshot_as_file` 存图并把路径写进日志，CI 配置为构建产物，排错效率天差地别。

---

## 4. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-15/selenium_drag_unittest.py` | 本章主示例：`unittest` + Selenium 4 拖放用例，类级钩子复用浏览器、断言 `#message` 文案（需本机 Chrome，未实测） |
| `chapter-15/link_checker.py` | 同域链接巡检：`HEAD` 探测 + 0.5s 限速 + 状态码汇总，不依赖浏览器（已实测，空链接集正常退出） |
| `chapter-15/requirements.txt` | 本章依赖：`requests>=2.31.0`、`beautifulsoup4>=4.12.0`、`selenium>=4.15.0` |

与第 2、3 章对照看：`link_checker.py` 的「抽链接 + `urljoin` + 域名过滤」就是早期章节爬虫循环的骨架，只是把「跟链抓内容」换成了「探测状态码」。与第 12 章（Selenium 抓取动态页）对照看：同一个驱动器，那边用来**读**渲染后的 DOM，本章用来**改**页面状态并断言结果——工具相同，意图相反。

---

## 练习建议

1. 把拖放断言改为**截图文件存在且大小大于某阈值**：在 `perform()` 后调用 `get_screenshot_as_file("after_drag.png")`，断言文件生成且非空。
2. 用 **`unittest.mock`** 模拟 `requests.get` / `session.head`，把 `link_checker.py` 的解析与巡检逻辑拆成可单测的函数，在无网络环境下跑通用例。
3. 给 `test_drag` 加一条**反向用例**：拖放前先读 `#message` 文本，断言此时**不含** "bot"，拖放后再断言包含，构成完整的状态迁移验证。
4. 为登录流程写一个 **`setUpClass` 登录一次、多个用例复用 Session** 的草图（注意 Cookie 过期与用例间状态污染问题）。
5. 改造 `link_checker.py`：把起始页发现的所有同域链接再各自 GET 一遍、收集二级链接，形成两层巡检；统计 2xx / 3xx / 4xx / 5xx 的分布并汇总输出。
6. 写一个最小 CI 配置（如 GitHub Actions）：安装 Chrome 与依赖后运行 `python -m unittest discover -v`，并把失败时的截图目录上传为构建产物。
