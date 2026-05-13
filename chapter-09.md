# 第 9 章 自然语言处理：学习笔记

本章介绍用统计与简单模型理解文本的进阶思路：摘要线索、**马尔可夫**式生成、**NLTK** 基础工具，以及图上**最短路径**与维基链接分析的联系。

---

## 1. 核心知识点与原理

### 1.1 概括数据（简易摘要思路）

一种朴素思路：先找高频 **n-gram**，再在原文中检索**包含这些 n-gram 的句子**作为候选摘要句（再配合位置、首句加权等启发式）。与第 8 章的频次统计直接衔接。

### 1.2 马尔可夫模型

**马尔可夫链**假设「下一状态」分布主要依赖**当前状态**（此处常为当前词）。用转移计数估计「给定词 w，下一个词是什么」可生成**风格近似**的模拟文本；阶数提高（bigram/trigram）会更像原文，但也更易过拟合小语料。

### 1.3 自然语言工具包（NLTK）

- **统计与分布**：词型/词例计数、频率分布、搭配等。
- **词性标注（POS）**：如 **`pos_tag`**，结合上下文猜测名词/动词等，消解部分歧义（例：*dust* 作名词与动词）。
- **分词**：`word_tokenize` 等；首次使用需下载 **`punkt`**、**`averaged_perceptron_tagger`**（或 `taggers/maxent_treebank_pos_tagger/english.pickle` 等，随 NLTK 版本而异）。

### 1.4 广度优先搜索（BFS）

在**有向图**（如页面链接图）上，BFS 常用于求**最短路径**（最少点击/最少边）。维基「六度分隔」类实验可用 BFS + 去重队列实现（与第 3 章递归随机游走对照）。

---

## 2. 代码示例：NLTK 词性标注

可运行脚本：`code/chapter09/nltk_pos_demo.py`

```python
from nltk import pos_tag, word_tokenize

text = word_tokenize("The dust was thick so he had to dust")
tagged_text = pos_tag(text)
print(tagged_text)
```

首次运行若缺数据：

```python
import nltk
nltk.download("punkt_tab")  # NLTK 3.8.2+ 常见
nltk.download("averaged_perceptron_tagger_eng")
```

（若报错，按提示改为 `punkt` / `averaged_perceptron_tagger` 等传统包名。）

---

## 3. 学习贴士

- **语料规模**：马尔可夫生成质量强依赖训练段长度与清洗质量。  
- **中文**：NLTK 主要为英文设计；中文分词可看 **jieba**、**pkuseg** 等。

---

## 4. 与本仓库其他示例

`code/chapter09/nltk_basics.py`：分词 + 停用词 + 词干（需 NLTK 数据）。

## 练习建议

1. 对同一句话分别用 **unigram / bigram** 马尔可夫链生成 50 词，比较可读性。  
2. 用 **FreqDist** 统计某文本前 20 高频词，人工挑 5 个停用词加入自定义表。  
3. 在维基链接图上（小规模）实现 BFS 求两页最短路径（注意礼仪与请求上限）。
