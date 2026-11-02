# 第 13 章 图像识别与文字处理：学习笔记

前面章节抓下来的不只有 HTML：扫描件、截图、验证码图片里的文字，用正则和选择器是无从下手的。本章解决的就是「怎么从图像里把文字恢复出来」这个问题。核心机制一句话：用 **Pillow** 把图像预处理成高对比度的干净灰度/黑白图，再交给系统级的 **Tesseract** OCR 引擎（经 `pytesseract` 桥接）识别成文本。典型**合规**用途包括：扫描件/发票/档案数字化、无障碍辅助、桌面自动化中对**自有**截图的识别等；而拿这套技术去绕第三方网站的验证码，则是本章明确划出的红线（见第 3 节）。

**本章目标**

1. 理清 **Pillow / Tesseract / pytesseract** 三者的分工与安装关系
2. 掌握灰度化、**点运算阈值**、缩放等图像预处理手段及其对 OCR 的影响
3. 理解「扫描阈值参数 + 按识别结果挑较优值」的自动调整思路及其过拟合风险
4. 知晓 **Tesseract 训练**的适用场景与成本，明确绕过第三方验证码的**法律与服务条款风险**
5. 会运行本章两个脚本：`pillow_resize.py` 与 `ocr_threshold_demo.py`，并能读懂降级提示
6. 建立「预处理 → 提取 → 清洗 → 落地」的 OCR 流水线整体观，知道与后续章节的衔接点

---

## 1. 核心工具库

### 1.1 三者的分工

OCR 这条链路涉及三个名字相近但层次完全不同的组件，初学者最容易混淆的就是「装了 `pytesseract` 为什么还是跑不起来」——因为它只是桥，不是引擎。

| 组件 | 层次 | 职责 | 安装方式 |
|---|---|---|---|
| **Pillow** | Python 图像库 | 打开图像、灰度化、裁剪、缩放、对比度与**点运算阈值**等预处理 | `pip install pillow` |
| **Tesseract** | 系统级 OCR 引擎 | 真正执行字符识别的开源引擎，独立于 Python 存在 | Windows 安装包 / `brew install tesseract` / `apt install tesseract-ocr`，并确保可执行文件加入 `PATH` |
| **pytesseract** | Python 包装器 | 桥接到 Tesseract CLI：把图像传给引擎、收回文本与元数据 | `pip install pytesseract`（**必须先装好上面的 Tesseract**） |

本章 `requirements.txt` 里只有 `Pillow>=10.0.0` 与 `pytesseract>=0.3.10` 两行，文件头部的注释特意说明：`pytesseract` 只是 wrapper，必须另装系统级 Tesseract；脚本检测不到时会打印安装提示而不是直接抛栈。

安装完成后可以分两层验证——先验证系统引擎，再验证 Python 桥：

```bash
tesseract --version          # 系统引擎：输出版本号即 OK
tesseract --list-langs       # 查看已安装的语言包（默认通常只有 eng）
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

第三行能打印版本号，说明三层（引擎、`PATH`、wrapper）全部打通；若第二行报「command not found」而引擎确实装了，就是安装目录没进 `PATH` 的问题，Windows 上尤其常见。需要识别中文还要另行安装 `chi_sim` 等语言包，并在调用时传 `lang="chi_sim"`。

### 1.2 可选扩展：NumPy

- **NumPy（可选）**：把图像转为数组后可做批量像素级运算（比逐像素 Python 循环快几个数量级），也方便与 OpenCV 生态衔接。
- 另一个用途是对 OCR 输出的置信度等元数据做数值处理，比如批量过滤低置信片段、统计一张图的平均置信度。
- 本章脚本没有用到 NumPy，纯 Pillow 已足够演示核心机制；当预处理逻辑复杂到「逐像素 lambda 写不下」时，再引入它不迟。

### 1.3 语言包与识别配置

Tesseract 按语言包工作，默认可执行文件通常只带英文。两个实用要点：

- **多语言**：识别中文需另装 `chi_sim` 语言包，调用时 `pytesseract.image_to_string(img, lang="chi_sim")`，多语言混排可传 `lang="eng+chi_sim"`；
- **PSM（页面分割模式）**：通过 `config="--psm 7"` 之类的参数告诉引擎版面形态（单行、单列、整页等），版式假设越贴近真实版面，识别越稳。这条在练习建议里会动手验证。

### 1.4 典型调用链

```text
PIL.Image.open(...) → convert("L") → point(阈值函数) → pytesseract.image_to_string(...) → str
        └──────────── Pillow 负责 ────────────┘   └──── pytesseract → Tesseract ────┘
