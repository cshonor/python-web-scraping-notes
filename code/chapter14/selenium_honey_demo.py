"""第14章：Selenium 检查隐藏链接与隐藏输入（itsatrap 示例页）。"""
from __future__ import annotations

import sys

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

URL = "https://pythonscraping.com/pages/itsatrap.html"


def main() -> int:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    try:
        driver = webdriver.Chrome(options=options)
    except WebDriverException as e:
        print("无法启动 Chrome:", e, file=sys.stderr)
        print("请安装 selenium 与本机 Chrome。", file=sys.stderr)
        return 1

    try:
        driver.get(URL)
        for link in driver.find_elements(By.TAG_NAME, "a"):
            if not link.is_displayed():
                print("警告：隐藏链接", link.get_attribute("href"))
        for field in driver.find_elements(By.TAG_NAME, "input"):
            if not field.is_displayed():
                print("警告：隐藏字段", field.get_attribute("name"))
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
