"""第17章：Chrome 通过本地 Tor SOCKS 访问 icanhazip（需 selenium + Tor）。"""
from __future__ import annotations

import sys

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

TOR_SOCKS = "socks5://127.0.0.1:9150"  # tor 守护进程常见 9050
URL = "https://icanhazip.com"


def main() -> int:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--proxy-server=" + TOR_SOCKS)

    try:
        driver = webdriver.Chrome(options=options)
    except WebDriverException as e:
        print("无法启动 Chrome:", e, file=sys.stderr)
        return 1

    try:
        driver.get(URL)
        print(driver.find_element(By.TAG_NAME, "body").text.strip())
        return 0
    except Exception as e:
        print("请求失败（Tor 未启动或代理不可达？）:", e, file=sys.stderr)
        return 1
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
