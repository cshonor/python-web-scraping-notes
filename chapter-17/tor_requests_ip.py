"""第17章：通过本地 Tor SOCKS 端口查看出口 IP（requests + PySocks）。"""
from __future__ import annotations

import sys

try:
    import requests
except ImportError:
    print("请安装: pip install requests", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    try:
        import socks  # noqa: F401  # PySocks：requests 使用 socks5h 代理所需
    except ImportError:
        print("请安装: pip install pysocks", file=sys.stderr)
        return 1

    # Tor Browser 默认 9150；tor 守护进程常见 9050
    ports = (9150, 9050)
    url = "https://icanhazip.com"
    for port in ports:
        proxies = {
            "http": f"socks5h://127.0.0.1:{port}",
            "https": f"socks5h://127.0.0.1:{port}",
        }
        try:
            r = requests.get(url, proxies=proxies, timeout=12)
            r.raise_for_status()
            print(f"SOCKS5 127.0.0.1:{port} ->", r.text.strip())
            return 0
        except OSError as e:
            print(f"端口 {port} 不可用:", e)
        except requests.RequestException as e:
            print(f"端口 {port} 请求失败:", e)
    print(
        "未检测到可用的本地 Tor SOCKS 端口。\n"
        "请先启动 Tor Browser 或 tor 服务，并确认监听 9150/9050。",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
