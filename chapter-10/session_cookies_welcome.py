"""第10章：Session + Cookie 登录示例（书中 pythonscraping cookies 页）。"""
from __future__ import annotations

import sys

import requests


def main() -> int:
    session = requests.Session()
    session.headers["User-Agent"] = "Chapter10Cookies/1.0 (educational)"

    login = "https://pythonscraping.com/pages/cookies/welcome.php"
    profile = "https://pythonscraping.com/pages/cookies/profile.php"

    try:
        # 原书使用 post(..., params=...)：字段走查询串；若站点改为表单体，请改为 data={...}
        r = session.post(
            login,
            params={"username": "Ryan", "password": "password"},
            timeout=25,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        print("登录页请求失败（站点不可用或网络问题）:", e, file=sys.stderr)
        return 1

    print("Cookie:", session.cookies.get_dict())

    try:
        r2 = session.get(profile, timeout=25)
        r2.raise_for_status()
    except requests.RequestException as e:
        print("profile 请求失败:", e, file=sys.stderr)
        return 1

    print(r2.text[:800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
