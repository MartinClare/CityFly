#!/usr/bin/env python3
"""Post approved City Sight stories to the Facebook Page.

Usage (on ECS):
  python scripts/post_facebook.py
  python scripts/post_facebook.py --lookback-days 14
  python scripts/post_facebook.py --limit 0   # 0 = no cap (default is FACEBOOK_MAX_PER_RUN, usually 2)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.config import load_env
from hk_city.facebook_publish import post_pending

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max posts this run; omit = FACEBOOK_MAX_PER_RUN (default 2); 0 = no cap",
    )
    parser.add_argument("--lookback-days", type=int, default=None, help="Only stories from the last N days")
    args = parser.parse_args()
    summary = post_pending(limit=args.limit, lookback_days=args.lookback_days)
    print(json.dumps({k: summary[k] for k in summary if k != "results"}, ensure_ascii=False))
    for row in summary.get("results") or []:
        print(json.dumps(row, ensure_ascii=False))
    return 0 if summary.get("ok") or summary.get("skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
