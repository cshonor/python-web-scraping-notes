"""第7章：远程 PDF 抽取文本（pdfminer.six，高层 extract_text）。"""
from __future__ import annotations

import sys
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = "https://pythonscraping.com/pages/warandpeace/chapter1.pdf"


def main() -> int:
    try:
        from pdfminer.high_level import extract_text
    except ImportError:
        print("请安装: pip install pdfminer.six", file=sys.stderr)
        return 1

    req = Request(URL, headers={"User-Agent": "Chapter07PdfDemo/1.0 (educational)"})
    try:
        with urlopen(req, timeout=40) as resp:
            data = resp.read()
    except (HTTPError, URLError, OSError) as e:
        print("下载 PDF 失败:", e, file=sys.stderr)
        return 1

    text = extract_text(BytesIO(data)) or ""
    print(text[:500].strip())
    print("\n... 总字符数:", len(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