```

---

## 2. 图像预处理与自动调整

### 2.1 为什么要预处理

Tesseract 对「白底黑字、笔画清晰」的图像识别率最高，而现实中的扫描件和截图往往带浅底噪点、灰底、抗锯齿毛边。预处理的目标就是把图像往「理想输入」方向推：去色、增强对比、消除浅噪声。一个朴素的经验是：**你在 OCR 之前每多花一分力气清洗图像，识别率的上限就抬高一分**——引擎本身并不会因为输入脏而变得更聪明，它只会猜得更离谱。

### 2.2 灰度化：`convert("L")`

把 RGB 三通道按亮度合成单通道灰度图，是几乎所有 OCR 预处理的第一步：

- 丢掉颜色信息后，后续运算只需处理一个通道，逻辑和性能都更简单；
- 对「黑字白底但扫描成彩色」的文档，灰度化本身不改变可读性，却为阈值化铺平道路。

### 2.3 阈值化：`point()` 点运算

阈值化把灰度图切成纯黑白二值图，核心是一行点运算：

```python
gray.point(lambda x: 0 if x < threshold else 255)
```

`point()` 对**每个像素独立**应用映射函数：小于阈值的像素压成纯黑（0），否则抬成纯白（255）。其效果：

- 浅灰噪点（灰度值通常较高）被抬成白色，背景被「擦干净」；
- 笔画本体（灰度值低）被压成纯黑，边缘变得更锐利；
- 阈值选得过低，浅笔画会丢；选得过高，噪点被当成笔画。没有普适值，必须按图调。

### 2.4 缩放、噪声处理与其他手段

- **缩放**：过小的字符放大后笔画变粗、可识别性上升，常用 `Image.resize()` 配合 `LANCZOS` 等重采样滤波器；反之过大的图可先缩小加速识别。注意本章 `pillow_resize.py` 文件名虽带 resize，实际只演示了生成与灰度化，并未调用 `resize()`。
- **噪声处理**：扫描件上的椒盐噪点、浅底纹是最常见的干扰。轻量做法是靠阈值化「顺带」抹掉浅色噪点；更系统的做法是邻域滤波——`ImageFilter.MedianFilter` 中值滤波对孤立噪点很有效，且比均值滤波更能保住笔画边缘。需要腐蚀/膨胀等形态学操作时，再引入 OpenCV 更顺手。
- **对比度/裁剪**：`ImageEnhance.Contrast` 可整体拉开明暗差距；`crop()` 把无关边框裁掉，减少引擎在噪声区域浪费的猜测。

几种常见手段的取舍一览：

| 手段 | 主要解决的问题 | 代价/风险 |
|---|---|---|
| 灰度化 `convert("L")` | 彩色干扰、通道冗余 | 基本无损，几乎总是第一步 |
| 阈值化 `point()` | 浅底噪点、灰底、抗锯齿毛边 | 阈值不当会丢笔画或留噪点 |
| 缩放 `resize()` | 字符过小/过大 | 放大模糊小图救不回来，反而引入伪影 |
| 中值滤波 | 孤立椒盐噪点 | 核开太大会糊掉细笔画 |
| 对比度增强 | 整体发灰、明暗拉不开 | 对已接近纯黑白的图收益为零 |

### 2.5 参数搜索（书中思路）

阈值不是拍脑袋定的。书中给出的思路是：在合理范围内（比如 120–180）**扫描候选阈值**，对每组参数跑一遍 OCR，用 **Tesseract 置信度或识别出的字符数**这类启发式指标挑一组较优参数。骨架大致是：

```python
best = None
for threshold in range(120, 181, 10):
    cleaned = clean_file(image, threshold)
    text = pytesseract.image_to_string(cleaned)
    score = len(text.strip())          # 启发式：识别出的字符数
    if best is None or score > best[1]:
        best = (threshold, score)
