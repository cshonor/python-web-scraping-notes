# 第 16 章 并行网页抓取：学习笔记

前面章节写的爬虫都是「单线程串行」的：发一个请求，等它回来，解析，再发下一个。对几十页的抓取没问题，面对成百上千个 URL 时，绝大部分时间其实在**干等网络**，CPU 反而闲着。本章解决的就是这个问题：在**遵守限速与服务条款**的前提下，用多线程、多进程或异步 I/O 把「等待时间」重叠起来，提高抓取与处理的吞吐。核心机制一句话：抓取是典型的 **I/O 密集型**任务，线程在等待 socket 数据时会释放 **GIL**，因此即使受 GIL 约束，多线程依然能让多个网络请求真正并行推进；但这套思路对纯 Python 的 CPU 密集计算（如大规模正文解析）并不成立，那要换进程或协程模型。本章两个脚本分别演示「手写 `Queue` + `threading`」与「高层 `ThreadPoolExecutor`」两条路。

**本章目标**

1. 理解**线程 / 进程 / 协程**三种并发模型的分工，知道抓取场景为什么首选线程或协程
2. 理解 **GIL** 的作用范围：它限制的是 CPU 密集型多线程，而不是 I/O 等待
3. 会用 **`queue.Queue`** 实现线程安全的**生产者-消费者**模式，并用哨兵值优雅结束消费者
4. 会用 **`concurrent.futures.ThreadPoolExecutor`** 的高层 API 做并发请求并逐个取回结果
5. 识别共享可变状态带来的**竞争条件**，掌握「队列传递 / 加锁 / 每线程私有再合并」三种解法
6. 建立**限速与合规意识**：并行会放大 QPS，须配合并发上限、`sleep` 与 `robots.txt`

---

## 1. 核心知识点与原理

### 1.1 并发模型对比：线程、进程、协程

Python 里做并发有三条主流路线，成本与适用面各不相同：

| 模型 | 内存与隔离 | 启动/切换成本 | 能否占满多核 CPU | 适用场景 |
|---|---|---|---|---|
| **线程（`threading`）** | 共享同一进程内存，通信最简单 | 低 | 否（受 GIL 约束） | **I/O 密集**：网络、磁盘等待 |
| **进程（`multiprocessing` / `ProcessPoolExecutor`）** | 独立内存空间，天然隔离崩溃域 | 高（fork/spawn、IPC 序列化） | 是 | **CPU 密集**：解析、压缩、哈希 |
| **协程（`asyncio`）** | 单线程内协作式切换 | 最低（无系统线程开销） | 否 | 海量并发连接（数千路以上） |

网页抓取的时间大头花在「发出请求 → 等响应」这段网络上，属于教科书级的 I/O 密集任务，所以**多线程**是性价比最高的入门方案：代码与串行版差异最小，收益却立竿见影。进程的开销与 IPC 复杂度只有当「下载下来的正文要做重计算」时才值得；协程（如 aiohttp、httpx AsyncClient）吞吐上限最高，但要全面改写为 `async` / `await` 风格，学习曲线更陡。

实战选型可以按这个顺序问三个问题：

1. **并发量级多大？** 几十到几百路 → 线程池足够；几千路以上长连接 → 考虑协程。
2. **瓶颈在网还是在算？** 在网 → 线程/协程；在算 → 进程池，或与线程混用（下载用线程、解析用进程）。
3. **要长期维护吗？** 要 → 尽早评估 Scrapy 这类内置调度的框架（第 5 章），别手写调度。

多数「学习 + 中小规模」场景停在第一问就结束了：线程池是最短路径，这正是本章把它作为主线的原因。

### 1.2 GIL 与 I/O 密集型：为什么多线程对抓取有效

**GIL（全局解释器锁）** 是 CPython 的实现细节：同一时刻只有一个线程在执行 Python 字节码。直觉上这会让多线程「毫无用处」，但关键在于：**线程在执行阻塞式 I/O（如 `urlopen` 的 `recv`、`requests.get` 的等待）时会释放 GIL**，把执行权让给其他线程。于是「线程 A 在等网络时，线程 B 可以发自己的请求」，多个连接的在途时间被重叠起来，总耗时从「各请求之和」逼近「最慢的那一个」。

