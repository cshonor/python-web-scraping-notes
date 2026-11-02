# 第 9 章 自然语言处理：学习笔记

前面几章解决的是「把网页抓下来、洗干净」，本章解决的是「洗干净之后，怎么让程序读懂一点」。核心机制一句话：把文本当作**统计数据**来处理 —— 用频次分布找重点（简易摘要）、用状态转移建模语言（马尔可夫生成）、用词性标注给每个词贴上语法角色（NLTK），再在页面链接构成的**有向图**上用 **BFS** 求最短路径。第 8 章产出的干净 n-gram 与去停用词后的词流，正是本章这些统计模型的直接输入；清洗质量决定下游一切 NLP 效果的上限。

**本章目标**

1. 理解 NLP 在「抓取 → 清洗 → 理解」链路中的位置与输入形态
2. 掌握用**高频 n-gram 反查原句**做简易摘要的朴素思路
3. 理解**马尔可夫链**的转移概率假设与阶数（unigram / bigram）对生成质量的影响
4. 会用 **NLTK** 完成分词、去停用词、词干化与**词性标注（POS）**
5. 理解 **BFS** 在链接图上求最短路径的用法，以及与第 3 章随机游走的对照

---

## 1. 核心知识点与原理

### 1.1 NLP 在抓取链路中的位置

一条完整的「抓网页 → 得知识」流水线大致是：

```text
requests/Scrapy 抓取 → BeautifulSoup 解析 → 第 8 章清洗（去标点、去停用词、n-gram）
→ 第 9 章理解（统计摘要 / 马尔可夫生成 / 词性标注）→ 入库或可视化
```

| 阶段 | 输入 | 输出 | 对应章节 |
|---|---|---|---|
| 抓取 | URL | 原始 HTML | 第 1–5 章 |
| 清洗 | HTML 文本 | 干净词流、n-gram 计数 | 第 8 章 |
| 理解 | 干净词流 | 摘要、标注、生成文本、路径 | **本章** |

关键认识：本章所有方法都是**统计式**的 —— 不「理解」语义，只对词与词的共现、顺序、分布做计数与推断。因此输入里混进一个乱码、一批菜单词，输出就坏一片，这就是为什么要先过第 8 章的清洗。

### 1.2 概括数据：n-gram 简易摘要

一种朴素但可用的自动摘要思路，分两步走：

1. **统计**：在全文（已清洗）上找高频 **n-gram**（如 bigram），它们是「这篇文章在反复谈论什么」的线索。
2. **反查**：回到原文，检索**包含这些高频 n-gram 的句子**，作为候选摘要句；再配合启发式加权（句位靠前加分、首句加分、含数字/专名加分）排序取前几句。

| 步骤 | 依赖 | 易错点 |
|---|---|---|
| n-gram 统计 | 第 8 章的清洗结果 | 没去停用词时，高频 n-gram 全是 "of the"、"in a" 这类废话 |
| 句子反查 | 原文（未清洗版本） | 摘抄句必须来自原文，否则摘要里混进清洗残留（小写、无标点） |

这个方法与第 8 章的频次统计直接衔接：第 8 章已经能产出 n-gram 计数表，本章只是多问了一句「这些高频片段出现在哪些句子里」。

一个具体的执行样例（以英文维基词条为例）：

```text
原文（已按句切分，保留原貌）         →  清洗副本（小写、去标点、去停用词）
                                        ↓
                                 bigram 计数表（如 "new york" × 12）
                                        ↓
                                 在原文中逐句检索含 "new york" 的句子
                                        ↓
                                 按句位 / 长度 / 启发式加权排序，取前 N 句
```

注意「统计用清洗副本、摘录用原文」这条双轨制：统计阶段要归一化才能让 *New York* 与 *new york* 计入同一项，而最终展示给人看的句子必须保留原文的大小写与标点。混用两轨是新手最常见的 bug 来源。

### 1.3 马尔可夫模型与文本生成

**马尔可夫链**的核心假设是：「下一状态」的概率分布只依赖**当前状态**，与更早的历史无关。把「状态」取为「当前词」，就可以用转移计数回答「给定词 w，下一个词最可能是什么」：

```text
训练：统计语料中所有 (w_i, w_{i+1}) 共现次数 → 得到转移表 P(next | current)
生成：从一个起始词出发，按转移表反复采样 → 拼出一段新文本
```

一个迷你的转移表示意（语料只有两句：*I like NLP. I like Python.*）：

