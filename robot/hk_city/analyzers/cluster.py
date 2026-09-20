"""Dedupe near-duplicate headlines and URLs."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlparse

from common.base_analyzer import BaseAnalyzer


class ClusterAnalyzer(BaseAnalyzer):
    name = "cluster"

    def analyze(self, raw: dict[str, Any]) -> dict[str, Any]:
        items = flatten_items(raw)
        clusters: list[dict[str, Any]] = []
        seen: dict[str, int] = {}
        for item in items:
            if str(item.get("id", "")).startswith("error:"):
                continue
            key = _cluster_key(item)
            if key in seen:
                clusters[seen[key]]["sources"].append(_slim(item))
                continue
            seen[key] = len(clusters)
            clusters.append(
                {
                    "id": key,
                    "title": item.get("title") or "",
                    "link": item.get("link") or "",
                    "published": item.get("published"),
                    "primary_tier": item.get("tier", 5),
                    "collector": item.get("_collector"),
                    "sources": [_slim(item)],
                }
            )
        return {"count": len(clusters), "clusters": clusters}


def flatten_items(raw: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for collector, payload in raw.items():
        if not isinstance(payload, dict):
            continue
        for item in payload.get("items") or []:
            if isinstance(item, dict):
                row = dict(item)
                row["_collector"] = collector
                items.append(row)
    return items


def _slim(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": item.get("source"),
        "title": item.get("title"),
        "link": item.get("link"),
        "published": item.get("published"),
        "tier": item.get("tier"),
        "policy": item.get("policy"),
        "summary": (item.get("summary") or "")[:1200],
        "collector": item.get("_collector"),
    }


def _cluster_key(item: dict[str, Any]) -> str:
    link = (item.get("link") or "").strip()
    if link:
        parsed = urlparse(link)
        path = parsed.netloc + parsed.path.rstrip("/")
        if parsed.query:
            path += "?" + parsed.query
        if path:
            return "url:" + path.lower()
    title = re.sub(r"\s+", "", (item.get("title") or "").lower())
    title = re.sub(r"[^\w\u4e00-\u9fff]", "", title)[:40]
    if title:
        return "t:" + title
    return "h:" + hashlib.sha1(str(item.get("id", "")).encode()).hexdigest()[:10]
