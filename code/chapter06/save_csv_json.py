"""第6章：写入 CSV 与 JSON Lines。"""
from __future__ import annotations

import csv
import json
from pathlib import Path

rows = [
    {"url": "https://example.com", "title": "Example"},
    {"url": "https://example.org", "title": "Example Domain .org"},
]

out_dir = Path(__file__).resolve().parent
csv_path = out_dir / "sample_output.csv"
jsonl_path = out_dir / "sample_output.jsonl"

with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["url", "title"])
    w.writeheader()
    w.writerows(rows)

with jsonl_path.open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print("wrote", csv_path, jsonl_path)