| 当前词 | 候选下一词（计数） | 归一化概率 |
|---|---|---|
| I | like (2) | 1.0 |
| like | NLP (1), Python (1) | 0.5 / 0.5 |
| NLP | . (1) | 1.0 |

从 *I* 出发采样，可能生成 *I like Python.*，也可能生成 *I like NLP.* —— 语料里从未出现的新组合就这样被「拼」出来了。真实语料上每个状态的候选更多，采样结果的多样性也随之上升。

| 阶数 | 状态定义 | 效果 | 风险 |
|---|---|---|---|
| unigram | 无上下文（词频采样） | 基本是随机词袋 | 几乎不可读 |
| bigram | 当前 1 个词 | 局部通顺、全局跑题 | 小语料上尚可 |
| trigram | 当前 2 个词 | 更像原文风格 | 容易**过拟合**：语料稍小就整段照抄原文 |

阶数越高，「看起来像人话」的程度越高，但本质仍是在复述训练语料的局部模式 —— 语料规模与清洗质量（还是第 8 章那套）直接决定生成上限。本章仓库没有独立的马尔可夫脚本，思路见「练习建议」第 1 条。

### 1.4 NLTK 工具链：分词、停用词、词干、词性标注

**NLTK**（Natural Language Toolkit）是 Python 里最经典的教学向 NLP 库，本章用到它的四个基本件：

| 组件 | 函数/类 | 作用 | 所需数据包 |
|---|---|---|---|
| 分词 | `word_tokenize` | 把句子切成词与标点 | `punkt` / `punkt_tab` |
| 停用词 | `corpus.stopwords` | 提供 179 个英文高频虚词表 | `stopwords` |
| 词干化 | `PorterStemmer` | 按规则砍词尾（running → run） | 无需数据（纯算法） |
| 词性标注 | `pos_tag` | 给每个词贴 Penn Treebank 标签 | `averaged_perceptron_tagger(_eng)` |

几个要点：

- **词性标注（POS）**：`pos_tag` 结合上下文推断每个词的语法角色，能消解一部分一词多类的歧义 —— 经典例句 *The dust was thick so he had to dust* 里，第一个 *dust* 是名词（NN），第二个 *dust* 是动词（VB）。
- **常用 Penn Treebank 标签速查**（`pos_tag` 默认输出这套标签）：

  | 标签 | 含义 | 例词 |
  |---|---|---|
  | DT | 限定词 | the, a |
  | NN / NNS | 名词（单 / 复） | dust, streets |
  | VB / VBD / VBG | 动词（原形 / 过去式 / 现在分词） | run, ran, running |
  | JJ / RB | 形容词 / 副词 | thick, beautifully |
  | PRP | 代词 | he, they |
  | TO / IN | 不定式标记 / 介词 | to, through |

  拿到不认识的标签，可以在交互式环境里运行 `nltk.help.upenn_tagset("NN")` 查官方释义。
- **词干化 ≠ 词形还原**：`PorterStemmer` 是规则砍尾，不理解词形变化 —— 实测 *ran* 原样保留（不会被还原成 *run*），*beautifully* 被砍成 *beauti*。要真正的词形还原得用 `WordNetLemmatizer`（另需 `wordnet` 数据包）。
- **数据包版本漂移**：NLTK 3.8.2 起把 `punkt` 的实现拆出 `punkt_tab`，把 `averaged_perceptron_tagger` 拆出按语言命名的 `averaged_perceptron_tagger_eng`。老教程只下载旧包名，在新版上可能仍报 `LookupError` —— 对策是新旧包名都下（`nltk_pos_demo.py` 的 `ensure_nltk_data()` 就是这么做的），或按报错提示补齐。
- **中文不适用**：NLTK 主要为英文设计，中文分词请换 **jieba**、**pkuseg** 等专用工具。

### 1.5 广度优先搜索（BFS）与链接图最短路径

把页面看成节点、链接看成有向边，维基就是一个巨大的**有向图**。「从词条 A 到词条 B 最少点几次链接」就是图上的**最短路径**问题，而 BFS 是无权图上求最短路径的标准解法：

```text
队列 ← 起点；visited ← {起点}
while 队列非空:
    node ← 队首出队
    if node == 终点: 返回路径长度
    for node 的每条出链（且未访问）: 标记 visited，入队
```