反过来说，如果任务是纯 Python 的字节码计算（比如对几万段文本跑复杂的正则清洗），GIL 会让多线程在多核机器上基本线性不起来 —— 此时应把计算放进 `ProcessPoolExecutor` 的子进程里，让 GIL 在各自进程中互不影响。一句话记忆：**多线程管「等」，多进程管「算」**。

加速比上也要管理预期：线程数从 1 加到 8，耗时不会精确变成 1/8。网络往返有波动、目标站会限速、本地 DNS 与连接建立也有串行段，实际收益随线程数增加而递减（Amdahl 定律的日常版）。经验做法是从小到大逐步调 `max_workers`，画出「线程数 — 总耗时」曲线，在收益明显变平的位置停下来，而不是直接开到几十上百。

### 1.3 竞争条件（Race Condition）

多个线程同时读写**同一个可变结构**（共享的 `list`、`set`、`dict`、计数器）时，交错执行可能导致丢失更新、读到中间态甚至抛异常。典型例子：

```python
results = []          # 共享可变结构

def scrape(url):
    body = fetch(url)
    results.append(len(body))   # 看似安全，换成 results += [...] 之类的复合操作就可能出问题
```

三种常用解法，按推荐度排序：

| 解法 | 做法 | 优点 | 缺点 |
|---|---|---|---|
| **队列传递** | 每个线程把结果 `q.put()` 进 `queue.Queue`，由单一消费者取出 | 无锁、顺序可控、天然串行化写入 | 多一个消费者线程的心智成本 |
| **加锁** | 共享区用 `with lock:` 保护 | 直接、改动小 | 锁粒度难把握，容易写出隐性串行 |
| **私有再合并** | 每个线程写自己的列表，主线程 `join` 后统一合并 | 完全无共享，最简单 | 结果不实时，内存峰值略高 |

本章两个示例恰好是前两种思路的体现：`queue_thread_scrape.py` 用队列把结果汇聚给消费者打印；`thread_pool_urls.py` 则干脆不共享任何状态，每个 future 独立返回 `(url, status_code)`，由主线程逐个 `fut.result()` 收取。

还有一个容易被忽视的细节：CPython 里 `list.append` 这类单步操作因 GIL 恰好是原子的，短 Demo 不加锁也常「看起来没事」。但这不是语言保证，换成复合操作（读-改-写）或换解释器实现就会翻车。工程代码不要赌实现细节 —— 该用队列就用队列。

### 1.4 Queue 与生产者-消费者模式

**`queue.Queue`** 是标准库提供的线程安全 FIFO：内部自带锁与条件变量，`put()` / `get()` 都是原子操作，比多个线程直接 `pop()` 一个共享 `list` 安全得多。它在抓取里有三种典型角色：

- **任务分发**：主线程（或上游爬虫）把待抓 URL `put` 进队列，多个 worker 线程各自 `get()` 领取 —— 天然实现负载均衡，谁空闲谁多干。
- **结果汇聚**：worker 把抓取结果 `put` 进结果队列，一个消费者线程统一写盘 / 打印，避免多线程同时写文件。
- **背压控制**：`Queue(maxsize=N)` 有容量上限，队列满时生产者会阻塞在 `put()`，防止「发现链接的速度远超抓取速度」时内存被 URL 撑爆。

消费者如何知道「活儿干完了」？常用**哨兵值**：生产者确认所有任务入队且 worker 结束后，往队列里 `put` 一个特殊对象（本章用 `None`），消费者 `get` 到它就退出循环。退出前记得补一次 `q.task_done()`，让队列的未完成计数归零：

```python
item = q.get()
if item is None:      # 哨兵
    q.task_done()
    break
```

配合 `q.task_done()` 与 `q.join()` 还能实现「等队列清空再退出主线程」的精确同步；若不打算用 `q.join()`，像本章脚本这样用「`join` 全部 worker → `put(None)` → `join` 消费者」的两段式收尾也足够严谨。`queue_thread_scrape.py` 用的正是这套模式。

### 1.5 ThreadPoolExecutor：高层并发抽象

