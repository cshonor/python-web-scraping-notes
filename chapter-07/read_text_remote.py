"""第7章：读取远程纯文本（decode 与编码意识）。"""
from __future__ import annotations

import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = "https://www.pythonscraping.com/pages/files/story.txt"


def main() -> int:
    req = Request(URL, headers={"User-Agent": "Chapter07TextDemo/1.0 (educational)"})
    try:
        with urlopen(req, timeout=20) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
    except (HTTPError, URLError, OSError) as e:
        print("请求失败:", e, file=sys.stderr)
        return 1

    text = raw.decode(charset, errors="replace")
    print(text[:800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
