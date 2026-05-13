"""第1章：BeautifulSoup 解析示例。"""
import requests
from bs4 import BeautifulSoup

url = "https://example.com"
response = requests.get(url, timeout=15)
response.raise_for_status()

soup = BeautifulSoup(response.text, "lxml")

title_tag = soup.title
if title_tag and title_tag.string:
    print("网页标题:", title_tag.string.strip())
else:
    print("网页标题: (无)")

for p in soup.find_all("p"):
    print(p.get_text(strip=True))
