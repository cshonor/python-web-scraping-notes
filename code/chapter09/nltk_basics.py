"""第9章：NLTK 基础（需安装 nltk 并下载数据）。"""
from __future__ import annotations

import sys


def main() -> int:
    try:
        import nltk
        from nltk.corpus import stopwords
        from nltk.stem import PorterStemmer
        from nltk.tokenize import word_tokenize
    except ImportError:
        print("请安装: pip install nltk", file=sys.stderr)
        return 1

    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        print('首次运行请执行: nltk.download("punkt") 与 nltk.download("stopwords")')
        return 0

    text = "Running runners ran beautifully through the streets."
    tokens = word_tokenize(text.lower())
    stops = set(stopwords.words("english"))
    stemmer = PorterStemmer()
    out = [stemmer.stem(w) for w in tokens if w.isalpha() and w not in stops]
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
