# 第8章：数据清洗

## 核心主题

对抓取后的原始字符串做规范化、去重、类型转换，得到可分析数据。

---

## 8.1 字符串与空白

### 核心概念

- **`str.strip`、正则 `re.sub`**：去首尾空白、统一换行  
- **Unicode 规范化**：`unicodedata.normalize("NFKC", s)` 处理全角半角等  

### 可运行代码示例

`code/chapter08/clean_text.py`

### 新手易错点

- 在解析阶段过度清洗可能删掉合法内容；清洗规则应可配置、可单测  

---

## 8.2 表格化与 pandas

### 核心概念

- **`pandas`**：去重 `drop_duplicates`、缺失值 `fillna`、类型 `astype`  

```bash
pip install pandas
```

`code/chapter08/pandas_dedupe.py`

---

## 本章小结

- 清洗是**可重复流水线**，与抓取解耦  
- 为每条规则写小函数，便于在第 15 章用测试锁定行为  

## 本章练习题

1. 实现函数：合并连续空白、统一为单个空格  
2. 对 DataFrame 按 `url` 去重，保留 `scraped_at` 最新一行  
3. 把价格字符串 `"$1,234.50"` 转为浮点数（处理货币符号与千分位）  
