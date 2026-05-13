# 第 13 章 图像识别与文字处理：学习笔记

本章介绍如何用 **OCR（光学字符识别）** 从图像中恢复文字，并结合 **Pillow** 做预处理。典型**合规**用途包括：扫描件/发票/档案数字化、无障碍辅助、桌面自动化中的**自有**截图识别等。

---

## 1. 核心工具库

- **Pillow**：打开图像、灰度化、裁剪、对比度与**点运算阈值**等预处理。
- **Tesseract**：主流开源 OCR 引擎；需单独安装系统 **`tesseract` 可执行文件**（Windows 安装包或包管理器；并确保加入 `PATH`）。
- **`pytesseract`**：Python 包装器，桥接到 Tesseract CLI。
- **NumPy（可选）**：将图像转为数组做批量像素运算、与 OpenCV 生态衔接；也可用于对置信度等元数据做数值处理。

---

## 2. 图像预处理与自动调整

- **阈值化**：将灰度图按阈值切成高对比黑白图，常能削弱浅底噪点、提升 OCR 稳定性。
- **参数搜索（书中思路）**：在合理范围内扫描阈值，结合 **Tesseract 置信度/字符数** 等启发式挑一组较优参数（注意过拟合单张图；批量任务应分数据集验证）。

---

## 3. 验证码（CAPTCHA）与训练（合规边界）

- **Tesseract 训练**：对固定字体、固定版式的小字符集，可通过训练数据提升识别率；工程成本高，且**误用风险大**。
- **强烈不建议**：对**第三方网站**登录/注册等验证码做「自动识别 + 多次尝试直到成功」，极易违反服务条款并可能触犯法律。教学与实验请在**自建靶场**、**授权渗透测试**或**公开 OCR 数据集**上进行。
- **更稳妥路线**：官方 API、人工打码平台（有合同与合规流程）、或产品侧去除不合理机器滥用场景的人机验证设计。

---

## 4. 代码示例：阈值 + OCR

需：`pip install pillow pytesseract`，并安装系统 **Tesseract**。

可运行脚本：`code/chapter13/ocr_threshold_demo.py`（若未安装 Tesseract，会提示安装步骤；脚本会生成一张简单测试图）

```python
from PIL import Image
import pytesseract

def clean_file(path: str, threshold: int) -> Image.Image:
    image = Image.open(path).convert("L")
    return image.point(lambda x: 0 if x < threshold else 255)

image = clean_file("test_image.png", 143)
print(pytesseract.image_to_string(image))
```

---

## 5. 学习贴士

- **OCR 不是万能**：复杂纹理、严重形变、重叠笔画会显著降准确率，必要时需深度学习检测/分割模型或人工复核。
- **与第 7、8 章衔接**：OCR 输出往往要做**清洗与规范化**后再入库。

---

## 6. 与本仓库其他示例

`code/chapter13/pillow_resize.py`：纯 Pillow 生成/处理图像的最小示例。

## 练习建议

1. 对同一张图扫描阈值 `120–180`，记录识别长度与肉眼可读性。  
2. 使用 `image_to_data` 输出每个词的置信度，过滤低置信片段。  
3. 阅读 Tesseract 文档中的 **PSM（页面分割模式）** 参数，尝试对一行文本优化配置。
