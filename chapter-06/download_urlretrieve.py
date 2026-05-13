"""第6章：演示将远程图片保存到本地（书中常用 urlretrieve 思路）。"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlretrieve

# Python 官方站点静态资源；仅作小文件下载演示
URL = "https://www.python.org/static/img/python-logo.png"
OUT = Path(__file__).resolve().parent / "_demo_python_logo.png"


def main() -> int:
    try:
        urlretrieve(URL, OUT)
    except (HTTPError, URLError, OSError) as e:
        print("下载失败:", e, file=sys.stderr)
        return 1
    print("已保存:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
