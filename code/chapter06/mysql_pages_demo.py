"""
第6章：PyMySQL 写入示例（需本机 MySQL + pip install pymysql）。

敏感信息请用环境变量：
  MYSQL_HOST  MYSQL_USER  MYSQL_PASSWORD
可选：MYSQL_PORT（默认 3306）
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    try:
        import pymysql
    except ImportError:
        print("请先安装: pip install pymysql", file=sys.stderr)
        return 1

    host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    user = os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQL_PASSWORD", "")
    port = int(os.environ.get("MYSQL_PORT", "3306"))

    if password == "":
        print("未设置 MYSQL_PASSWORD，跳过数据库演示。", file=sys.stderr)
        print("示例: set MYSQL_PASSWORD=yoursecret  后重新运行。")
        return 0

    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE DATABASE IF NOT EXISTS scraping")
            cur.execute("USE scraping")
            cur.execute(
                """CREATE TABLE IF NOT EXISTS pages (
                id BIGINT NOT NULL AUTO_INCREMENT,
                title VARCHAR(200),
                content VARCHAR(10000),
                PRIMARY KEY (id))"""
            )
            title = "示例标题"
            content = "抓取的网页内容..."
            cur.execute(
                "INSERT INTO pages (title, content) VALUES (%s, %s)",
                (title, content),
            )
        conn.commit()
        print("数据已成功写入 scraping.pages（示例一行）")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
