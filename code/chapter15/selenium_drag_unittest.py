"""第15章：unittest + Selenium 拖放示例（Chrome / Selenium 4）。"""
from __future__ import annotations

import unittest

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By

URL = "https://pythonscraping.com/pages/javascript/draggableDemo.html"


class TestDragAndDrop(unittest.TestCase):
    driver = None

    @classmethod
    def setUpClass(cls) -> None:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        try:
            cls.driver = webdriver.Chrome(options=options)
        except WebDriverException as e:
            raise unittest.SkipTest(f"Chrome WebDriver 不可用: {e}") from e
        cls.driver.get(URL)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.driver is not None:
            cls.driver.quit()

    def test_drag(self) -> None:
        assert self.driver is not None
        element = self.driver.find_element(By.ID, "draggable")
        target = self.driver.find_element(By.ID, "div2")
        ActionChains(self.driver).drag_and_drop(element, target).perform()
        msg = self.driver.find_element(By.ID, "message").text
        self.assertIn("bot", msg.lower())


if __name__ == "__main__":
    unittest.main()
