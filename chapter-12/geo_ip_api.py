"""第12章：通过公开 JSON API 查询 IP 所在国家（urllib + json）。"""
from __future__ import annotations

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def get_country(ip_address: str) -> str | None:
    """
    使用 ip-api.com 免费接口（有频率与用途限制，详见其官网说明）。
    书中淘宝 IP 库接口已不可用，此为教学替代示例。
    """
    url = f"http://ip-api.com/json/{ip_address}?fields=status,message,country"
    req = Request(url, headers={"User-Agent": "Chapter12GeoDemo/1.0 (educational)"})
    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
    except (HTTPError, URLError, OSError) as e:
        print("请求失败:", e, file=sys.stderr)
        return None

    data = json.loads(raw)
    if data.get("status") != "success":
        print("接口返回非 success:", data, file=sys.stderr)
        return None
    return data.get("country")


def main() -> int:
    ip = "50.78.253.58"
    c = get_country(ip)
    print(ip, "->", c)
    return 0 if c else 1


if __name__ == "__main__":
    raise SystemExit(main())
