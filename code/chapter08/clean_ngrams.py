"""第8章：清洗 + 2-gram Counter（书中思路，正则已勘误）。"""
from __future__ import annotations

import re
import string
from collections import Counter


def clean_input(content: str) -> list[str]:
    """去角标式 [1]、换行，再分句分词（英文演示向）。"""
    content = re.sub(r"\[\d+\]", " ", content)
    content = content.replace("\n", " ")
    content = content.upper()
    # 与书中一致：剔除非 ASCII（会删除中文；多语言请改用 normalize/casefold）
    content = content.encode("utf-8", errors="ignore").decode("ascii", errors="ignore")
    sentences = content.split(". ")
    out: list[str] = []
    for sentence in sentences:
        for word in sentence.split(" "):
            w = word.strip(string.punctuation + string.whitespace)
            if w:
                out.append(w)
    return out


def ngrams(words: list[str], n: int):
    return zip(*[words[i:] for i in range(n)])


def main() -> None:
    sample = """
    Monty Python (also collectively known as the Pythons)[2][3]
    were a British comedy troupe.
    They created the sketch show.
    """
    words = clean_input(sample)
    pairs = list(ngrams(words, 2))
    counts = Counter(" ".join(pair) for pair in pairs)
    print("词表长度:", len(words))
    print("前若干 2-gram:", counts.most_common(10))


if __name__ == "__main__":
    main()
