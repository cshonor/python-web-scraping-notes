"""第11章：Playwright 渲染标题（可选依赖）。"""
from __future__ import annotations

import sys


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("安装: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto("https://example.com", wait_until="domcontentloaded", timeout=30_000)
            print("title:", page.title())
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