| 特性 | 说明 |
|---|---|
| 正确性 | 按层扩展，第一次到达终点时经过的边数必然最少 |
| 去重 | `visited` 集合（第 3 章用过同一招）防环路死循环 |
| 对照第 3 章 | 第 3 章是**递归随机游走**（无目标、漫游），BFS 是**有目标的层序搜索** |
| 对照 DFS | DFS 一路扎到底，找到的路径不保证最短；BFS 用队列换空间，换来最短性保证 |

「六度分隔」类实验（任意两个维基词条之间平均几步可达）就是在这张图上跑 BFS 统计出来的。实战抓取时要控制规模与频率：BFS 每层节点数爆炸式增长（按平均出度 d 估算，第 k 层约有 d^k 个新节点），务必配合请求上限与礼貌延时（第 2、5 章的原则在这里依然适用）。教学演示建议固定起点、限制最大深度在两到三层以内，并把每页抓到的链接数截断到前几十条。

---

## 2. 代码示例：NLTK 词性标注

两个脚本均已在本机实测通过（环境：NLTK 3.10.4，实测日期 2026-11-02），下列输出为真实运行结果。首次运行前安装依赖：

```bash
cd chapter-09
pip install -r requirements.txt   # nltk>=3.8.0
```

### 2.1 `nltk_pos_demo.py`：一句话看清一词多类

词性标注的最小演示。脚本先用 `ensure_nltk_data()` 把新旧两套数据包名（`punkt` / `punkt_tab`、`averaged_perceptron_tagger` / `averaged_perceptron_tagger_eng`）逐个静默下载，下载失败也不中断；然后对 *The dust was thick so he had to dust* 做 `word_tokenize` 分词，再交给 `pos_tag` 标注。这句的看点是 *dust* 出现两次：句首作名词「灰尘」，句尾作动词「掸灰」，标注器靠上下文把两者区分开。

```python
def ensure_nltk_data() -> None:
    import nltk
    for pkg in ("punkt", "punkt_tab", "averaged_perceptron_tagger", "averaged_perceptron_tagger_eng"):
        try:
            nltk.download(pkg, quiet=True)
        except Exception:
            pass

text = word_tokenize("The dust was thick so he had to dust")
tagged_text = pos_tag(text)
print(tagged_text)
```

```bash
cd chapter-09
python nltk_pos_demo.py
```

**已实测**（2026-11-02），输出：

```text
[('The', 'DT'), ('dust', 'NN'), ('was', 'VBD'), ('thick', 'RB'), ('so', 'RB'), ('he', 'PRP'), ('had', 'VBD'), ('to', 'TO'), ('dust', 'VB')]
```

两个 *dust* 分别标为 **NN（名词）** 与 **VB（动词）**，歧义消解成功。顺带一提：*thick* 被标成了 RB（副词）而非常理的 JJ（形容词）—— 统计标注器不是完美的，小句子上偶尔会犯这种错，工程上要对标注结果保留一分怀疑。常用标签速查：DT 限定词、NN 名词、VB/VBD 动词（原形/过去式）、PRP 代词、TO 不定式标记（完整对照表见 1.4 节）。

脚本里还有两个值得抄的工程细节：`ensure_nltk_data()` 对四个包名逐个 `try / except` 静默下载，新旧 NLTK 版本都能自愈；缺库时打印提示到 stderr 并返回退出码 1，与缺数据时优雅退出的分支（返回 0）区分开 —— 写命令行工具时这种「失败原因可区分」的退出码设计很省心。

### 2.2 `nltk_basics.py`：分词 → 去停用词 → 词干化

NLTK 基础三件套的组合演示。脚本先用 `nltk.data.find("tokenizers/punkt")` 探测数据包是否存在，缺失则打印提示并优雅退出（返回 0），不会甩出 traceback；数据齐备后，把 *Running runners ran beautifully through the streets.* 转小写、分词，再用 `stopwords.words("english")` 滤掉虚词（本句中 *through*、*the* 被滤除），最后对剩下的**纯字母** token（`w.isalpha()` 把标点也挡在外面）逐个做 Porter 词干化并打印列表。

```python
text = "Running runners ran beautifully through the streets."
tokens = word_tokenize(text.lower())
stops = set(stopwords.words("english"))
stemmer = PorterStemmer()
out = [stemmer.stem(w) for w in tokens if w.isalpha() and w not in stops]
print(out)
```

```bash
cd chapter-09
python -c "import nltk; nltk.download('stopwords')"   # 首次需要
python nltk_basics.py
```

