"""第9章：NLTK 词性标注示例（需 nltk 与数据包）。"""
from __future__ import annotations

import sys


def ensure_nltk_data() -> None:
    import nltk

    for pkg in ("punkt", "punkt_tab", "averaged_perceptron_tagger", "averaged_perceptron_tagger_eng"):
        try:
            nltk.download(pkg, quiet=True)
        except Exception:
            pass


def main() -> int:
    try:
        import nltk
        from nltk import pos_tag, word_tokenize
    except ImportError:
        print("请安装: pip install nltk", file=sys.stderr)
        return 1

    ensure_nltk_data()

    text = word_tokenize("The dust was thick so he had to dust")
    tagged_text = pos_tag(text)
    print(tagged_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
