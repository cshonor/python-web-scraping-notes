"""第8章：pandas 去重示例（需安装 pandas）。"""
from __future__ import annotations

import sys

try:
    import pandas as pd
except ImportError:
    print("请安装: pip install pandas", file=sys.stderr)
    raise SystemExit(1)

df = pd.DataFrame(
    [
        {"url": "https://a", "title": "t1", "scraped_at": "2026-01-02"},
        {"url": "https://a", "title": "t2", "scraped_at": "2026-01-01"},
        {"url": "https://b", "title": "t3", "scraped_at": "2026-01-01"},
    ]
)
df["scraped_at"] = pd.to_datetime(df["scraped_at"])
out = df.sort_values("scraped_at").drop_duplicates("url", keep="last")
print(out)
