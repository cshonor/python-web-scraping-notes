"""第11章：Selenium 4 + 显式等待抓取 Ajax 示例页（需 Chrome + selenium）。"""
from __future__ import annotations

import sys

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

URL = "https://pythonscraping.com/pages/javascript/ajaxDemo.html"


def get_dynamic_content(url: str) -> int:
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print("无法启动 Chrome WebDriver:", e, file=sys.stderr)
        print("请安装: pip install selenium", file=sys.stderr)
        print("并确保本机已安装 Google Chrome（Selenium Manager 会尝试匹配驱动）。", file=sys.stderr)
        return 1

    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "loadedButton"))
        )
        content = driver.find_element(By.ID, "content").text
        print("内容加载成功:\n", content)
        return 0
    except TimeoutException:
        print("加载超时：未在限定时间内找到 #loadedButton", file=sys.stderr)
        return 1
    finally:
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    raise SystemExit(get_dynamic_content(URL))
