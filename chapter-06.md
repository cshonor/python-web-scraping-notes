# 第6章：存储数据

## 核心主题

将抓取结果以 CSV、JSON、关系型数据库等形式可靠落盘。

---

## 6.1 平面格式

### 核心概念

- **CSV**：表格互操作最好；注意编码 `encoding="utf-8-sig"` 便于 Excel 打开  
- **JSON / JSON Lines**：嵌套结构友好；`.jsonl` 适合流式追加  

### 可运行代码示例

`code/chapter06/save_csv_json.py`

### 新手易错点

- CSV 字段内含逗号、换行时需用 `csv` 模块而非手写拼接  
- 数据库连接应用上下文管理器或 `try/finally` 关闭  

---

## 6.2 SQLite 示例

### 核心概念

- **标准库 `sqlite3`**：零配置，适合本地与中规模数据  
- **主键与唯一约束**：避免重复插入同一 URL  

### 可运行代码示例

`code/chapter06/sqlite_store.py`

---

## 本章小结

- 存储格式由**下游消费方式**决定：人看用 CSV，程序接用 JSON/API，分析用 SQL  
- 写入路径要考虑**并发写入**（第 16 章）时的锁与事务  

## 本章练习题

1. 将同一批字典列表分别写入 UTF-8 CSV 与 `jsonl`  
2. 设计一张 `pages(url TEXT PRIMARY KEY, title TEXT, scraped_at TEXT)` 并批量插入  
3. 实现「若 URL 已存在则更新 `title`」的 upsert 逻辑（SQLite 3.24+ `INSERT ... ON CONFLICT`）  
