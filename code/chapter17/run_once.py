"""第17章：单次运行入口（可被 cron / 任务计划程序调用）。"""
from __future__ import annotations

import sys
from datetime import datetime, timezone


def main() -> int:
    print("run_once:", datetime.now(timezone.utc).isoformat())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
