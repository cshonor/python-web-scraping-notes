"""第13章：Pillow 生成并处理图像。"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

out = Path(__file__).resolve().parent / "demo_gray.png"
img = Image.new("RGB", (120, 40), color=(200, 220, 255))
gray = img.convert("L")
gray.save(out)
print("saved", out)
