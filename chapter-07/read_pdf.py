"""第7章：从 PDF 抽取文本（需安装 pypdf）。"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    try:
        from pypdf import PdfReader
    except ImportError:
        print("请安装: pip install pypdf", file=sys.stderr)
        return 1

    pdf_path = Path(__file__).resolve().parent / "sample.pdf"
    if not pdf_path.is_file():
        print("请将任意 small.pdf 放到:", pdf_path, file=sys.stderr)
        print("或修改脚本中的 pdf_path。", file=sys.stderr)
        return 0

    reader = PdfReader(str(pdf_path))
    text = ""
    for page in reader.pages[:3]:
        text += page.extract_text() or ""
    print("前3页文本长度:", len(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
