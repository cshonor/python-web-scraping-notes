"""示例管线：透传 + 可选解析 last_updated 为 ISO 时间字符串。"""
from __future__ import annotations

import re
from datetime import datetime


class WikiSpiderPipeline:
    """默认透传；可在此做去重、丢弃空标题等。"""

    def process_item(self, item, spider):
        return item


class LastUpdatedParsePipeline:
    """
    将英文维基页脚常见格式解析为 UTC 近似 ISO 字符串。
    解析失败时跳过，不抛异常（不同语言皮肤格式差异大）。
    """

    _prefix = re.compile(
        r"^\s*This page was last edited on\s+",
        re.IGNORECASE,
    )

    # 例: "13 May 2026, at 13:35" 或历史带括号 "… 13:35 (UTC)."
    _footer_re = re.compile(
        r"^(\d{1,2})\s+([A-Za-z]+\s+\d{4}),\s+at\s+(\d{1,2}):(\d{2})(?:\s*\(?UTC\)?)?\.?\s*$",
    )

    def process_item(self, item, spider):
        raw = item.get("last_updated")
        if not raw:
            return item
        s = self._prefix.sub("", str(raw)).strip()
        m = self._footer_re.match(s)
        if not m:
            return item
        day, rest, hh, mm = m.groups()
        padded = f"{int(day):02d} {rest}, at {int(hh):02d}:{int(mm):02d}."
        try:
            dt = datetime.strptime(padded, "%d %B %Y, at %H:%M.")
            item["last_updated_iso"] = dt.isoformat() + "Z"
        except ValueError:
            pass
        return item
