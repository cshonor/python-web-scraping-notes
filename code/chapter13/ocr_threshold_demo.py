"""第13章：阈值预处理 + Tesseract OCR（需系统安装 tesseract）。"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def clean_file(image: Image.Image, threshold: int) -> Image.Image:
    gray = image.convert("L")
    return gray.point(lambda x: 0 if x < threshold else 255)


def make_sample_png(path: Path) -> None:
    img = Image.new("RGB", (320, 80), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    draw.text((12, 20), "HELLO OCR 123", fill=(0, 0, 0), font=font)
    img.save(path)


def main() -> int:
    try:
        import pytesseract
    except ImportError:
        print("请安装: pip install pytesseract pillow", file=sys.stderr)
        return 1

    out_dir = Path(__file__).resolve().parent
    sample = out_dir / "_ocr_sample.png"
    make_sample_png(sample)

    try:
        img = Image.open(sample)
        cleaned = clean_file(img, 143)
        text = pytesseract.image_to_string(cleaned)
    except pytesseract.TesseractNotFoundError:
        print("未检测到 Tesseract 可执行文件。", file=sys.stderr)
        print("Windows: 安装后把安装目录加入 PATH。", file=sys.stderr)
        print("https://github.com/tesseract-ocr/tesseract", file=sys.stderr)
        return 1

    print("OCR 输出:\n", text.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