手写 `threading.Thread` + `Queue` 灵活，但线程创建、`join`、异常回收全要自己管。**`concurrent.futures.ThreadPoolExecutor`** 把这些封装成「提交任务 → 拿回 Future → 遍历结果」三步：

```python
with ThreadPoolExecutor(max_workers=4) as ex:
    futures = {ex.submit(fetch, u): u for u in URLS}
    for fut in as_completed(futures):
        url, code = fut.result()
```

要点：

- **`max_workers`** 就是并发上限，线程复用而非每任务新建，开销更可控。
- **`ex.submit(fn, *args)`** 立即返回一个 `Future`，任务在池里异步执行。
- **`as_completed(futures)`** 按**完成先后**产出 future —— 谁先回来先处理谁，总耗时取决于最慢的任务而不是固定顺序。
- **`fut.result()`** 取返回值；若任务内部抛了异常，异常会在调用 `result()` 时**重新抛出**，因此遍历处是统一的异常捕获点。
- `with` 块退出时自动 `shutdown(wait=True)`，等所有任务收尾，不用手写 `join`。

对比手工线程方案：线程池少了「结果队列 + 消费者线程」一层，代码量减半；代价是结果的落地时机不再那么自由（若想边抓边写盘，还是队列模式顺手）。

### 1.6 限速、并发伦理与分布式扩展

并行最容易被忽视的一点是：**它会等比放大你对目标站的压力**。串行时 1 秒 1 个请求，开 16 个线程理论峰值就是 16 QPS —— 小站点可能直接被压垮，大站点会触发 403 / 429 封禁，甚至违反服务条款。基本纪律：

- 遵守 **`robots.txt`** 与站点条款，UA 里写明 bot 身份与联系方式（本章脚本 UA 已带 `educational` 标识）。
- 设置**并发上限**与 **`time.sleep` / 限速器**；Scrapy 用户则用 `DOWNLOAD_DELAY`、`AUTOTHROTTLE`（第 5 章）。
- 出错重试要有**指数退避**，别在 500 错误上立刻高频重打。

单机到顶之后的思路是**分布式**：用中央任务队列（Redis、RabbitMQ、Kafka 这类消息中间件）存待抓 URL，多台机器上的 worker 各自拉取、回传结果与新发现的链接，实现水平扩展。这套「中央调度 + 工人拉活」的结构与第 5 章 Scrapy 调度器的思想一致，只是跨出了单机边界。相比单机版，分布式要额外解决三件单机里几乎免费的事：

| 问题 | 单机里的解法 | 分布式里的解法 |
|---|---|---|
| **URL 去重** | 进程内一个 `set` 就够 | Redis 集合或布隆过滤器，全局可见 |
| **限速** | 局部 `sleep` / 令牌桶 | 按域名的全局限速器（如 Redis 计数 + 过期窗口） |
| **任务分配** | `queue.Queue` 内存队列 | 中央消息队列 + 确认机制，worker 崩溃可重投 |

没有这三件套就上多机，分布式只是把压力与重复请求放大得更快。学习阶段先用本章脚本把单机的并发原语吃透，分布式是「同一思想换存储」的自然延伸，而不是另一套知识。

---

## 2. 示例代码：基于 `Queue` 的多线程抓取（现代写法）

书中原始示例用的是低层 **`_thread`** 模块；本仓库改写为现代的 **`threading`**，并用 **`Queue` + 哨兵值** 结束消费者线程。两个脚本均已在 2026-11-02 用本仓库指定解释器实际运行验证，输出为真实结果。

### 2.1 `queue_thread_scrape.py`：Queue + threading 的生产者-消费者

演示最经典的并发抓取骨架：一个**消费者线程** `storage` 循环从队列取结果并打印；`main` 为 `URLS` 里每个 URL 起一个**工作线程** `scrape` 抓取页面，把「`URL -> 字节数`」或错误信息 `put` 进队列。所有 worker `join` 之后，主线程 `q.put(None)` 投递哨兵，消费者收到 `None` 即 `break` 退出。抓取侧带合规 `User-Agent` 与 25 秒超时，并用 `try / except (HTTPError, URLError, OSError)` 捕获网络异常 —— 失败不会让线程悄悄死掉，错误同样会进入队列被看到。消费者线程显式 `daemon=False`，靠 `consumer.join()` 保证主线程等它收尾。

