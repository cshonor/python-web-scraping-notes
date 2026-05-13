"""第8章：文本清洗小函数。"""
import re
import unicodedata


def squash_spaces(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


raw = "  全角ＡＢＣ　\n\tfoo   bar  "
print(squash_spaces(raw))
