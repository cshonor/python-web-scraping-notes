"""第2章：CSS 选择器与 lambda 筛选。"""
from bs4 import BeautifulSoup

html = """
<html><body>
<div class="item" data-id="1"><a href="/a">A</a></div>
<div class="item" data-id="2"><span>B</span></div>
</body></html>
"""
soup = BeautifulSoup(html, "lxml")

print("CSS select:", [x.get_text(strip=True) for x in soup.select("div.item a")])

items = soup.find_all("div", class_="item", attrs={"data-id": True})
print("lambda 过滤 data-id>1:", [i["data-id"] for i in items if int(i["data-id"]) > 1])
