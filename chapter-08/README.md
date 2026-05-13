# 第 8 章 数据清洗：学习笔记

本章讨论如何处理 Web 上的「脏数据」（标点噪声、大小写不一致、断行与引用标记等），通过**预防型清洗**与**落库后标准化**，让下游分析可靠。

---

## 1. 核心知识点与原理

### 1.1 n-gram 模型

**n-gram** 指文本中 **n 个连续词**（或字符）组成的片段。2-gram（bigram）常用于语言模型、去重近似、简单特征与摘要候选。与 **`collections.Counter`** 结合可统计高频片段，用于发现模板句、固定搭配或噪声模式。

### 1.2 数据标准化

目标是在业务含义不变的前提下，**统一表示形式**，例如：

- 电话、日期、货币格式归一；
- 英文常做 **case folding**（如统一大写或小写）以减少「同一词」的多种写法（注意：专有名词过度大写化会损失信息，可按字段策略选择）。

### 1.3 常用工具

- **`collections.Counter`**：统计词或 n-gram 频次，接口简单。
- **正则 `re`**：去引用角标、多余空白、异常分隔符。
- **OpenRefine**：开源桌面工具，用 **GREL** 等在表格上做筛选、聚类、批量变换，适合**人机结合**的大规模清洗（与纯代码流水线互补）。
- **pandas**（扩展）：去重、缺失值、类型转换，见 `chapter-08/pandas_dedupe.py`。

---

## 2. 代码示例：获取干净的词表与 2-gram

书中思路：先 **`cleanInput`** 得到词列表，再用 **`Counter`** 统计 **2-gram**。

**易错点勘误**：原稿正则 `'\n|[[\d+\]]'` 括号易写错；常见需求是去掉类似 **`[12]`** 的角标与换行。下面用更清晰的写法；**`encode('utf-8').decode('ascii','ignore')`** 会剔除所有非 ASCII 字符，**会伤中文**，多语言场景请改用 **`casefold()` / `unicodedata`** 等更温和手段。

可运行脚本：`chapter-08/clean_ngrams.py`

```python
import re
import string
from collections import Counter

def cleanInput(content):
    content = re.sub(r"\[\d+\]", " ", content)
    content = content.replace("\n", " ")
    content = content.upper()
    content = content.encode("utf-8", errors="ignore").decode("ascii", errors="ignore")
    sentences = content.split(". ")
    out = []
    for sentence in sentences:
        for word in sentence.split(" "):
            w = word.strip(string.punctuation + string.whitespace)
            if w:
                out.append(w)
    return out

def ngrams(words, n):
    return zip(*[words[i:] for i in range(n)])

words = cleanInput("Hello world. World hello.[1]")
bigrams = list(ngrams(words, 2))
print(Counter(" ".join(pair) for pair in bigrams))
```

---

## 3. 学习贴士

- **清洗可逆性**：尽量保留原始字段副本，清洗结果写入新列，便于回溯。
- **与 NLP 衔接**：第 9 章的分词、词干化之前，先完成本章的**噪声裁剪**，避免垃圾进垃圾出。

---

## 4. 与本仓库其他示例

- `chapter-08/clean_text.py`：空白与 Unicode 规范化小例。

## 练习建议

1. 把「去角标」规则改成同时支持 `[12]` 与 `(2024)` 两种引用样式。  
2. 用 **pandas** 对一列文本做 `str.lower().str.strip()` 后再 `value_counts()`。  
3. 在 OpenRefine 中导入一份 CSV，试用 **facet + cluster** 合并拼写变体（记录操作步骤即可）。
