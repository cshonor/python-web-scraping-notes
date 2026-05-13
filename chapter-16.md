# 第 16 章 并行网页抓取：学习笔记

本章讨论在**遵守限速与条款**的前提下，用**多线程、多进程或异步 I/O** 提高抓取与处理吞吐。

---

## 1. 核心知识点与原理

### 1.1 进程 vs 线程

- **线程**：共享同一进程内存，通信简单；**I/O 等待**（网络、磁盘）场景下，多线程常能提高利用率。纯 **Python CPU 密集**计算受 **GIL** 影响，多线程未必能占满多核。
- **进程**：独立内存空间，可绕过 GIL 利用多核，但 IPC 与启动成本更高，适合 CPU 密集解析或隔离崩溃域。

### 1.2 竞争条件（Race Condition）

多线程同时写入**同一可变结构**（如共享 `list`/`set`）可能导致丢失更新或异常。应使用 **`queue.Queue`**、**锁（`threading.Lock`）** 或「每线程私有结果再合并」等模式。

### 1.3 队列（Queue）

**`queue.Queue`** 提供线程安全的 FIFO，适合：任务分发（URL）、结果汇聚、背压控制。比多个线程直接 `pop` 共享 `list` 更安全。

### 1.4 分布式扩展（思路）

单机之外，可用**中央任务队列**（Redis、消息队列）+ 多个 worker 拉取 URL、回传新链接，实现水平扩展；仍需全局限速与去重（与第 5 章 Scrapy 调度思想一致）。

---

## 2. 示例代码：基于 `Queue` 的多线程抓取（现代写法）

书中示例使用 **`_thread`**；推荐改用 **`threading`**，并用 **`Queue` + 哨兵** 结束消费者线程。

可运行脚本：`code/chapter16/queue_thread_scrape.py`

```python
import threading
from queue import Queue
from urllib.request import Request, urlopen

def storage(q: Queue) -> None:
    while True:
        item = q.get()
        if item is None:
            q.task_done()
            break
        print("存储:", item)
        q.task_done()

def scrape(url: str, q: Queue) -> None:
    req = Request(url, headers={"User-Agent": "ParallelDemo/1.0"})
    with urlopen(req, timeout=20) as resp:
        body = resp.read()
    q.put(f"{url} -> {len(body)} bytes")

def main() -> None:
    q: Queue[str | None] = Queue()
    consumer = threading.Thread(target=storage, args=(q,))
    consumer.start()
    urls = ["https://example.com/", "https://example.com/?v=demo2"]
    workers = [threading.Thread(target=scrape, args=(u, q)) for u in urls]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    q.put(None)
    consumer.join()

if __name__ == "__main__":
    main()
```

---

## 3. 学习贴士

- **法律与礼仪**：并行会放大 QPS；务必遵守 **`robots.txt`**、服务条款与合理 **`sleep`/并发上限**，避免对目标服务器与业务造成不当压力（并注意第 18 章合规边界）。  
- **调试顺序**：先在**单线程 + 有头浏览器**跑通选择器，再上并行与无头环境，能显著减少排错成本。  
- **工程首选**：高并发抓取可优先评估 **Scrapy / 专用下载器**（第 5 章），而非裸线程无限扩容。

---

## 4. 与本仓库其他示例

`code/chapter16/thread_pool_urls.py`：`ThreadPoolExecutor` 版并发 `requests` 示例。

## 练习建议

1. 为 `storage` 增加**写入文件锁**，避免打印交错。  
2. 用 **`concurrent.futures.ProcessPoolExecutor`** 将 CPU 密集的解析函数放到子进程。  
3. 给队列增加**最大长度**，实现简单背压。