```

两条注意事项：

- **过拟合单张图**：在一张图上搜出来的最优阈值，换一批图可能完全不是最优；批量任务应分数据集验证。
- **启发式不等于正确**：字符数多不代表识别得对（噪点也会被识别成「字符」），置信度也只是引擎的自评，最终仍要抽样人工核对。更可靠的打分方式是接 `image_to_data` 返回的逐词置信度取均值，但仍只是自评。

---

## 3. 验证码（CAPTCHA）与训练（合规边界）

### 3.1 Tesseract 训练：可行但昂贵

对**固定字体、固定版式**的小字符集（比如自家系统生成的某种票据编号），可以通过准备训练数据、微调 Tesseract 语言模型来提升识别率。大致流程：收集并标注样本图 → 按版式生成或扩充训练集 → 用官方训练工具产出 `.traineddata` → 通过 `lang` 参数加载评估。但要认清：

- **工程成本高**：标注样本、生成训练集、调参评估，每一步都是实打实的工作量；
- **适用面窄**：训练成果只对那一类版式有效，换字体换背景就失效；
- **误用风险大**：这项能力最常见的「应用场景」恰恰是绕过验证码——见下。

### 3.2 为什么不该绕过第三方验证码

对**第三方网站**登录/注册等环节的验证码做「自动识别 + 多次尝试直到成功」，问题不只是技术层面：

| 维度 | 风险 |
|---|---|
| 服务条款 | 验证码的存在本身就是站点明确表达「拒绝自动化访问」的信号，绕过几乎必然违反 ToS |
| 法律 | 在多数法域，绕过访问控制措施可能触犯计算机犯罪或反不正当竞争相关法规 |
| 对抗成本 | 验证码方案持续升级（扭曲、语义题、行为验证），识别方陷入无止境的军备竞赛 |
| 工程收益 | 识别率再高也到不了 100%，失败重试会进一步放大请求特征，被封只是时间问题 |

教学与实验请在**自建靶场**、**授权渗透测试**或**公开 OCR 数据集**上进行——识别自己生成的图，识别率随便刷，谁也不受伤害。

### 3.3 更稳妥的替代路径

| 路径 | 适用场景 | 说明 |
|---|---|---|
| **官方 API** | 目标站提供数据接口 | 很多站点（包括有验证码的站点）本身就有授权通道，又快又合法，应作为首选排查项 |
| **人工打码平台** | 确有合规业务刚需（如无障碍场景） | 选有合同与合规流程的服务商，留存授权链证据 |
| **产品侧反思** | 自家产品被爬虫困扰 | 优先考虑风控策略与人机验证的合理设计，而不是指望验证码挡住一切 |
| **自建靶场练习** | 学习与研究 | 自己生成验证码图、自己识别，识别率随便刷，零合规风险 |

一句话总结：验证码技术本身中立于善恶，**识别谁生成的图**决定了这件事的性质。

---

## 4. 代码示例：阈值 + OCR

前置依赖：`pip install pillow pytesseract`（或 `pip install -r requirements.txt`），并安装系统 **Tesseract** 且加入 `PATH`。本章两个脚本均在本地用仓库指定 Python 实际运行，结果如实记录如下。

### 4.1 `pillow_resize.py`：纯 Pillow 生成/处理图像的最小示例

零网络、零外部依赖的最小脚本：新建一张 120x40 的 RGB 纯色图（颜色 `(200, 220, 255)`，浅蓝），用 `convert("L")` 转成灰度图后保存为脚本同目录的 `demo_gray.png`，最后打印保存路径。文件路径用 `Path(__file__).resolve().parent` 定位，从任何工作目录运行产物都落在脚本旁边。虽然文件名叫 resize，但脚本并未调用 `resize()`，它演示的是「生成 → 灰度化 → 落盘」这条 Pillow 基本功链路，也正是 4.2 中 OCR 预处理的前半段。顺带一提：浅蓝 `(200, 220, 255)` 转灰度后是较亮的灰，保存出的 PNG 只有一百多字节——纯色图高度可压缩，文件极小是正常现象，不是保存失败。

```python
out = Path(__file__).resolve().parent / "demo_gray.png"
img = Image.new("RGB", (120, 40), color=(200, 220, 255))
gray = img.convert("L")
gray.save(out)
print("saved", out)
```

```bash
cd chapter-13
python pillow_resize.py
```

**已实测**：输出 `saved .../chapter-13/demo_gray.png`，生成 131 字节的灰度 PNG，退出码 0。

### 4.2 `ocr_threshold_demo.py`：阈值预处理 + Tesseract OCR

完整演示「造图 → 清洗 → 识别」全流程，并带两条优雅的降级路径。脚本分三部分：

- `make_sample_png(path)`：用 Pillow 造一张 320x80 白底测试图，尝试加载 `arial.ttf` 36 号字体（`OSError` 时回退 `ImageFont.load_default()`），在 `(12, 20)` 处写上黑字 `HELLO OCR 123` 后保存；
- `clean_file(image, threshold)`：先 `convert("L")` 灰度化，再 `point()` 阈值化——注意它接收的是 `Image` 对象而非文件路径；
- `main()`：`import pytesseract` 失败（未安装）时打印 `请安装: pip install pytesseract pillow` 并返回 1；识别过程中捕获 `pytesseract.TesseractNotFoundError`（包装器在、系统引擎不在）时打印安装指引并返回 1；都正常则打印 OCR 结果。

```python
def clean_file(image: Image.Image, threshold: int) -> Image.Image:
    gray = image.convert("L")
    return gray.point(lambda x: 0 if x < threshold else 255)

