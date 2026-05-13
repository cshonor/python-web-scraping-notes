"""
Optional Playwright demo: renders a page and prints the document title.

Requires: pip install playwright && playwright install chromium

If Playwright is not installed, the script exits with a clear message.
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Playwright not installed. Run:\n"
            "  pip install playwright\n"
            "  playwright install chromium",
            file=sys.stderr,
        )
        return 1

    url = "https://example.com"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            title = page.title()
            print("Title:", title)
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
