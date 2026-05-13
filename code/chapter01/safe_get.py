"""第1章：带异常处理的安全 GET。"""
import requests
from requests.exceptions import RequestException


def safe_get_url(url: str, timeout: float = 10) -> str | None:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except RequestException as e:
        print(f"请求出错: {e}")
        return None


if __name__ == "__main__":
    html = safe_get_url("https://example.com")
    if html:
        print("获取成功，长度:", len(html))
    else:
        print("获取失败")
