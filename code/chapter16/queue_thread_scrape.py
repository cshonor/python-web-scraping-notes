"""第16章：Queue + threading 的简单并发抓取（替代书中 _thread 示例）。"""
from __future__ import annotations

import threading
from queue import Queue
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URLS = [
    "https://example.com/",
    "https://example.com/?v=demo2",
]


def storage(q: Queue[str | None]) -> None:
    while True:
        item = q.get()
        if item is None:
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


def main() -> None:
    q: Queue[str | None] = Queue()
    consumer = threading.Thread(target=storage, args=(q,), daemon=False)
    consumer.start()

    workers: list[threading.Thread] = []
    for u in URLS:
        t = threading.Thread(target=scrape, args=(u, q))
        t.start()
        workers.append(t)
    for t in workers:
        t.join()

    q.put(None)
    consumer.join()


if __name__ == "__main__":
    main()
