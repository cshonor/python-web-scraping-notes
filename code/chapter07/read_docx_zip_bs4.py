"""第7章：.docx = ZIP + word/document.xml + BeautifulSoup（xml）。"""
from __future__ import annotations

import sys
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile

from bs4 import BeautifulSoup

URL = "https://pythonscraping.com/pages/AWordDocument.docx"


def main() -> int:
    req = Request(URL, headers={"User-Agent": "Chapter07DocxDemo/1.0 (educational)"})
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except (HTTPError, URLError, OSError) as e:
        print("下载失败:", e, file=sys.stderr)
        print("可将任意 .docx 放到与本脚本同目录的 sample.docx 后重试。", file=sys.stderr)
        from pathlib import Path

        p = Path(__file__).resolve().parent / "sample.docx"
        if not p.is_file():
            return 1
        raw = p.read_bytes()

    zf = ZipFile(BytesIO(raw))
    try:
        xml_content = zf.read("word/document.xml")
    except KeyError:
        print("ZIP 中缺少 word/document.xml", file=sys.stderr)
        return 1
    finally:
        zf.close()

    word_obj = BeautifulSoup(xml_content.decode("utf-8", errors="replace"), "xml")
    for text_elem in word_obj.find_all("w:t"):
        t = text_elem.text
        if t:
            print(t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