img = Image.open(sample)
cleaned = clean_file(img, 143)
text = pytesseract.image_to_string(cleaned)
```

```bash
cd chapter-13
pip install -r requirements.txt   # 另需系统级 Tesseract
python ocr_threshold_demo.py
```

脚本的健壮性设计值得单独看——两条降级分支对应两种「缺东西」的情况：

| 缺失项 | 触发点 | 脚本行为 |
|---|---|---|
| `pytesseract` 未安装 | `main()` 开头的 `import pytesseract` 抛 `ImportError` | stderr 打印 `请安装: pip install pytesseract pillow`，返回 1 |
| 系统 Tesseract 未安装/不在 `PATH` | `image_to_string` 抛 `pytesseract.TesseractNotFoundError` | stderr 打印安装指引与官方仓库地址，返回 1 |

**已实测（降级路径）**：本机环境未装 `pytesseract`，脚本按预期走 `ImportError` 分支，向 stderr 打印 `请安装: pip install pytesseract pillow` 并以退出码 1 结束；系统 `tesseract` 二进制同样不存在，故未产生任何 OCR 输出。注意该分支在 `make_sample_png` 之前触发，因此 `_ocr_sample.png` 并未生成——这也验证了脚本「检测不到依赖时给提示、不抛栈」的设计。装好两层依赖后重跑，预期输出以 `OCR 输出:` 开头、内容为 `HELLO OCR 123`（字体回退到默认位图字体时可能有轻微误差）。

---

## 5. 学习贴士

- **OCR 不是万能**：复杂纹理背景、严重形变、重叠笔画会显著拉低准确率，这类场景需要深度学习检测/分割模型或人工复核兜底，不要指望调阈值解决一切。
- **预处理往往比换引擎更划算**：同一张脏图，花十分钟调灰度+阈值，收益常常大于换更 fancy 的识别方案。先洗干净，再谈识别。
- **降级提示是工程素养**：`ocr_threshold_demo.py` 对两种缺失（缺 Python 包、缺系统引擎）分别给出可操作的安装提示而非 traceback，自己写工具脚本时值得照抄。
- **与第 7、8 章衔接**：OCR 输出往往带噪声（错字、多余空白、断行），要做**清洗与规范化**后再入库，别直接当结构化数据用。
- **先跑通再调优**：第一次接触这条链路时，先用脚本自带的测试图确认三层依赖全通，再换自己的图——把「环境没装好」和「参数没调好」两类问题分开排查。
- **合规意识前置**：动手写识别代码之前先想清楚「这张图我有没有权识别」，自建靶场随便玩，第三方验证码碰都别碰。

---

## 6. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-13/pillow_resize.py` | Pillow 生成纯色图 + `convert("L")` 灰度化 + 落盘（已实测，生成 `demo_gray.png`） |
| `chapter-13/ocr_threshold_demo.py` | 造测试图 → 阈值化 → `pytesseract.image_to_string`，含双降级路径（已实测 ImportError 分支） |
| `chapter-13/requirements.txt` | 本章依赖：`Pillow>=10.0.0`、`pytesseract>=0.3.10`，注释内附系统级 Tesseract 安装命令 |

对照第 6 章看：OCR 产出的文本同样面临「落地」问题——识别结果可以走 CSV/JSON Lines 或数据库入库，只是入库前多一道清洗工序。对照第 12 章（若你按顺序读过来）也能看到一个共性：凡是「从非结构化载体恢复结构化数据」的环节，都遵循「预处理 → 提取 → 清洗 → 落地」这条流水线，本章只是把「载体」从 HTML 换成了像素。

---

## 练习建议

1. 对同一张测试图扫描阈值 `120–180`（步长 10），记录每组阈值下的识别长度与肉眼可读性，体会「没有普适阈值」。
2. 把 `image_to_string` 换成 **`image_to_data`**，输出每个词的置信度，试着过滤低置信片段后再拼接文本。
3. 阅读 Tesseract 文档中的 **PSM（页面分割模式）** 参数，用 `--psm 7`（单行文本）之类的配置对 `HELLO OCR 123` 这种单行图做针对性优化。
4. 给 `make_sample_png` 加点噪点（随机像素撒点或浅色底纹），观察不预处理与阈值化后识别结果的差异。
5. 用 `ImageEnhance.Contrast` 和 `resize` 各写一种预处理变体，与纯阈值化横向对比同一批图的识别效果。
6. 把 `ocr_threshold_demo.py` 的降级提示模式搬到自己的某个工具脚本里：对关键外部依赖做显式检测，失败时打印可操作的安装指引而非 traceback。
