"""第11章：Playwright 版 Ajax 等待（不依赖 ChromeDriver）。"""
from __future__ import annotations

import sys


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("安装: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    url = "https://pythonscraping.com/pages/javascript/ajaxDemo.html"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_selector("#loadedButton", timeout=15_000)
            txt = page.locator("#content").inner_text()
            print(txt)
        except Exception as e:
            print("Playwright 失败:", e, file=sys.stderr)
            return 1
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
