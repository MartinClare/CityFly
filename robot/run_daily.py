#!/usr/bin/env python3
"""Daily City Fly desk: collect -> analyze -> briefing + article packs.

Usage:
  python run_daily.py hk_city
  python run_daily.py hk_city --date 2026-09-19
  python run_daily.py hk_city --skip-collect
  python run_daily.py hk_city --skip-images
  python run_daily.py hk_city --skip-report
  python run_daily.py hk_city --hourly
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.config import load_env, load_topic_config
from common.storage import TopicStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_daily")

FEED_GROUPS = [
    "gov_news",
    "city_projects",
    "living_housing",
    "mobility",
    "city_macro",
    "local_news",
    "consultancy",
    "tech_local",
]


def _hk_city_pipeline(storage: TopicStorage, config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    from hk_city.analyzers.editorial_view import EditorialViewAnalyzer
    from hk_city.collectors.group import GroupCollector
    from hk_city.collectors.property_data import PropertyDataCollector
    from hk_city.reporter import CityFlyReporter

    statuses: list[dict[str, Any]] = []
    if not args.skip_collect:
        collectors: list[Any] = [GroupCollector(storage, config, name) for name in FEED_GROUPS]
        collectors.append(PropertyDataCollector(storage, config))
        for c in collectors:
            statuses.append(c.run())
    else:
        logger.info("Skipping collect (--skip-collect)")

    raw = storage.list_raw()
    editorial = EditorialViewAnalyzer(storage, config).run(raw)
    view = {
        "as_of": storage.as_of,
        "topic": "hk_city",
        "independent_summary": editorial.get("independent_summary"),
        "ranked_candidates": editorial.get("ranked_candidates") or [],
        "property_snapshot": editorial.get("property_snapshot"),
        "pillar_mix": editorial.get("pillar_mix"),
        "publishable_count": editorial.get("publishable_count"),
        "collector_status": statuses,
    }
    path = storage.write_processed_json("view.json", view)
    logger.info("Wrote independent view -> %s", path)

    report_path = None
    if not args.skip_report:
        CityFlyReporter(storage, config).run(view, raw)
        report_path = str(storage.report_path())
    else:
        logger.info("Skipping report (--skip-report)")

    return {"view_path": str(path), "report_path": report_path, "statuses": statuses}


PIPELINES: dict[str, Callable[..., dict[str, Any]]] = {
    "hk_city": _hk_city_pipeline,
}


def main(argv: list[str] | None = None) -> int:
    load_env()
    parser = argparse.ArgumentParser(description="Run City Fly daily desk")
    parser.add_argument("topic", choices=sorted(PIPELINES.keys()), help="Topic package name")
    parser.add_argument("--date", dest="as_of", default=None, help="As-of date YYYY-MM-DD")
    parser.add_argument("--skip-collect", action="store_true")
    parser.add_argument("--skip-report", action="store_true")
    parser.add_argument("--skip-images", action="store_true", help="Write packs without calling kie.ai")
    parser.add_argument(
        "--hourly",
        action="store_true",
        help="Recrawl and rank only. Do not draft articles (use for hourly cron).",
    )
    args = parser.parse_args(argv)
    if args.hourly:
        args.skip_report = True

    if args.as_of:
        date.fromisoformat(args.as_of)

    storage = TopicStorage(args.topic, as_of=args.as_of)
    storage.ensure_dirs()
    config = load_topic_config(args.topic)
    if getattr(args, "skip_images", False):
        config["skip_images"] = True

    logger.info("=== Daily run topic=%s as_of=%s ===", args.topic, storage.as_of)
    result = PIPELINES[args.topic](storage, config, args)
    logger.info("Done: %s", {k: result[k] for k in ("view_path", "report_path")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
