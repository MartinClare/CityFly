#!/usr/bin/env python3
"""Write extra magazine packs from named today's stories. Does not recrawl."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common.config import load_env, load_topic_config
from common.storage import TopicStorage
from hk_city.analyzers.classify import classify_item
from hk_city.reporter import CityFlyReporter

PICKS = [
    (2, "https://news.rthk.hk/rthk/ch/component/k2/1870708-20260919.htm"),
    (3, "https://news.rthk.hk/rthk/ch/component/k2/1870699-20260919.htm"),
    (4, "https://news.rthk.hk/rthk/ch/component/k2/1870698-20260919.htm"),
]

EXTRA_FOR = {
    "https://news.rthk.hk/rthk/ch/component/k2/1870699-20260919.htm": [
        "https://news.rthk.hk/rthk/ch/component/k2/1870643-20260918.htm",
        "https://news.rthk.hk/rthk/ch/component/k2/1870642-20260918.htm",
    ]
}


def _by_link(raw: dict, url: str) -> dict | None:
    for payload in raw.values():
        if not isinstance(payload, dict):
            continue
        for item in payload.get("items") or []:
            if (item.get("link") or "").rstrip("/") == url.rstrip("/"):
                return item
    return None


def main() -> int:
    load_env()
    storage = TopicStorage("hk_city", as_of="2026-09-19")
    config = load_topic_config("hk_city")
    config["skip_images"] = True
    view = storage.read_json(storage.processed_dir / "view.json")
    raw = storage.list_raw()
    ranked = { (c.get("link") or "").rstrip("/"): c for c in (view.get("ranked_candidates") or []) }
    reporter = CityFlyReporter(storage, config)

    for idx, url in PICKS:
        item = _by_link(raw, url)
        cand = ranked.get(url.rstrip("/"))
        if item and not cand:
            row = dict(item)
            row["_collector"] = "local_news"
            cand = classify_item(row)
        if item and cand:
            cand = {**cand, **{k: item.get(k) for k in ("title", "link", "summary", "source", "published")}}
            cand.setdefault("sources", [item])
        if not cand:
            print(f"missing {url}")
            continue
        extras = []
        for extra_url in EXTRA_FOR.get(url, []):
            hit = _by_link(raw, extra_url)
            if hit:
                extras.append(hit)
        if extras:
            cand = {**cand, "sources": [*(cand.get("sources") or []), *extras]}
        print(f"drafting {idx}: {cand.get('title')}")
        reporter._one_pack(idx, cand, view)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