一行行看数据在管道里的变化（左侧为每个处理阶段的产物）：

| 阶段 | 数据形态 |
|---|---|
| 原句 | `Running runners ran beautifully through the streets.` |
| `lower()` + `word_tokenize` | `['running', 'runners', 'ran', 'beautifully', 'through', 'the', 'streets', '.']` |
| `isalpha()` 过滤 | 去掉 `'.'` |
| 停用词过滤 | 去掉 `'through'`、`'the'` |
| `PorterStemmer.stem` | `['run', 'runner', 'ran', 'beauti', 'street']` |

**已实测**（2026-11-02），输出：

```text
['run', 'runner', 'ran', 'beauti', 'street']
```

这份输出恰好暴露了词干化的边界：*Running* → *run*、*streets* → *street* 符合预期；但 *runners* 只砍成 *runner*（不会去重到 *run*），*ran* 原样保留（不规则变化认不出），*beautifully* 被砍成不存在的 *beauti*。想要「都归一到词典原形」，得换词形还原器 —— 这正是 1.4 节说的「词干化 ≠ 词形还原」。

---

## 3. 学习贴士

- **语料是马尔可夫生成的天花板**。训练段越长、清洗越干净，生成越像样；几百词的小语料用 trigram 只会整段复读原文，不如退回 bigram。
- **把 nltk.download 当成安装的一部分**。NLTK 的库代码和数据包是分开分发的，`pip install nltk` 之后没有数据包，`word_tokenize` / `pos_tag` 一调就 `LookupError`。脚本化的做法参考 `nltk_pos_demo.py`：把所需包名列成清单逐个静默下载。
- **数据包名会随版本漂移**。NLTK 3.8.2+ 引入 `punkt_tab`、`averaged_perceptron_tagger_eng` 等新包名；报 `LookupError` 时直接按报错信息里建议的包名下载最保险，别死记教程里的旧名字。
- **代理环境下 NLTK 3.10 可能拒下载**。新版引入了 SSRF 防护，检测到代理 egress 时会拒绝拉取语料；确认代理可信后需显式 opt-in（如设 `NLTK_ALLOW_PROXIED_URLOPEN=1`）才能下载。本次实测正是用该变量跑通的。
- **中文任务换工具链**。NLTK 的分词与停用词表为英文设计，中文文本直接喂进去会得到按空格切的碎块；中文分词与词性标注看 jieba、pkuseg、LAC 等。

---

## 4. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-09/nltk_pos_demo.py` | 词性标注最小演示：自带数据包兜底下载，区分 *dust* 名/动两用（已实测） |
| `chapter-09/nltk_basics.py` | 分词 + 英文停用词过滤 + Porter 词干化（已实测，输出 `['run', 'runner', 'ran', 'beauti', 'street']`） |
| `chapter-09/requirements.txt` | 本章依赖 `nltk>=3.8.0`，注释里写明首次运行需 `nltk.download` 语料 |

对照第 8 章看：第 8 章手工实现了去停用词与 n-gram 统计，本章的 `nltk_basics.py` 用现成库做同一件事 —— 自写一遍再用库一遍，两边输出对照着看，对「库里到底做了什么」就有手感了。BFS 部分可对照第 3 章的递归随机游走脚本：一个无目标漫游、一个有目标层序搜索，图的两种基本玩法。

---

## 练习建议

1. 对同一语料分别用 **unigram / bigram** 马尔可夫链生成 50 词，比较可读性；再把语料砍半重跑 bigram，观察过拟合（整句照抄原文）现象。
2. 用 **FreqDist** 统计一段英文文本的前 20 高频词，人工挑 5 个 NLTK 停用词表没覆盖的「领域虚词」加入自定义表，重跑 `nltk_basics.py` 风格的过滤流程。
3. 修改 `nltk_pos_demo.py`：换一句含一词多类的句子（如 *They can fish.* 的 *can*），先预测每个词的标签再运行验证，标错了想想统计模型为什么错。
4. 把 `nltk_basics.py` 的 `PorterStemmer` 换成 `WordNetLemmatizer`（需另下 `wordnet` 数据包），对比 *ran*、*runners* 两个词在两种方案下的输出差异。
5. 在维基链接图上（小规模，比如固定起点只展开两层）实现 BFS 求两页最短路径，注意 `visited` 去重、请求上限与礼貌延时。
