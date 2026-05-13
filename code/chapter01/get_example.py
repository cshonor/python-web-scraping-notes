"""第1章：GET 请求示例。"""
import requests

url = "https://example.com"
response = requests.get(url, timeout=15)

print(f"状态码: {response.status_code}")
print("响应内容前500字符:")
print(response.text[:500])