主线程的收尾顺序值得单独记住：先 `join` 全部 worker（保证所有结果已入队），再 `put(None)` 投哨兵，最后 `join` 消费者（保证打印完再退出）。任何一步颠倒都会出问题 —— 先投哨兵会丢结果，不 `join` 消费者则主线程可能在最后一行打印前退出。类型标注 `Queue[str | None]` 也直白地表达了「队列里流动的是字符串或哨兵」这一约定。

关键代码摘录（完整文件见 `chapter-16/queue_thread_scrape.py`）：

```python
def storage(q: Queue[str | None]) -> None:
    while True:
        item = q.get()
        if item is None:      # 哨兵：结束消费者
            q.task_done()
            break
        print("存储:", item)
        q.task_done()

def scrape(url: str, q: Queue[str | None]) -> None:
    req = Request(url, headers={"User-Agent": "Chapter16QueueDemo/1.0 (educational)"})
    try:
        with urlopen(req, timeout=25) as resp:
            body = resp.read()
        q.put(f"{url} -> {len(body)} bytes")
    except (HTTPError, URLError, OSError) as e:
        q.put(f"{url} -> ERROR {e}")
```

运行命令：

```bash
cd chapter-16
python queue_thread_scrape.py
```

**已实测（2026-11-02）**：退出码 0，输出两行（顺序随线程完成先后可能变化）：

```text
存储: https://example.com/ -> 577 bytes
存储: https://example.com/?v=demo2 -> 577 bytes
```

两个 URL 返回的字节数相同，因为 `example.com` 对带 query 的请求返回同一份页面 —— 这正好说明「结果字节数」不等于「内容唯一性」，真实项目里去重要按规范化 URL 做。

### 2.2 `thread_pool_urls.py`：ThreadPoolExecutor 并发 requests

同一问题的线程池写法，更短更直白。`fetch(url)` 用 `requests.get(url, timeout=20)` 抓取并返回 `(url, status_code)` 元组；`main` 在 `max_workers=4` 的池里 `submit` 全部 URL，构造 `{future: url}` 的映射，再用 `as_completed` 按完成顺序遍历，`fut.result()` 取出结果打印。URL 列表只有两条（`example.com` 与 `iana.org/domains/reserved`），是刻意的小规模演示：脚本注释明确提醒「示例 URL，注意全局限速」。与 2.1 相比，这里没有任何共享状态，自然不存在竞争条件 —— 代价是异常处理集中在 `result()` 调用点，本例未捕获，网络失败会以 traceback 形式暴露，工程代码应在 `fetch` 内或遍历处补上。

关键代码摘录（完整文件见 `chapter-16/thread_pool_urls.py`）：

```python
def fetch(url: str) -> tuple[str, int]:
    r = requests.get(url, timeout=20)
    return url, r.status_code

def main() -> None:
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fetch, u): u for u in URLS}
        for fut in as_completed(futures):
            url, code = fut.result()
            print(url, code)
```

运行命令（依赖 `requests`，先装 `requirements.txt`；本章运行环境已装）：

```bash
cd chapter-16
pip install -r requirements.txt   # requests>=2.31.0
python thread_pool_urls.py
```

**已实测（2026-11-02）**：退出码 0，输出两行（顺序为完成先后）：

```text
https://example.com 200
https://www.iana.org/domains/reserved 200
```

两个站点均返回 200。注意 `as_completed` 的输出顺序**不保证**与 `URLS` 列表一致 —— 若业务需要稳定顺序，应改用 `ex.map(fetch, URLS)`（按提交顺序产出）或收集后排序。

两个脚本放在同一章不是重复，而是对照：2.1 展示「队列 + 手工线程」的完整控制面（结果实时流入消费者、可以加背压、落地时机自由），2.2 展示「线程池」的极简心智（无共享状态、三步走完）。选型原则很朴素：结果要边抓边处理、或任务来自上游持续流入，用队列模式；一次性把固定清单抓完、只要汇总结果，用线程池。两者之外的第三条路 `asyncio`，本章未展开，留待需要数千路并发时再学。

---

## 3. 学习贴士

- **法律与礼仪**：并行会等比放大 QPS；务必遵守 `robots.txt`、服务条款，设置合理的 `sleep` 与并发上限，避免对目标服务器与业务造成不当压力（并注意第 18 章的合规边界）。UA 里留真实联系方式是被封时唯一的沟通渠道。
- **调试顺序**：先在**单线程 + 有头浏览器**里把选择器与流程跑通，再上并行与无头环境。并行会把时序 bug（竞态、重复请求）放大成偶发故障，先消灭确定性 bug 能显著降低排错成本。
- **先测「串行基线」再上并发**：记录串行版总耗时与正确结果，并发改造后对比 —— 既能量化加速比，又能用「结果集合是否与串行一致」做最简单的正确性校验。发现不一致时，第一反应应该是怀疑共享状态（见 1.3），而不是怀疑网络。
- **工程首选**：高并发、长周期的抓取优先评估 **Scrapy 或专用下载框架**（第 5 章），它们内置调度、重试、限速与去重；裸线程适合中小规模、一次性任务，不要无限扩容。
- **超时与重试成对出现**：并发脚本里任何网络调用都必须带 `timeout`（本章两个脚本分别是 25 秒与 20 秒），否则一个挂起的连接会永久占住一个线程；重试次数要有上限并配合退避。

  补充一句：连接超时与读取超时语义不同，requests 可传元组 `(connect, read)` 分开控制，长列表抓取时读取超时不宜设太短。

---

## 4. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-16/queue_thread_scrape.py` | `Queue` + `threading` 生产者-消费者抓取：哨兵结束消费者、异常入队（已实测） |
| `chapter-16/thread_pool_urls.py` | `ThreadPoolExecutor(max_workers=4)` + `as_completed` 并发 `requests`（已实测） |
| `chapter-16/requirements.txt` | 本章依赖：仅 `requests>=2.31.0`（queue 脚本只用标准库） |
| `chapter-05/wikiSpider/` | 对照：Scrapy 用 Twisted 异步调度实现并发，内置限速与去重 —— 本章手工方案的「框架版」 |
| `chapter-06/sqlite_store.py` | 对照：并发抓到的数据如何幂等落库（`INSERT OR REPLACE`） |

把本章的两个脚本与第 5 章对照看很有意思：`queue_thread_scrape.py` 的「主线程发任务、worker 拉活、消费者收结果」正是 Scrapy「调度器 — 下载器 — Pipeline」的手工微缩版；理解了前者，后者的架构图就不再抽象。同理，本章的「结果汇聚进队列」与第 6 章的「结果落盘 / 落库」可以无缝拼接：把 `storage` 里的 `print` 换成 `csv.writer` 或 `sqlite3` 参数化插入，就是一个端到端的小型并发采集器。

---

## 练习建议

1. 为 `storage` 增加**写入文件锁**（`threading.Lock`），把结果写入同一文件，观察不加锁时多线程输出交错的复现条件；再把打印换成追加写文件，思考为何 `open(..., "a")` 的短写在多数平台上看似安全、跨平台却不可依赖。
2. 把 `queue_thread_scrape.py` 的 URL 列表扩到 20 个，给队列加 `Queue(maxsize=5)`，体会背压下生产者的阻塞行为。
3. 给 `scrape` / `fetch` 增加**最多 3 次、指数退避**的重试，并用一个无效域名验证错误路径确实走进了队列 / `result()` 异常分支。
4. 用 `concurrent.futures.ProcessPoolExecutor` 把「下载后对正文做 CPU 密集解析」的函数放到子进程，对比与纯线程版的总耗时。
5. 把 `thread_pool_urls.py` 的遍历从 `as_completed` 改成 `ex.map(fetch, URLS)`，验证输出顺序变为与 `URLS` 一致，并思考两种顺序各自适合什么下游。
6. 给两个脚本加 `time.sleep` 限速与总耗时统计，分别测 `max_workers=1 / 4 / 8` 的耗时曲线，直观感受「I/O 并发的边际收益递减」。
